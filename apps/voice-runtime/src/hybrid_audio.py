import re
import asyncio
from dataclasses import dataclass, field
from typing import Optional

from src.tts import KokoroClient, TTSResult
from src.audio_queue import AudioQueue, AudioItem
from src.reaction_sounds import ReactionSoundEngine
from src.logging import get_logger

logger = get_logger("hybrid-audio")

ACTION_PATTERN = re.compile(r"\*(\w+)\*")


@dataclass
class AudioOutput:
    tts_result: Optional[TTSResult] = None
    reaction_file: Optional[str] = None
    breathing_file: Optional[str] = None
    total_duration_ms: float = 0.0


class HybridAudioPipeline:
    def __init__(self):
        self.tts = KokoroClient()
        self.queue = AudioQueue()
        self.reactions = ReactionSoundEngine()
        self._breathing_enabled = True

    async def process_text(self, text: str, voice: Optional[str] = None) -> list[AudioOutput]:
        cleaned_text, actions = self._extract_actions(text)

        outputs: list[AudioOutput] = []

        for action in actions:
            reaction_file = self.reactions.get_reaction_for_action(action)
            if reaction_file:
                outputs.append(AudioOutput(reaction_file=reaction_file))

        if cleaned_text.strip():
            try:
                tts_result = await self.tts.synthesize(cleaned_text.strip(), voice=voice)
                outputs.append(AudioOutput(tts_result=tts_result, total_duration_ms=tts_result.duration_ms))
            except Exception as e:
                logger.error("TTS synthesis failed", {"error": str(e)})

        return outputs

    async def process_and_queue(self, text: str, voice: Optional[str] = None) -> bool:
        outputs = await self.process_text(text, voice)

        for output in outputs:
            if output.tts_result:
                import base64
                audio_data = base64.b64decode(output.tts_result.audio_base64)
                item = AudioItem(
                    id=f"tts_{len(text)}",
                    audio_data=audio_data,
                    duration_ms=output.tts_result.duration_ms,
                    interruptible=True,
                )
                await self.queue.enqueue(item)

            if output.reaction_file:
                try:
                    with open(output.reaction_file, "rb") as f:
                        reaction_data = f.read()
                    item = AudioItem(
                        id=f"reaction_{output.reaction_file}",
                        audio_data=reaction_data,
                        duration_ms=500,
                        priority=1,
                        interruptible=False,
                    )
                    await self.queue.enqueue(item)
                except FileNotFoundError:
                    logger.warn("Reaction file not found", {"file": output.reaction_file})

        return len(outputs) > 0

    async def interrupt(self) -> None:
        await self.queue.interrupt()
        logger.info("Hybrid audio interrupted")

    def _extract_actions(self, text: str) -> tuple[str, list[str]]:
        actions = ACTION_PATTERN.findall(text)
        cleaned = ACTION_PATTERN.sub("", text).strip()
        return cleaned, [a.lower() for a in actions]

    async def health_check(self) -> dict[str, bool]:
        return {
            "tts": await self.tts.health_check(),
            "reactions": self.reactions.health_check(),
            "queue": self.queue.queue_size < self.queue._max_size,
        }
