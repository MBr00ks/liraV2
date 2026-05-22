import re
import random
import os
from dataclasses import dataclass, field
from typing import Optional

from src.logging import get_logger

logger = get_logger("reaction-sounds")

REACTION_MAPPING = {
    "giggle": ["giggle_01.wav", "giggle_02.wav", "giggle_03.wav"],
    "laugh": ["laugh_01.wav", "laugh_02.wav"],
    "sigh": ["sigh_01.wav", "sigh_02.wav", "sigh_03.wav"],
    "gasp": ["gasp_01.wav", "gasp_02.wav"],
    "moan": ["moan_01.wav", "moan_02.wav"],
    "breath": ["breath_01.wav", "breath_02.wav", "breath_03.wav"],
    "footsteps": ["footsteps_01.wav", "footsteps_02.wav"],
    "hum": ["hum_01.wav"],
    "sniffle": ["sniffle_01.wav"],
}

ACTION_PATTERN = re.compile(r"\*(\w+)\*")


@dataclass
class ReactionSound:
    name: str
    file_path: str
    duration_ms: float


class ReactionSoundEngine:
    def __init__(self, sound_dir: str = "public/audio/reactions"):
        self.sound_dir = sound_dir
        self._cache: dict[str, list[str]] = {}
        self._scan_directory()

    def _scan_directory(self) -> None:
        if not os.path.isdir(self.sound_dir):
            logger.warn("Reaction sound directory not found", {"path": self.sound_dir})
            return

        for root, _, files in os.walk(self.sound_dir):
            for f in files:
                if f.endswith(".wav"):
                    category = f.rsplit("_", 1)[0] if "_" in f else f.rsplit(".", 1)[0]
                    if category not in self._cache:
                        self._cache[category] = []
                    self._cache[category].append(os.path.join(root, f))

    def extract_actions(self, text: str) -> list[str]:
        matches = ACTION_PATTERN.findall(text)
        return [m.lower() for m in matches]

    def get_reaction_for_action(self, action: str) -> Optional[str]:
        action = action.lower().strip()

        for key, files in REACTION_MAPPING.items():
            if key in action or action in key:
                available = [f for f in files if f in self._cache.get(key, [])]
                if available:
                    return random.choice(available)
                return files[0]

        return None

    def get_all_reactions(self) -> dict[str, list[str]]:
        return {k: v for k, v in self._cache.items() if v}

    def health_check(self) -> bool:
        total = sum(len(v) for v in self._cache.values())
        return total > 0
