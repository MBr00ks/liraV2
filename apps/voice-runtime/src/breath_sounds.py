import os
import re
import random
import numpy as np
import soundfile as sf
from typing import Optional

from src.config import get_settings
from src.audio_utils import resample_to_target, apply_fades, extract_best_segment, pitch_shift, TARGET_SR
from src.log import get_logger

logger = get_logger("breath-sounds")

ORIGINAL_BREATH_RE = re.compile(r"breath_(inhale|exhale|calm|both)", re.I)

EMOTIONAL_ACTIONS = {"sigh", "tease", "whisper", "soft", "murmur", "breathe", "close", "gentle"}
EMOTIONAL_KEYWORDS = {"miss", "love", "wish", "feel", "soft", "warm", "careful", "delicate"}
GASP_ACTIONS = {"gasp", "startled", "shock", "surprise"}
COUGH_ACTIONS = {"cough", "hem"}
YAWN_ACTIONS = {"yawn", "tired"}
SHHH_ACTIONS = {"shhh", "hush", "quiet", "silence"}
HEAVY_BREATH_ACTIONS = {"pant", "breathing heavily", "heavy breathing", "out of breath", "arousal", "excited", "breathless"}
SOFT_BREATH_ACTIONS = {"soft breathing", "gentle breath", "calm breathing"}

CATEGORY_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("gasp", re.compile(r"gasp", re.I)),
    ("cough", re.compile(r"cough", re.I)),
    ("yawn", re.compile(r"yawn", re.I)),
    ("shhh", re.compile(r"shhh|shush|quiet", re.I)),
    ("breath_heavy", re.compile(r"breath_heavy|_heavy_", re.I)),
    ("breath_soft", re.compile(r"breath_soft|_soft_", re.I)),
    ("breath", re.compile(r"breath|inhale|exhale|calm", re.I)),
]


class BreathSoundEngine:
    def __init__(self, breath_dir: str | None = None, vocals_dir: str | None = None):
        settings = get_settings()
        self.breath_dir = breath_dir or os.path.join(settings.reaction_sound_dir, "breaths")
        self.vocals_dir = vocals_dir or os.path.join(settings.reaction_sound_dir, "vocals")
        self._clips: dict[str, list[dict]] = {
            "breath": [], "breath_heavy": [], "breath_soft": [],
            "gasp": [], "cough": [], "yawn": [], "shhh": [], "other": [],
        }
        self._scan_directory(self.breath_dir)
        self._scan_directory(self.vocals_dir)

    def _categorize(self, filename: str) -> str:
        for cat, pattern in CATEGORY_PATTERNS:
            if pattern.search(filename):
                return cat
        return "other"

    def _scan_directory(self, directory: str) -> None:
        if not os.path.isdir(directory):
            logger.debug("Sound directory not found", {"path": directory})
            return
        for f in sorted(os.listdir(directory)):
            if not f.endswith(".wav"):
                continue
            if ORIGINAL_BREATH_RE.search(f):
                continue
            path = os.path.join(directory, f)
            try:
                data, orig_sr = sf.read(path, dtype="int16")
                data = resample_to_target(data, orig_sr)
                data = extract_best_segment(data, mode="min")
                data = pitch_shift(data, semitones=-1.5)
                data = apply_fades(data)
                cat = self._categorize(f)
                self._clips[cat].append({"file": f, "path": path, "data": data, "sr": TARGET_SR})
                logger.debug("Loaded sound clip", {"category": cat, "file": f, "samples": len(data)})
            except Exception as e:
                logger.error("Failed to load sound clip", {"file": f, "error": str(e)})
        counts = {k: len(v) for k, v in self._clips.items() if v}
        logger.info("Sound clips loaded", {"categories": counts})

    def should_add_breath(
        self,
        chunk_index: int,
        total_chunks: int,
        actions: list[str] | None = None,
        chunk_text: str = "",
        full_text: str = "",
    ) -> tuple[bool, str]:
        if not any(self._clips.values()):
            return False, ""

        if chunk_index == 0:
            return False, ""

        if actions:
            for action in actions:
                action_lower = action.lower().strip()
                for hb in HEAVY_BREATH_ACTIONS:
                    if hb in action_lower:
                        return True, "breath_heavy"
                for sb in SOFT_BREATH_ACTIONS:
                    if sb in action_lower:
                        return True, "breath_soft"
                for gas in GASP_ACTIONS:
                    if gas in action_lower:
                        return True, "gasp"
                for cgh in COUGH_ACTIONS:
                    if cgh in action_lower:
                        return True, "cough"
                for ywn in YAWN_ACTIONS:
                    if ywn in action_lower:
                        return True, "yawn"
                for sh in SHHH_ACTIONS:
                    if sh in action_lower:
                        return True, "shhh"
                if action_lower in EMOTIONAL_ACTIONS:
                    return True, "breath_soft"

        if random.random() < 0.30:
            return True, "breath_soft"

        return False, ""

    def get_breath(self, category: str = "breath", volume_scale: float | None = None) -> np.ndarray | None:
        pool = self._clips.get(category, [])
        if not pool:
            if category in ("breath_heavy", "breath_soft"):
                pool = self._clips.get("breath", [])
            if not pool:
                for fallback in self._clips.values():
                    if fallback:
                        pool = fallback
                        break
        if not pool:
            return None

        clip = random.choice(pool)
        data = clip["data"].copy().astype(np.float32)

        vol = volume_scale if volume_scale is not None else random.uniform(0.85, 1.0)
        data *= vol

        data = np.clip(data, -32768, 32767).astype(np.int16)
        return data

    def get_random_breath(self, volume_scale: float | None = None) -> np.ndarray | None:
        return self.get_breath("breath", volume_scale)

    @property
    def is_loaded(self) -> bool:
        return any(self._clips.values())

    def health_check(self) -> bool:
        return self.is_loaded
