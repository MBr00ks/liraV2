import re
import random
import os
import soundfile as sf
import numpy as np
from dataclasses import dataclass
from typing import Optional

from src.audio_utils import resample_to_target, apply_fades, extract_best_segment, pitch_shift, TARGET_SR
from src.log import get_logger

logger = get_logger("reaction-sounds")

ACTION_PATTERN = re.compile(r"\*(.+?)\*")
ORIGINAL_BREATH_RE = re.compile(r"breath_(inhale|exhale|calm|both)", re.I)
SOURCE_FILE_RE = re.compile(r"giggles_low|giggles_medium", re.I)

CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "moans": {"moan", "moaning"},
    "giggles": {"giggle", "giggling", "chuckle", "chuckling"},
    "orgasms": {"orgasm", "climax", "cumming", "cum"},
    "blowjob": {"blowjob", "sucking", "deep throat", "oral", "cock", "dick"},
    "breaths": {"breath", "exhale", "inhale", "sigh", "pant", "panting", "breathing heavily", "out of breath", "breathless", "aroused", "excited", "gasp", "gasping", "startled", "surprise"},
    "vocals": {"cough", "yawn", "shhh", "hush"},
}

CATEGORY_PITCH_SHIFT: dict[str, float] = {
    "moans": -0.75,
    "giggles": -3.0,
    "breaths": -1.5,
    "blowjob": -1.0,
    "orgasms": -1.0,
    "vocals": -0.5,
    "assortment": -1.0,
}


SPECIFIC_FILTER: dict[str, tuple[str, re.Pattern]] = {
    "sigh": ("breaths", re.compile(r"^sigh", re.I)),
    "sighs": ("breaths", re.compile(r"^sigh", re.I)),
    "sighing": ("breaths", re.compile(r"^sigh", re.I)),
    "yawn": ("vocals", re.compile(r"^yawn(?!_stutter)", re.I)),
    "cough": ("vocals", re.compile(r"^cough", re.I)),
    "shhh": ("vocals", re.compile(r"^shhh", re.I)),
    "stretch": ("vocals", re.compile(r"yawn_stutter", re.I)),
}


@dataclass
class ReactionSound:
    name: str
    file_path: str
    duration_ms: float


class ReactionSoundEngine:
    def __init__(self, sound_dir: str = "public/audio/reactions"):
        self.sound_dir = sound_dir
        self._cache: dict[str, list[tuple[str, np.ndarray]]] = {}
        self._scan_directory()

    def _scan_directory(self) -> None:
        if not os.path.isdir(self.sound_dir):
            logger.warn("Reaction sound directory not found", {"path": self.sound_dir})
            return

        count = 0
        for root, _, files in os.walk(self.sound_dir):
            category = os.path.basename(root)
            if not category:
                continue
            if category not in self._cache:
                self._cache[category] = []
            pitch_st = CATEGORY_PITCH_SHIFT.get(category, -1.5)
            for f in files:
                if not f.endswith(".wav"):
                    continue
                if ORIGINAL_BREATH_RE.search(f) or SOURCE_FILE_RE.search(f):
                    continue
                path = os.path.join(root, f)
                try:
                    data, orig_sr = sf.read(path, dtype="int16")
                    data = resample_to_target(data, orig_sr)
                    data = extract_best_segment(data, mode="max")
                    data = pitch_shift(data, semitones=pitch_st)
                    data = apply_fades(data)
                    self._cache[category].append((f, data))
                    count += 1
                except Exception as e:
                    logger.error("Failed to load reaction sound", {"file": f, "error": str(e)})

        counts = {k: len(v) for k, v in self._cache.items() if v}
        logger.info("Reaction sounds loaded", {"total": count, "categories": counts})

    def extract_actions(self, text: str) -> list[str]:
        matches = ACTION_PATTERN.findall(text)
        return [m.lower() for m in matches]

    def get_reaction_for_action(self, action: str) -> Optional[np.ndarray]:
        action = action.lower().strip()

        if action in SPECIFIC_FILTER:
            cat, pattern = SPECIFIC_FILTER[action]
            pool = self._cache.get(cat, [])
            matched = [d for fname, d in pool if pattern.search(fname)]
            if matched:
                return random.choice(matched)

        for category, keywords in CATEGORY_KEYWORDS.items():
            pool = self._cache.get(category, [])
            if not pool:
                continue
            for kw in keywords:
                if kw in action or action in kw:
                    return random.choice([d for _, d in pool])

        return None

    def get_all_reactions(self) -> dict[str, list[str]]:
        return {k: [d.shape for _, d in v] for k, v in self._cache.items() if v}

    def health_check(self) -> bool:
        total = sum(len(v) for v in self._cache.values())
        return total > 0
