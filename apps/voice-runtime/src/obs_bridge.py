import json
import hashlib
import base64
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from src.config import get_settings
from src.log import get_logger

logger = get_logger("obs-bridge")


class OBSConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class OBSStatus:
    connected: bool = False
    connected_time: float = 0.0
    version: str = ""
    tts_source_exists: bool = False
    tts_source_active: bool = False
    filters_active: list[str] = field(default_factory=list)


REQUEST_TIMEOUT = 10.0
RECONNECT_DELAY = 5.0


class OBSBridge:
    def __init__(self) -> None:
        settings = get_settings()
        self.host = settings.obs_host
        self.port = settings.obs_port
        self.password = settings.obs_password
        self.tts_source_name = settings.obs_tts_source
        self.enabled = settings.obs_enabled
        self.state = OBSConnectionState.DISCONNECTED
        self._ws: Optional[Any] = None
        self._request_id = 0
        self._status = OBSStatus()

    @property
    def ws_url(self) -> str:
        return f"ws://{self.host}:{self.port}"

    async def connect(self) -> bool:
        if not self.enabled:
            logger.info("OBS integration disabled, skipping connection")
            return False
        if self.state == OBSConnectionState.CONNECTED:
            return True

        self.state = OBSConnectionState.CONNECTING
        try:
            import websockets

            self._ws = await websockets.connect(self.ws_url, close_timeout=5)
            hello = json.loads(await self._ws.recv())

            if hello.get("op") != 0:
                raise RuntimeError(f"Unexpected OBS handshake: {hello.get('op')}")

            auth_required = hello.get("d", {}).get("authentication", {}).get("challenge") if True else None
            identify = {"op": 1, "d": {"rpcVersion": 1}}

            if auth_required and self.password:
                challenge = hello["d"]["authentication"]["challenge"]
                salt = hello["d"]["authentication"].get("salt", "")
                secret = base64.b64encode(
                    hashlib.sha256((self.password + salt).encode()).digest()
                ).decode()
                auth = base64.b64encode(
                    hashlib.sha256((secret + challenge).encode()).digest()
                ).decode()
                identify["d"]["authentication"] = auth
            elif auth_required:
                raise RuntimeError("OBS requires authentication but no password configured")

            await self._ws.send(json.dumps(identify))
            identified = json.loads(await self._ws.recv())

            if identified.get("op") != 2:
                raise RuntimeError(f"OBS identification failed: {identified}")

            self.state = OBSConnectionState.CONNECTED
            self._status.connected = True
            logger.info("Connected to OBS WebSocket",
                        {"host": self.host, "port": self.port, "version": identified.get("d", {}).get("obsVersion", "")})
            return True

        except Exception as e:
            self.state = OBSConnectionState.ERROR
            self._status.connected = False
            logger.warn("Failed to connect to OBS", {"error": str(e), "host": self.host, "port": self.port})
            return False

    async def disconnect(self) -> None:
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._ws = None
        self.state = OBSConnectionState.DISCONNECTED
        self._status.connected = False
        logger.info("Disconnected from OBS")

    async def _send_request(self, request_type: str, request_data: Optional[dict] = None) -> Optional[dict]:
        if self.state != OBSConnectionState.CONNECTED or not self._ws:
            return None

        self._request_id += 1
        rid = str(self._request_id)
        msg = {"op": 6, "d": {"requestType": request_type, "requestId": rid}}
        if request_data:
            msg["d"]["requestData"] = request_data

        try:
            await self._ws.send(json.dumps(msg))
            while True:
                resp = json.loads(await self._ws.recv())
                if resp.get("op") == 7 and resp.get("d", {}).get("requestId") == rid:
                    return resp["d"]
        except Exception as e:
            logger.error("OBS request failed", {"request": request_type, "error": str(e)})
            self.state = OBSConnectionState.ERROR
            return None

    async def get_scene_list(self) -> list[dict]:
        result = await self._send_request("GetSceneList")
        return (result or {}).get("responseData", {}).get("scenes", [])

    async def get_source_active(self, source_name: str) -> bool:
        result = await self._send_request("GetInputSettings", {"inputName": source_name})
        return result is not None

    async def set_source_volume(self, source_name: str, volume_db: float) -> bool:
        result = await self._send_request("SetInputVolume", {
            "inputName": source_name,
            "inputVolumeDb": volume_db,
        })
        return result is not None

    async def get_source_volume(self, source_name: str) -> Optional[float]:
        result = await self._send_request("GetInputVolume", {"inputName": source_name})
        if result:
            return result.get("responseData", {}).get("inputVolumeDb")
        return None

    async def toggle_source_mute(self, source_name: str) -> Optional[bool]:
        current = await self._send_request("GetInputMute", {"inputName": source_name})
        if current is None:
            return None
        is_muted = current.get("responseData", {}).get("inputMuted", False)
        await self._send_request("SetInputMute", {
            "inputName": source_name,
            "inputMuted": not is_muted,
        })
        return not is_muted

    async def set_source_mute(self, source_name: str, muted: bool) -> bool:
        result = await self._send_request("SetInputMute", {
            "inputName": source_name,
            "inputMuted": muted,
        })
        return result is not None

    async def get_source_filters(self, source_name: str) -> list[dict]:
        result = await self._send_request("GetSourceFilterList", {"sourceName": source_name})
        if result:
            return result.get("responseData", {}).get("filters", [])
        return []

    async def set_filter_enabled(self, source_name: str, filter_name: str, enabled: bool) -> bool:
        result = await self._send_request("SetSourceFilterEnabled", {
            "sourceName": source_name,
            "filterName": filter_name,
            "filterEnabled": enabled,
        })
        return result is not None

    async def set_current_scene(self, scene_name: str) -> bool:
        result = await self._send_request("SetCurrentProgramScene", {"sceneName": scene_name})
        return result is not None

    async def get_stats(self) -> dict:
        result = await self._send_request("GetStats")
        return (result or {}).get("responseData", {})

    async def ensure_tts_source(self) -> tuple[bool, list[str]]:
        filters: list[str] = []
        exists = await self._send_request("GetInputSettings", {"inputName": self.tts_source_name})
        if exists is None:
            return False, filters
        filter_list = await self.get_source_filters(self.tts_source_name)
        filters = [f["filterName"] for f in filter_list if f.get("filterEnabled", False)]
        return True, filters

    async def health_check(self) -> OBSStatus:
        if self.state != OBSConnectionState.CONNECTED:
            status = OBSStatus(connected=False)
        else:
            try:
                stats = await self.get_stats()
                source_exists = await self._send_request("GetInputSettings", {"inputName": self.tts_source_name})
                source_active = source_exists is not None
                filters = await self.get_source_filters(self.tts_source_name) if source_active else []
                active_filters = [f["filterName"] for f in filters if f.get("filterEnabled", False)]

                self._status = OBSStatus(
                    connected=True,
                    tts_source_exists=source_active,
                    tts_source_active=source_active,
                    filters_active=active_filters,
                )
            except Exception as e:
                logger.warn("OBS health check failed", {"error": str(e)})
                self.state = OBSConnectionState.ERROR
                self._status = OBSStatus(connected=False)
        return self._status
