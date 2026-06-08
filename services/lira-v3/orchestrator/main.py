"""
Lira V2.5 Orchestrator — Central nervous system.
Connects all subsystems via NATS, serves WebSocket for chat UI,
monitors service health, routes requests.
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File

from shared.settings import settings
from shared.lore_manager import LoreManager
from shared.prompt_assembler import PromptAssembly
from shared.mode_router import (
    get_system_prompt, get_style_guide,
    list_personalities, update_personality,
    save_snapshot, list_snapshots, load_snapshot,
)
from chat.llm_client import LLMClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("orchestrator")

# --- Shared state ---
lore_mgr = LoreManager(settings.lore_path)
assembler = PromptAssembly(lore_mgr)
llm = LLMClient()
active_mode: str = "assistant"


class SessionState:
    """Per-connection conversation state. Global is fine for single-user local app."""
    def __init__(self):
        self.history: list[dict] = []

    def add_user(self, text: str):
        self.history.append({"role": "user", "content": text})

    def add_assistant(self, text: str):
        self.history.append({"role": "assistant", "content": text})

    def clear(self):
        self.history.clear()

    def delete(self, index: int):
        if 0 <= index < len(self.history):
            self.history.pop(index)

    def build_prompt(self, mode: str, user_text: str) -> dict:
        """Build prompt with proper message ordering — user appears once."""
        return assembler.build(mode, self.history, user_text)


session = SessionState()


# --- Health monitor ---
async def _health_check():
    """Check all critical services, return status dict."""
    results = {}
    async with httpx.AsyncClient(timeout=5) as client:
        for name, url in [
            ("ollama", f"{settings.ollama_base_url}/api/tags"),
            ("kokoro", f"{settings.kokoro_tts_url.rsplit('/v1', 1)[0]}/health"),
            ("whisper", f"{settings.whisper_url.rsplit('/', 1)[0]}/health"),
        ]:
            try:
                resp = await client.get(url)
                results[name] = resp.status_code == 200
            except Exception:
                results[name] = False
    return results


# --- WebSocket chat handler ---
async def _handle_chat(ws: WebSocket, user_text: str):
    global active_mode

    session.add_user(user_text)
    assembled = session.build_prompt(active_mode, user_text)

    # Send lore debug
    await ws.send_json({
        "type": "lore_injected",
        "lore": assembled["injected_lore"],
        "system_preview": assembled["system"][:500],
    })

    # Stream from LLM
    full_response = ""
    async for delta in llm.stream(assembled["system"], assembled["messages"]):
        if delta is None:
            # Signal to fall back to cloud
            await ws.send_json({"type": "text", "delta": "(switching to cloud...)\n"})
            async for delta in llm.stream_fallback(assembled["system"], assembled["messages"]):
                if delta:
                    full_response += delta
                    await ws.send_json({"type": "text", "delta": delta})
            break
        full_response += delta
        await ws.send_json({"type": "text", "delta": delta})

    session.add_assistant(full_response)

    # TTS — send full response to voice proxy
    if full_response.strip():
        try:
            clean = full_response.strip().replace('"', '').replace('\u201c', '').replace('\u201d', '')
            async with httpx.AsyncClient(timeout=60) as client:
                tts_resp = await client.post(
                    settings.kokoro_tts_url,
                    json={
                        "model": "tts-1",
                        "input": clean,
                        "voice": settings.kokoro_voice,
                        "speed": settings.kokoro_speed,
                        "mode": active_mode,
                    },
                )
                if tts_resp.status_code == 200:
                    import base64
                    b64 = base64.b64encode(tts_resp.content).decode()
                    await ws.send_json({"type": "audio", "chunk": b64})
        except Exception as e:
            try:
                await ws.send_json({"type": "tts_error", "message": f"TTS failed: {e}"})
            except Exception:
                pass

    await ws.send_json({"type": "done", "full_text": full_response})


# --- Image handler ---
async def _handle_image(prompt: str) -> tuple[bytes, str]:
    from pathlib import Path
    import random
    import re

    # Build workflow from template
    raw = Path(settings.comfyui_workflow_path).read_text(encoding="utf-8")
    s = raw.replace("%prompt%", prompt)
    s = s.replace("%seed%", str(random.randint(0, 2**32 - 1)))
    for key, val in {
        "%steps%": "20", "%width%": "896", "%height%": "896",
        "%scale%": "5", "%sampler%": "dpmpp_2m", "%scheduler%": "karras",
        "%denoise%": "1",
        "%model%": "unrealvisionXLPhotoreal_realismUniversal.safetensors",
        "%negative_prompt%": "worst quality, low quality, bad anatomy, deformed, blurry, watermark, text, signature",
    }.items():
        s = s.replace(key, val)
    workflow = json.loads(s)

    async with httpx.AsyncClient(timeout=30) as client:
        # Clear stale queue
        try:
            await client.post(f"{settings.comfyui_base_url}/interrupt")
            await client.post(f"{settings.comfyui_base_url}/queue", json={"clear": True})
        except Exception:
            pass

        # Submit prompt
        resp = await client.post(
            f"{settings.comfyui_base_url}/prompt",
            json={"prompt": workflow, "client_id": "lira-v25"},
        )
        if resp.is_error:
            raise RuntimeError(f"ComfyUI error: {resp.status_code}")
        prompt_id = resp.json().get("prompt_id", "")

    # Poll for completion
    deadline = asyncio.get_event_loop().time() + 300
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            if asyncio.get_event_loop().time() > deadline:
                raise TimeoutError("ComfyUI generation timed out")
            await asyncio.sleep(2)
            resp = await client.get(f"{settings.comfyui_base_url}/history/{prompt_id}")
            if resp.is_error:
                continue
            history = resp.json().get(prompt_id)
            if history and history.get("status", {}).get("completed"):
                break
            if history and history.get("status", {}).get("error"):
                raise RuntimeError(f"ComfyUI failed: {history['status']['error']}")

    # Find output image
    outputs = history.get("outputs", {})
    out_dir = Path(settings.comfyui_output_dir)
    for node_output in outputs.values():
        for img in node_output.get("images", []):
            filepath = out_dir / img["filename"]
            if filepath.exists():
                return filepath.read_bytes(), img["filename"]

    raise RuntimeError("Image not found in ComfyUI output")


# --- Auto-search ---
async def _web_search(query: str, max_results: int = 5) -> list[dict]:
    import urllib.parse
    import re
    url = "https://html.duckduckgo.com/html/"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, data={"q": query}, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
        })
        if resp.status_code != 200:
            return []
        html = resp.text
        results = []
        blocks = re.findall(r'<div[^>]*class="[^"]*result[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)
        for block in blocks:
            title_m = re.search(r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*>(.*?)</a>', block, re.DOTALL)
            snippet_m = re.search(r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', block, re.DOTALL)
            if title_m:
                title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip()
                snippet = re.sub(r'<[^>]+>', '', snippet_m.group(1)).strip() if snippet_m else ""
                if title and title not in {r['title'] for r in results}:
                    results.append({"title": title, "snippet": snippet[:300]})
            if len(results) >= max_results:
                break
        return results


# --- Routes ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup health check
    health = await _health_check()
    for name, ok in health.items():
        status = "OK" if ok else "DOWN"
        logger.info(f"  {name}: {status}")
    yield


app = FastAPI(title="Lira V2.5 Orchestrator", lifespan=lifespan)


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("http://localhost:3000")


@app.get("/api/health")
async def api_health():
    return {"status": "ok", "services": await _health_check()}


@app.get("/api/debug/settings")
async def debug_settings():
    import os
    return {
        "lore_path": settings.lore_path,
        "cwd": os.getcwd(),
        "ollama_model": settings.ollama_model,
    }


@app.get("/api/lore/all")
async def lore_all():
    return {"count": len(lore_mgr._entries), "entries": lore_mgr.as_dict(lore_mgr.all_entries())}


@app.websocket("/ws")
async def chat_ws(ws: WebSocket):
    global active_mode
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "message")

            if msg_type == "set_mode":
                active_mode = data.get("mode", "assistant")
                await ws.send_json({"type": "mode_set", "mode": active_mode})
                continue

            if msg_type == "clear_history":
                session.clear()
                await ws.send_json({"type": "history_cleared"})
                continue

            if msg_type == "get_lore":
                await ws.send_json({"type": "lore_list", "entries": lore_mgr.as_dict(lore_mgr.all_entries())})
                continue

            # Lore CRUD handlers (abbreviated — full CRUD from V2 main.py can be ported later)
            if msg_type in ("toggle_worldbook", "toggle_lore", "update_lore", "delete_message"):
                # Placeholder — full lore CRUD routes port from V2
                continue

            if msg_type != "message":
                continue

            user_text = data.get("text", "")
            if not user_text.strip():
                continue

            # Detect /search command
            import re as re_mod
            search_match = re_mod.match(r"^/(?:search|g)\s+(.+)", user_text, re_mod.IGNORECASE)
            if search_match:
                query = search_match.group(1).strip()
                await ws.send_json({"type": "text", "delta": f"Searching: {query}...\n\n"})
                try:
                    results = await _web_search(query)
                    if results:
                        ctx = "Web search results:\n" + "\n".join(f"- {r['title']}: {r['snippet']}" for r in results)
                        user_text = f"I searched for: {query}\n\n{ctx}\n\nBased on these results, respond: {query}"
                    else:
                        user_text = f"I searched for '{query}' but found nothing. What do you know about this?"
                except Exception:
                    pass

            # Auto-image detection
            image_match = re_mod.match(
                r"^(?:show\s+me|generate|create|make|draw|visualize|picture\s+of|image\s+of)\s+(.+)",
                user_text, re_mod.IGNORECASE
            )
            if image_match and settings.comfyui_workflow_path:
                description = image_match.group(1).strip().rstrip(".!?")
                person_words = {"portrait", "woman", "man", "person", "face", "fae", "elf", "character", "girl", "boy", "lady", "her", "him", "self", "lira", "female", "male", "human"}
                trigger = "lira_base, " if any(w in description.lower() for w in person_words) else ""
                prompt = f"{trigger}RAW photo, photorealistic, 8k, highly detailed, {description}"
                await ws.send_json({"type": "text", "delta": f"*Crafting an image: {description}...*\n"})
                try:
                    img_bytes, filename = await _handle_image(prompt)
                    import base64 as b64mod
                    await ws.send_json({
                        "type": "image",
                        "data": b64mod.b64encode(img_bytes).decode(),
                        "filename": filename,
                        "prompt": prompt,
                    })
                    await ws.send_json({"type": "done", "full_text": ""})
                    continue
                except Exception as e:
                    await ws.send_json({"type": "text", "delta": f"Image failed: {e}\n"})

            # Auto-search for factual questions
            search_context = ""
            if "?" in user_text and not user_text.startswith("/"):
                q_words = {"what", "when", "where", "who", "how", "why", "which", "latest", "current", "today", "news", "weather"}
                words = set(re_mod.findall(r'\b\w+\b', user_text.lower()))
                if words & q_words:
                    try:
                        clean_q = re_mod.sub(r'\b(what|when|where|who|how|why|which|is|the|a|an|does|do|did|can|could|would|will|are)\b', '', user_text, flags=re_mod.I)
                        clean_q = re_mod.sub(r'\?+', '', clean_q).strip()
                        results = await _web_search(clean_q or user_text, max_results=3)
                        if results:
                            search_context = (
                                "\n\n[SYSTEM: Current web search results. Use to answer accurately.]\n" +
                                "\n".join(f"- {r['title']}: {r['snippet']}" for r in results)
                            )
                            await ws.send_json({"type": "text", "delta": "(searched web)\n"})
                    except Exception:
                        pass

            await _handle_chat(ws, user_text + search_context)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@app.post("/api/generate-image")
async def api_generate_image(data: dict):
    if not settings.comfyui_workflow_path:
        from fastapi.responses import Response
        return Response(content=json.dumps({"error": "ComfyUI not configured"}), media_type="application/json", status_code=400)
    prompt = data.get("prompt", "")
    if not prompt:
        from fastapi.responses import Response
        return Response(content=json.dumps({"error": "prompt required"}), media_type="application/json", status_code=400)
    if "lira_base" not in prompt.lower():
        person_words = {"portrait", "woman", "man", "person", "face", "fae", "elf", "character", "girl", "boy", "lady", "her", "him", "self", "lira", "female", "male", "human"}
        if any(w in prompt.lower() for w in person_words):
            prompt = f"lira_base, {prompt}"
    try:
        img_bytes, filename = await _handle_image(prompt)
        from fastapi.responses import Response
        return Response(content=img_bytes, media_type="image/png", headers={"X-Filename": filename})
    except Exception as e:
        from fastapi.responses import Response
        return Response(content=json.dumps({"error": str(e)}), media_type="application/json", status_code=500)


# --- Snapshots ---
@app.get("/api/snapshots")
async def api_list_snapshots():
    return {"snapshots": list_snapshots()}


@app.post("/api/snapshots")
async def api_create_snapshot(data: dict):
    name = data.get("name", "Unnamed")
    result = save_snapshot(name, settings.lore_path)
    return {"snapshot": result}


@app.post("/api/snapshots/load")
async def api_load_snapshot(data: dict):
    file = data.get("file", "")
    snapshot = load_snapshot(file)
    if snapshot is None:
        from fastapi.responses import Response
        return Response(content=json.dumps({"error": "Snapshot not found"}), status_code=404)
    if "lore" in snapshot and snapshot["lore"]:
        lore_mgr.replace_all(snapshot["lore"].get("entries", []))
        lore_mgr.save()
    return {"loaded": snapshot.get("name", file)}


# --- Logs ---
@app.get("/api/logs")
async def api_list_logs():
    log_dir = Path(settings.log_dir)
    if not log_dir.exists():
        return {"sessions": []}
    sessions = []
    for f in sorted(log_dir.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append({
                "session_id": data.get("session_id", f.stem),
                "file": f.name,
                "message_count": len(data.get("messages", [])),
                "timestamp": data.get("messages", [{}])[0].get("timestamp", "") if data.get("messages") else "",
            })
        except Exception:
            sessions.append({"session_id": f.stem, "file": f.name, "message_count": 0, "timestamp": ""})
    return {"sessions": sessions}


@app.get("/api/logs/{session_id}")
async def api_get_log(session_id: str):
    log_path = Path(settings.log_dir) / f"{session_id}.json"
    if not log_path.exists():
        from fastapi.responses import Response
        return Response(content=json.dumps({"error": "Log not found"}), status_code=404)
    data = json.loads(log_path.read_text(encoding="utf-8"))
    return {"session_id": data.get("session_id", session_id), "messages": data.get("messages", [])}


# --- Personalities ---
@app.get("/api/personalities")
async def api_list_personalities():
    return {"personalities": list_personalities()}


@app.put("/api/personalities/{mode}")
async def api_update_personality(mode: str, data: dict):
    updated = update_personality(mode, data)
    return {"personality": updated}


# --- Lore CRUD ---
@app.delete("/api/lore/entry/{entry_id}")
async def api_delete_lore(entry_id: str):
    if lore_mgr.delete_entry(entry_id):
        lore_mgr.save()
        return {"deleted": entry_id}
    from fastapi.responses import Response
    return Response(content=json.dumps({"error": "Entry not found"}), status_code=404)


@app.delete("/api/lore/worldbook/{name}")
async def api_delete_worldbook(name: str):
    count = lore_mgr.delete_worldbook(name)
    if count > 0:
        lore_mgr.save()
    return {"deleted": name, "count": count}


@app.post("/api/lore/entry/{entry_id}/move")
async def api_move_entry(entry_id: str, data: dict):
    direction = data.get("direction", "up")
    result = lore_mgr.move_entry(entry_id, direction)
    if result is None:
        from fastapi.responses import Response
        return Response(content=json.dumps({"error": "Entry not found"}), status_code=404)
    lore_mgr.save()
    return {"entry": lore_mgr.as_dict([result])[0]}


@app.post("/api/lore/worldbook/{name}/move")
async def api_move_worldbook(name: str, data: dict):
    direction = data.get("direction", "up")
    ok = lore_mgr.move_worldbook(name, direction)
    if not ok:
        from fastapi.responses import Response
        return Response(content=json.dumps({"error": "Worldbook not found or cannot move"}), status_code=400)
    lore_mgr.save()
    return {"worldbook": name, "order": lore_mgr.worldbook_order()}


@app.patch("/api/lore/entry/{entry_id}")
async def api_quick_update_entry(entry_id: str, data: dict):
    updated = lore_mgr.update_entry(entry_id, data)
    if updated is None:
        from fastapi.responses import Response
        return Response(content=json.dumps({"error": "Entry not found"}), status_code=404)
    lore_mgr.save()
    return {"entry": lore_mgr.as_dict([updated])[0]}


@app.get("/api/lore/export")
async def api_export_lore(worldbook: str = ""):
    if worldbook:
        entries = lore_mgr.as_dict([e for e in lore_mgr.all_entries() if e.source_worldbook == worldbook])
    else:
        entries = lore_mgr.as_dict(lore_mgr.all_entries())
    return {"version": "2.0", "description": "Lira lore export", "entries": entries}


@app.post("/api/lore/import")
async def api_import_lore(data: dict):
    imported = data.get("entries", [])
    if not imported:
        return {"imported": 0, "error": "No entries in payload"}
    for entry in imported:
        lore_mgr.create_entry(
            title=entry.get("title", "Imported"),
            content=entry.get("content", ""),
            activation=entry.get("activation", "trigger"),
            modes=entry.get("modes", []),
            trigger_keywords=entry.get("trigger_keywords", []),
            source_worldbook=entry.get("source_worldbook", "Imported"),
            priority=entry.get("priority", 0),
        )
    lore_mgr.save()
    return {"imported": len(imported)}


@app.post("/api/lore/entry")
async def api_create_entry(data: dict):
    entry = lore_mgr.create_entry(
        title=data.get("title", "New Entry"),
        content=data.get("content", ""),
        activation=data.get("activation", "trigger"),
        modes=data.get("modes", []),
        trigger_keywords=data.get("trigger_keywords", []),
        source_worldbook=data.get("source_worldbook", "Custom"),
        priority=data.get("priority", 0),
    )
    lore_mgr.save()
    return {"entry": lore_mgr.as_dict([entry])[0]}


@app.post("/api/lore/worldbook")
async def api_create_worldbook(data: dict):
    name = data.get("name", "New Worldbook")
    modes = data.get("modes", [])
    lore_mgr.create_worldbook(name, modes)
    lore_mgr.save()
    return {"worldbook": name, "count": len([e for e in lore_mgr.all_entries() if e.source_worldbook == name])}


# --- Transcribe ---
@app.post("/api/transcribe")
async def api_transcribe(file: UploadFile = File(...)):
    import httpx as httpx_mod
    audio_bytes = await file.read()
    async with httpx_mod.AsyncClient(timeout=30) as client:
        resp = await client.post(
            settings.whisper_url,
            files={"file": (file.filename or "audio.wav", audio_bytes, file.content_type or "audio/wav")},
        )
        if resp.is_error:
            return {"text": "", "error": f"Whisper error: {resp.status_code}"}
        data = resp.json()
        return {"text": data.get("text", "")}


if __name__ == "__main__":
    import uvicorn
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")
    uvicorn.run("orchestrator.main:app", host=settings.host, port=settings.port, reload=True)
