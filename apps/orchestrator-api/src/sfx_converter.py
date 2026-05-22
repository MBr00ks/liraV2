import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.emotion_engine import EmotionalState, Realm, ProsodyMode
from src.logging import get_logger

logger = get_logger("sfx-converter")


class SFXCategory(Enum):
    SOFT_LAUGH = "soft_laugh"
    AMUSED_HUM = "amused_hum"
    PLEASED_BREATH = "pleased_breath"
    PLAYFUL_GIGGLE = "playful_giggle"
    SMALL_SIGH = "small_sigh"
    ANNOYED_BREATH = "annoyed_breath"
    DRY_EXHALE = "dry_exhale"
    THOUGHTFUL_HUM = "thoughtful_hum"
    PAUSE_BREATH = "pause_breath"
    SLOWER_BREATH = "slower_breath"
    WARMER_VOCAL = "warmer_vocal"
    NONE = "none"


@dataclass
class SFXEvent:
    sfx: SFXCategory
    file: str
    timing: str = "pre-speech"
    volume: float = 0.8


@dataclass
class ConvertedResponse:
    spoken_text: str
    sfx: Optional[SFXEvent] = None
    prosody: Optional[str] = None


ACTION_PATTERNS = [
    (r"\*([^*]*(?:laugh|giggle|chuckle|smirk|smile)[^*]*)\*", SFXCategory.SOFT_LAUGH, "pre-speech"),
    (r"\*([^*]*(?:sigh|exhale|breath)[^*]*)\*", SFXCategory.SMALL_SIGH, "pre-speech"),
    (r"\*([^*]*(?:hum|mm|think)[^*]*)\*", SFXCategory.THOUGHTFUL_HUM, "pre-speech"),
    (r"\*([^*]*(?:gasp|sharp breath)[^*]*)\*", SFXCategory.PAUSE_BREATH, "pre-speech"),
    (r"\*([^*]*(?:leans|tilts|shifts)[^*]*)\*", SFXCategory.NONE, "none"),
    (r"\*([^*]*(?:eyes|gaze|look)[^*]*)\*", SFXCategory.NONE, "none"),
    (r"\*([^*]*(?:pause|silence|quiet)[^*]*)\*", SFXCategory.PAUSE_BREATH, "pre-speech"),
    (r"\(([^)]*(?:laugh|giggle|smile)[^)]*)\)", SFXCategory.SOFT_LAUGH, "pre-speech"),
    (r"\(([^)]*(?:sigh|breath)[^)]*)\)", SFXCategory.SMALL_SIGH, "pre-speech"),
]

EMOTION_SFX_FALLBACK: dict[EmotionalState, SFXCategory] = {
    EmotionalState.PLAYFUL: SFXCategory.AMUSED_HUM,
    EmotionalState.FRUSTRATED: SFXCategory.DRY_EXHALE,
    EmotionalState.CURIOUS: SFXCategory.THOUGHTFUL_HUM,
    EmotionalState.FLIRTATIOUS: SFXCategory.WARMER_VOCAL,
    EmotionalState.PROTECTIVE: SFXCategory.PLEASED_BREATH,
}

SFX_FILE_MAP: dict[SFXCategory, str] = {
    SFXCategory.SOFT_LAUGH: "soft_laugh_01.wav",
    SFXCategory.AMUSED_HUM: "amused_hum_01.wav",
    SFXCategory.PLEASED_BREATH: "pleased_breath_01.wav",
    SFXCategory.PLAYFUL_GIGGLE: "playful_giggle_01.wav",
    SFXCategory.SMALL_SIGH: "small_sigh_01.wav",
    SFXCategory.ANNOYED_BREATH: "annoyed_breath_01.wav",
    SFXCategory.DRY_EXHALE: "dry_exhale_01.wav",
    SFXCategory.THOUGHTFUL_HUM: "thoughtful_hum_01.wav",
    SFXCategory.PAUSE_BREATH: "pause_breath_01.wav",
    SFXCategory.SLOWER_BREATH: "slower_breath_01.wav",
    SFXCategory.WARMER_VOCAL: "warmer_vocal_01.wav",
    SFXCategory.NONE: "",
}


def strip_action_markers(text: str) -> str:
    cleaned = re.sub(r"\*[^*]*\*", "", text)
    cleaned = re.sub(r"\([^)]*\)", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def detect_sfx_from_text(text: str, emotion: EmotionalState, realm: Realm) -> Optional[SFXEvent]:
    for pattern, sfx_category, timing in ACTION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if sfx_category == SFXCategory.NONE:
                return None
            file_name = SFX_FILE_MAP.get(sfx_category, "")
            if not file_name:
                return None
            return SFXEvent(sfx=sfx_category, file=file_name, timing=timing)

    fallback = EMOTION_SFX_FALLBACK.get(emotion)
    if fallback and realm == Realm.BETWEEN:
        file_name = SFX_FILE_MAP.get(fallback, "")
        if file_name:
            return SFXEvent(sfx=fallback, file=file_name, timing="pre-speech", volume=0.6)

    return None


def convert_response(
    raw_text: str,
    emotion: EmotionalState,
    realm: Realm,
    prosody: Optional[ProsodyMode] = None,
) -> ConvertedResponse:
    sfx_event = detect_sfx_from_text(raw_text, emotion, realm)
    spoken = strip_action_markers(raw_text)
    prosody_value = prosody.value if prosody else None

    return ConvertedResponse(
        spoken_text=spoken,
        sfx=sfx_event,
        prosody=prosody_value,
    )


def format_sfx_event(event: SFXEvent) -> dict:
    return {
        "event": "audio.sfx_requested",
        "payload": {
            "sfx": event.sfx.value,
            "file": event.file,
            "timing": event.timing,
            "volume": event.volume,
        },
    }
