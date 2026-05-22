import asyncio
from dataclasses import dataclass, field
from typing import Optional
from collections import deque

from src.logging import get_logger

logger = get_logger("audio-queue")


@dataclass
class AudioItem:
    id: str
    audio_data: bytes
    duration_ms: float
    priority: int = 0
    interruptible: bool = True


class AudioQueue:
    def __init__(self, max_size: int = 50):
        self._queue: deque[AudioItem] = deque()
        self._max_size = max_size
        self._playing: Optional[AudioItem] = None
        self._interrupted = False
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()

    async def enqueue(self, item: AudioItem) -> bool:
        async with self._lock:
            if len(self._queue) >= self._max_size:
                logger.warn("Audio queue full, dropping item", {"item_id": item.id})
                return False

            self._queue.append(item)
            self._not_empty.set()
            logger.debug("Audio item enqueued", {"item_id": item.id, "queue_size": len(self._queue)})
            return True

    async def dequeue(self, timeout: float = 5.0) -> Optional[AudioItem]:
        try:
            await asyncio.wait_for(self._not_empty.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

        async with self._lock:
            if not self._queue:
                self._not_empty.clear()
                return None

            item = self._queue.popleft()
            if not self._queue:
                self._not_empty.clear()
            return item

    async def interrupt(self) -> Optional[AudioItem]:
        async with self._lock:
            self._interrupted = True
            current = self._playing
            self._playing = None
            self._queue.clear()
            self._not_empty.clear()
            logger.info("Audio queue interrupted", {"was_playing": current.id if current else None})
            return current

    def mark_playing(self, item: AudioItem) -> None:
        self._playing = item
        self._interrupted = False

    def mark_done(self, item_id: str) -> None:
        if self._playing and self._playing.id == item_id:
            self._playing = None

    @property
    def is_playing(self) -> bool:
        return self._playing is not None

    @property
    def is_interrupted(self) -> bool:
        return self._interrupted

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    async def clear(self) -> None:
        async with self._lock:
            self._queue.clear()
            self._not_empty.clear()
            logger.info("Audio queue cleared")
