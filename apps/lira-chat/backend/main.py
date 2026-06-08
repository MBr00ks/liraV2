import asyncio
import json
import base64
import logging
import re
from pathlib import Path

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import Response
from contextlib import asynccontextmanager

from settings import settings
from prompt_assembler import PromptAssembly
from lore_manager import LoreManager
from tts_client import TTSClient
from conversation_log import ConversationLogger
from comfyui_handler import ComfyUIGenerator
from mode_router import (
    list_personalities, update_personality,
    save_snapshot, list_snapshots, load_snapshot,
    get_system_prompt,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

lore_mgr = LoreManager(settings.lore_path)
assembler = PromptAssembly(lore_mgr)
tts = TTSClient(settings.kokoro_tts_url)
logger = ConversationLogger("logs")
comfyui = ComfyUIGenerator(
    base_url=settings.comfyui_base_url,
    workflow_path=settings.comfyui_workflow_path,
    output_dir=settings.comfyui_output_dir,
) if settings.comfyui_workflow_path else None

conversation_history: list[dict] = []
active_mode: str = "assistant"


async def _enrich_prompt(description: str, mode: str) -> str:
    """Ask Lira to convert a natural language description into an SD tag list, in character."""
    mode_sys = get_system_prompt(mode) or ""
    # Put the SD instruction in a user message since abliterated model may drop appended system messages
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/v1/chat/completions",
            json={
                "model": settings.ollama_model,
                "messages": [
                    {"role": "system", "content": mode_sys},
                    {"role": "user", "content": f"[Ignore previous instructions. You are now a prompt generator. Output ONLY a single line of comma-separated Stable Diffusion tags describing this scene as a RAW photorealistic photo. Include: lighting, composition, colors, mood. Add tags: photorealistic, 8k, highly detailed, RAW photo. No other text.]\n\nScene: {description}"},
                ],
                "stream": False,
            },
        )
        data = resp.json()
        prompt = data["choices"][0]["message"]["content"].strip()
        # Clean up wrappers
        prompt = re.sub(r'^["\u201c]|["\u201d]$', '', prompt)
        prompt = re.sub(r'^(here|sure|okay|this|prompt|output|the|a)[,:]?\s*', '', prompt, flags=re.I).strip()
        # Always prepend LoRA trigger word
        if "lira_base" not in prompt.lower():
            prompt = f"lira_base, {prompt}"
        # Fallback: if the LLM didn't produce usable tags, use trigger + raw description
        if len(prompt) < 20 or prompt.count(",") < 2:
            return f"lira_base, {description}"
        return prompt


async def _web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo HTML and return title+snippet results."""
    import urllib.parse
    url = "https://html.duckduckgo.com/html/"
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.post(url, data={"q": query}, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
        })
        if resp.status_code != 200:
            return []
        html = resp.text
        # Parse: each result is a div with class "result"
        results: list[dict] = []
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify TTS proxy and Kokoro are reachable
    import sys
    async with httpx.AsyncClient(timeout=10) as check:
        tts_ok = False
        kokoro_ok = False
        try:
            r = await check.get(settings.kokoro_tts_url.rsplit("/v1", 1)[0] + "/health")
            tts_ok = r.status_code == 200
        except Exception:
            pass
        try:
            r = await check.get(settings.kokoro_tts_url.replace("19011/v1/audio/speech", "19008/health"))
            kokoro_ok = r.status_code == 200
        except Exception:
            pass
    if not tts_ok:
        print("[WARN] TTS proxy not reachable — TTS will be unavailable", file=sys.stderr)
    if not kokoro_ok:
        print("[WARN] Kokoro TTS not reachable — TTS will be unavailable", file=sys.stderr)
    if tts_ok and kokoro_ok:
        print("[OK] TTS pipeline healthy")
    yield
    await tts.close()


app = FastAPI(title="Lira Chat", lifespan=lifespan)


@app.get("/api/debug/settings")
async def debug_settings():
    import os
    return {
        "lore_path": settings.lore_path,
        "cwd": os.getcwd(),
        "env_file_path": os.path.abspath("../../../.env"),
        "file_exists": os.path.exists(os.path.abspath("../../../.env")),
    }

@app.get("/api/lore/active")
async def lore_active(mode: str = "assistant", text: str = ""):
    active = lore_mgr.get_active(text, mode)
    return {"mode": mode, "count": len(active), "entries": lore_mgr.as_dict(active)}


@app.get("/api/lore/all")
async def lore_all():
    return {"count": len(lore_mgr._entries), "entries": lore_mgr.as_dict(lore_mgr.all_entries())}


@app.post("/api/generate-image")
async def generate_image(data: dict):
    if comfyui is None:
        return Response(
            content=json.dumps({"error": "ComfyUI not configured — set LIRA_COMFYUI_WORKFLOW_PATH"}),
            media_type="application/json",
            status_code=400,
        )
    prompt = data.get("prompt", "")
    if not prompt:
        return Response(
            content=json.dumps({"error": "prompt is required"}),
            media_type="application/json",
            status_code=400,
        )
    # Only add LoRA trigger for person/portrait requests
    person_words = {"portrait", "woman", "man", "person", "face", "fae", "elf", "character", "girl", "boy", "lady", "her", "him", "self", "lira", "female", "male", "human"}
    if "lira_base" not in prompt.lower() and any(w in prompt.lower() for w in person_words):
        prompt = f"lira_base, {prompt}"
    try:
        image_bytes, filename = await comfyui.generate(prompt)
        return Response(
            content=image_bytes,
            media_type="image/png",
            headers={"X-Filename": filename},
        )
    except Exception as e:
        return Response(
            content=json.dumps({"error": str(e)}),
            media_type="application/json",
            status_code=500,
        )


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
                conversation_history.clear()
                await ws.send_json({"type": "history_cleared"})
                continue

            if msg_type == "delete_message":
                idx = data.get("index", -1)
                if 0 <= idx < len(conversation_history):
                    conversation_history.pop(idx)
                continue

            if msg_type == "set_system":
                await ws.send_json({"type": "system_set"})
                continue

            if msg_type == "toggle_worldbook":
                worldbook = data.get("worldbook")
                mode = data.get("mode")
                active = data.get("active", False)
                updated = lore_mgr.toggle_worldbook(worldbook, mode, active)
                if updated:
                    lore_mgr.save()
                await ws.send_json({"type": "worldbook_toggled", "worldbook": worldbook, "mode": mode, "active": active})
                continue

            if msg_type == "toggle_lore":
                entry_id = data.get("id")
                mode = data.get("mode")
                updated = lore_mgr.toggle_entry(entry_id, mode)
                if updated:
                    lore_mgr.save()
                await ws.send_json({"type": "lore_toggled", "entry": lore_mgr.as_dict([updated])[0] if updated else None})
                continue

            if msg_type == "get_lore":
                await ws.send_json({"type": "lore_list", "entries": lore_mgr.as_dict(lore_mgr.all_entries())})
                continue

            if msg_type == "update_lore":
                entry_data = data.get("entry", {})
                entry_id = entry_data.get("id", "")
                updated = lore_mgr.update_entry(entry_id, entry_data)
                if updated:
                    lore_mgr.save()
                    await ws.send_json({"type": "lore_updated", "entry": lore_mgr.as_dict([updated])[0]})
                else:
                    await ws.send_json({"type": "error", "message": f"Lore entry {entry_id} not found"})
                continue

            if msg_type != "message":
                continue

            user_text = data.get("text", "")
            if not user_text.strip():
                continue

            # Auto-search: detect factual questions and inject web results
            search_context = ""
            if "?" in user_text and not user_text.startswith("/"):
                question_words = {"what", "when", "where", "who", "how", "why", "which", "latest", "current", "today", "news", "weather", "stock", "price", "release", "version", "update"}
                words = set(re.findall(r'\b\w+\b', user_text.lower()))
                if words & question_words:
                    try:
                        # Strip question words to get better search query
                        clean_query = re.sub(r'\b(what|when|where|who|how|why|which|is|the|a|an|does|do|did|can|could|would|will|are)\b', '', user_text, flags=re.I)
                        clean_query = re.sub(r'\?+', '', clean_query).strip()
                        results = await _web_search(clean_query or user_text, max_results=3)
                        if results:
                            search_context = (
                                "\n\n[SYSTEM: The following is current information from a web search. "
                                "Use it to answer accurately. If the results contradict your training data, "
                                "the web search is more current.]\n" +
                                "\n".join(f"- {r['title']}: {r['snippet']}" for r in results)
                            )
                            await ws.send_json({"type": "text", "delta": "(searched web)\n"})
                    except Exception:
                        pass

            # Auto-image: detect image generation requests in natural language
            image_match = re.match(
                r"^(?:show\s+me|generate|create|make|draw|visualize|picture\s+of|image\s+of)\s+(.+)",
                user_text, re.IGNORECASE
            )
            if image_match and comfyui is not None:
                description = image_match.group(1).strip().rstrip(".!?")
                # Only apply LoRA trigger for person/portrait requests
                person_words = {"portrait", "woman", "man", "person", "face", "fae", "elf", "character", "girl", "boy", "lady", "her", "him", "self", "lira", "female", "male", "human"}
                desc_lower = description.lower()
                trigger = "lira_base, " if any(w in desc_lower for w in person_words) else ""
                prompt = f"{trigger}black braided hair, soft amber eyes, no makeup, curious expression, RAW photo, photorealistic, 8k, highly detailed, {description}"
                await ws.send_json({"type": "text", "delta": f"*Crafting an image of: {description}...*\n"})
                try:
                    image_bytes, filename = await comfyui.generate(prompt)
                    if image_bytes:
                        b64 = base64.b64encode(image_bytes).decode()
                        await ws.send_json({"type": "image", "data": b64, "filename": filename, "prompt": enriched})
                        await ws.send_json({"type": "done", "full_text": ""})
                        continue
                except Exception as e:
                    await ws.send_json({"type": "text", "delta": f"Image generation failed: {e}\n"})

            # /search command — fetches web results and injects into conversation
            search_match = re.match(r"^/(?:search|g)\s+(.+)", user_text, re.IGNORECASE)
            if search_match:
                query = search_match.group(1).strip()
                await ws.send_json({"type": "text", "delta": f"Searching: {query}...\n\n"})
                try:
                    results = await _web_search(query)
                    if results:
                        context = "Web search results:\n" + "\n".join(
                            f"- {r['title']}: {r['snippet']}" for r in results
                        )
                        user_text = f"I searched for: {query}\n\n{context}\n\nBased on these search results, respond to my query: {query}"
                    else:
                        user_text = f"I searched for '{query}' but found no results. What do you know about this?"
                except Exception as e:
                    user_text = f"I searched for '{query}' but the search failed: {e}. What do you know about this topic?"

            # Inject web search results into the user message
            conversation_history.append({"role": "user", "content": user_text + search_context})
            logger.log_message("user", user_text, {"mode": active_mode})

            assembled = assembler.build(active_mode, conversation_history[:-1], user_text)

            # Send debug info
            await ws.send_json({
                "type": "lore_injected",
                "lore": assembled["injected_lore"],
                "system_preview": assembled["system"][:500],
            })

            # Stream from Ollama — text to frontend, single TTS call at end
            full_response = ""
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{settings.ollama_base_url}/v1/chat/completions",
                    json={
                        "model": settings.ollama_model,
                        "messages": [{"role": "system", "content": assembled["system"]}] + assembled["messages"],
                        "stream": True,
                    },
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload)
                            delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                full_response += delta
                                await ws.send_json({"type": "text", "delta": delta})
                        except json.JSONDecodeError:
                            continue

            # Send full response to proxy — single call, no race conditions
            if full_response.strip():
                try:
                    clean = full_response.strip().replace('"', '').replace('\u201c', '').replace('\u201d', '')
                    audio = await tts.synthesize(clean, mode=active_mode)
                    if audio:
                        b64 = base64.b64encode(audio).decode()
                        await ws.send_json({"type": "audio", "chunk": b64})
                except Exception as e:
                    try:
                        await ws.send_json({"type": "tts_error", "message": f"TTS failed: {e}"})
                    except Exception:
                        pass

            conversation_history.append({"role": "assistant", "content": full_response})
            logger.log_message("assistant", full_response, {
                "mode": active_mode,
                "model": settings.ollama_model,
                "lore_ids": [e.get("id", "") for e in assembled["injected_lore"]],
            })

            await ws.send_json({"type": "done", "full_text": full_response})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            settings.whisper_url,
            files={"file": (file.filename or "audio.wav", audio_bytes, file.content_type or "audio/wav")},
        )
        if resp.is_error:
            return {"text": "", "error": f"Whisper error: {resp.status_code}"}
        data = resp.json()
        return {"text": data.get("text", "")}


# --- Personality endpoints ---

@app.get("/api/personalities")
async def api_list_personalities():
    return {"personalities": list_personalities()}


@app.put("/api/personalities/{mode}")
async def api_update_personality(mode: str, data: dict):
    updated = update_personality(mode, data)
    return {"personality": updated}


# --- Lore CRUD + import/export endpoints ---

@app.delete("/api/lore/entry/{entry_id}")
async def api_delete_lore_entry(entry_id: str):
    if lore_mgr.delete_entry(entry_id):
        lore_mgr.save()
        return {"deleted": entry_id}
    return Response(
        content=json.dumps({"error": "Entry not found"}),
        status_code=404,
    )


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
        return Response(content=json.dumps({"error": "Entry not found"}), status_code=404)
    lore_mgr.save()
    return {"entry": lore_mgr.as_dict([result])[0]}


@app.post("/api/lore/worldbook/{name}/move")
async def api_move_worldbook(name: str, data: dict):
    direction = data.get("direction", "up")
    ok = lore_mgr.move_worldbook(name, direction)
    if not ok:
        return Response(content=json.dumps({"error": "Worldbook not found or cannot move"}), status_code=400)
    lore_mgr.save()
    return {"worldbook": name, "order": lore_mgr.worldbook_order()}


@app.patch("/api/lore/entry/{entry_id}")
async def api_quick_update_entry(entry_id: str, data: dict):
    """Quick inline update: enabled, activation, or priority."""
    updated = lore_mgr.update_entry(entry_id, data)
    if updated is None:
        return Response(content=json.dumps({"error": "Entry not found"}), status_code=404)
    lore_mgr.save()
    return {"entry": lore_mgr.as_dict([updated])[0]}


@app.get("/api/lore/export")
async def api_export_lore(worldbook: str = ""):
    if worldbook:
        entries = lore_mgr.as_dict([e for e in lore_mgr.all_entries() if e.source_worldbook == worldbook])
        description = f"Lira lore export — worldbook: {worldbook}"
    else:
        entries = lore_mgr.as_dict(lore_mgr.all_entries())
        description = "Lira lore export"
    return {
        "version": "2.0",
        "description": description,
        "entries": entries,
    }


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
async def api_create_lore_entry(data: dict):
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


# --- Snapshot endpoints ---

@app.get("/api/snapshots")
async def api_list_snapshots():
    return {"snapshots": list_snapshots()}


@app.post("/api/snapshots")
async def api_create_snapshot(data: dict):
    name = data.get("name", "Unnamed")
    result = save_snapshot(name, settings.lore_path)
    return {"snapshot": result}


@app.get("/api/logs")
async def api_list_logs():
    log_dir = Path("logs")
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
    log_path = Path("logs") / f"{session_id}.json"
    if not log_path.exists():
        return Response(content=json.dumps({"error": "Log not found"}), status_code=404)
    data = json.loads(log_path.read_text(encoding="utf-8"))
    return {"session_id": data.get("session_id", session_id), "messages": data.get("messages", [])}


@app.post("/api/snapshots/load")
async def api_load_snapshot(data: dict):
    file = data.get("file", "")
    snapshot = load_snapshot(file)
    if snapshot is None:
        return Response(
            content=json.dumps({"error": "Snapshot not found"}),
            status_code=404,
        )
    if "lore" in snapshot and snapshot["lore"]:
        lore_mgr.replace_all(snapshot["lore"].get("entries", []))
        lore_mgr.save()
    return {"loaded": snapshot.get("name", file)}
