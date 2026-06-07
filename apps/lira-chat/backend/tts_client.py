import httpx


class TTSClient:
    def __init__(self, url: str = "http://localhost:19011/v1/audio/speech"):
        self._url = url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def synthesize(self, text: str, voice: str = "bf_isabella", speed: float = 1.0, mode: str = "") -> bytes | None:
        try:
            client = await self._get_client()
            resp = await client.post(self._url, json={
                "model": "tts-1",
                "input": text,
                "voice": voice,
                "speed": speed,
                "mode": mode,
            })
            resp.raise_for_status()
            return resp.content
        except Exception:
            return None

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
