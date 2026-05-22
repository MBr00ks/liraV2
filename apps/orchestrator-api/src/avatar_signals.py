from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.emotion_engine import EmotionalState, Realm, ProsodyMode
from src.logging import get_logger

logger = get_logger("avatar-signals")


class AvatarSignal(Enum):
    NEUTRAL_ATTENTIVE = "neutral_attentive"
    FOCUSED = "focused"
    THINKING = "thinking"
    AMUSED = "amused"
    PLAYFUL_TEASE = "playful_tease"
    SOFT_FRUSTRATION = "soft_frustration"
    PROTECTIVE_CONCERN = "protective_concern"
    BETWEEN_CONFIDENT = "between_confident"
    MOONSTACHE_NARRATOR_WRY = "moonstache_narrator_wry"
    LISTENING_IDLE = "listening_idle"
    SPEAKING_EMPHASIS = "speaking_emphasis"


@dataclass
class AvatarSignalEvent:
    signal: AvatarSignal
    intensity: int
    duration_ms: int
    realm: str
    emotion: str


EMOTION_TO_SIGNAL: dict[EmotionalState, AvatarSignal] = {
    EmotionalState.FOCUSED: AvatarSignal.FOCUSED,
    EmotionalState.PLAYFUL: AvatarSignal.AMUSED,
    EmotionalState.PROTECTIVE: AvatarSignal.PROTECTIVE_CONCERN,
    EmotionalState.FRUSTRATED: AvatarSignal.SOFT_FRUSTRATION,
    EmotionalState.CURIOUS: AvatarSignal.THINKING,
    EmotionalState.FLIRTATIOUS: AvatarSignal.BETWEEN_CONFIDENT,
    EmotionalState.NARRATIVE_PRESSURE: AvatarSignal.MOONSTACHE_NARRATOR_WRY,
}

REALM_SIGNAL_MODIFIERS: dict[Realm, dict] = {
    Realm.ASSISTANT: {"duration_ms": 1800, "max_intensity": 2},
    Realm.MOONSTACHE: {"duration_ms": 3000, "max_intensity": 3},
    Realm.BETWEEN: {"duration_ms": 2200, "max_intensity": 4},
}

INTENSITY_DURATION_SCALE = {
    0: 1500,
    1: 1800,
    2: 2200,
    3: 2800,
    4: 3500,
}


def emotion_to_avatar_signal(
    emotion: EmotionalState,
    realm: Realm,
    intensity: int = 0,
    prosody: Optional[ProsodyMode] = None,
) -> AvatarSignalEvent:
    base_signal = EMOTION_TO_SIGNAL.get(emotion, AvatarSignal.NEUTRAL_ATTENTIVE)

    realm_config = REALM_SIGNAL_MODIFIERS.get(realm, REALM_SIGNAL_MODIFIERS[Realm.ASSISTANT])
    max_intensity = realm_config["max_intensity"]
    clamped_intensity = min(intensity, max_intensity)

    base_duration = INTENSITY_DURATION_SCALE.get(clamped_intensity, 1800)
    duration = realm_config["duration_ms"]
    final_duration = max(base_duration, duration)

    if prosody == ProsodyMode.BETWEEN_FLIRTATIOUS:
        base_signal = AvatarSignal.BETWEEN_CONFIDENT
    elif prosody == ProsodyMode.MOONSTACHE_NARRATOR:
        base_signal = AvatarSignal.MOONSTACHE_NARRATOR_WRY
    elif prosody == ProsodyMode.PLAYFUL_SASSY and emotion == EmotionalState.PLAYFUL:
        base_signal = AvatarSignal.PLAYFUL_TEASE

    return AvatarSignalEvent(
        signal=base_signal,
        intensity=clamped_intensity,
        duration_ms=final_duration,
        realm=realm.value,
        emotion=emotion.value,
    )


def format_avatar_event(event: AvatarSignalEvent) -> dict:
    return {
        "event": "avatar.signal_requested",
        "payload": {
            "signal": event.signal.value,
            "intensity": event.intensity,
            "duration_ms": event.duration_ms,
            "realm": event.realm,
            "emotion": event.emotion,
        },
    }
