import asyncio
import json
import base64
import logging
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

            conversation_history.append({"role": "user", "content": user_text})
            logger.log_message("user", user_text, {"mode": active_mode})

            assembled = assembler.build(active_mode, conversation_history[:-1], user_text)

            # Send debug info
            await ws.send_json({
                "type": "lore_injected",
                "lore": assembled["injected_lore"],
                "system_preview": assembled["system"][:500],
            })

            # Stream from Ollama — text only, no TTS chunking
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

            # Send full response to proxy for prosody + TTS
            if full_response.strip():
                try:
                    audio = await tts.synthesize(full_response.strip(), mode=active_mode)
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
