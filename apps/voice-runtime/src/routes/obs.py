from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from src.main import obs_bridge
from src.logging import get_logger

logger = get_logger("obs-route")

router = APIRouter()


class OBSStatusResponse(BaseModel):
    connected: bool
    tts_source_exists: bool = False
    tts_source_active: bool = False
    filters_active: list[str] = []


class VolumeResponse(BaseModel):
    source: str
    volume_db: float


class MuteResponse(BaseModel):
    source: str
    muted: bool


class FilterAction(BaseModel):
    source: str = "Kokoro TTS"
    filter_name: str
    enabled: bool


@router.get("/status", response_model=OBSStatusResponse)
async def get_obs_status():
    status = await obs_bridge.health_check()
    return OBSStatusResponse(
        connected=status.connected,
        tts_source_exists=status.tts_source_exists,
        tts_source_active=status.tts_source_active,
        filters_active=status.filters_active,
    )


@router.post("/source/volume", response_model=VolumeResponse)
async def set_source_volume(source: str = "Kokoro TTS", volume_db: float = 0.0):
    success = await obs_bridge.set_source_volume(source, volume_db)
    return VolumeResponse(source=source, volume_db=volume_db)


@router.get("/source/volume", response_model=Optional[VolumeResponse])
async def get_source_volume(source: str = "Kokoro TTS"):
    vol = await obs_bridge.get_source_volume(source)
    if vol is None:
        return None
    return VolumeResponse(source=source, volume_db=vol)


@router.post("/source/mute", response_model=MuteResponse)
async def toggle_source_mute(source: str = "Kokoro TTS"):
    new_state = await obs_bridge.toggle_source_mute(source)
    return MuteResponse(source=source, muted=bool(new_state))


@router.post("/source/mute/set", response_model=MuteResponse)
async def set_source_mute(source: str = "Kokoro TTS", muted: bool = True):
    await obs_bridge.set_source_mute(source, muted)
    return MuteResponse(source=source, muted=muted)


@router.get("/filters")
async def list_source_filters(source: str = "Kokoro TTS"):
    filters = await obs_bridge.get_source_filters(source)
    return {
        "source": source,
        "filters": [{"name": f["filterName"], "enabled": f["filterEnabled"]} for f in filters],
    }


@router.post("/filters/toggle")
async def toggle_filter(action: FilterAction):
    success = await obs_bridge.set_filter_enabled(action.source, action.filter_name, action.enabled)
    return {
        "source": action.source,
        "filter": action.filter_name,
        "enabled": action.enabled,
        "success": success,
    }


@router.get("/scenes")
async def list_scenes():
    scenes = await obs_bridge.get_scene_list()
    return {"scenes": [s["sceneName"] for s in scenes]}


@router.post("/scene/switch")
async def switch_scene(scene_name: str):
    success = await obs_bridge.set_current_scene(scene_name)
    return {"scene": scene_name, "success": success}
