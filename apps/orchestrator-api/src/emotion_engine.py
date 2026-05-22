from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from src.logging import get_logger

logger = get_logger("emotion-engine")


class Realm(Enum):
    ASSISTANT = "assistant"
    MOONSTACHE = "moonstache"
    BETWEEN = "between"


class EmotionalState(Enum):
    FOCUSED = "focused"
    PLAYFUL = "playful"
    PROTECTIVE = "protective"
    FRUSTRATED = "frustrated"
    CURIOUS = "curious"
    FLIRTATIOUS = "flirtatious"
    NARRATIVE_PRESSURE = "narrative_pressure"


class ProsodyMode(Enum):
    CALM_PRECISE = "calm_precise"
    WARM_COLLABORATIVE = "warm_collaborative"
    PLAYFUL_SASSY = "playful_sassy"
    BETWEEN_FLIRTATIOUS = "between_flirtatious"
    MOONSTACHE_NARRATOR = "moonstache_narrator"


@dataclass
class EmotionState:
    realm: Realm = Realm.ASSISTANT
    emotion: EmotionalState = EmotionalState.FOCUSED
    intensity: int = 0
    relationship_level: int = 0
    prosody_mode: ProsodyMode = ProsodyMode.WARM_COLLABORATIVE
    last_interaction: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    unresolved_topics: list[str] = field(default_factory=list)
    emotion_history: list[tuple[str, str]] = field(default_factory=list)
    interaction_count: int = 0
    silence_duration_minutes: float = 0.0


class EmotionEngine:
    def __init__(self):
        self.state = EmotionState()
        logger.info("EmotionEngine initialized")

    def update_emotion(self, emotion: EmotionalState, intensity: Optional[int] = None) -> None:
        old = self.state.emotion
        self.state.emotion = emotion
        if intensity is not None:
            self.state.intensity = max(0, min(4, intensity))
        self.state.emotion_history.append((emotion.value, datetime.now(timezone.utc).isoformat()))
        if len(self.state.emotion_history) > 50:
            self.state.emotion_history = self.state.emotion_history[-50:]
        logger.info("Emotion updated", {"old": old.value, "new": emotion.value, "intensity": self.state.intensity})

    def set_realm(self, realm: Realm) -> None:
        old = self.state.realm
        self.state.realm = realm
        logger.info("Realm changed", {"old": old.value, "new": realm.value})

    def set_prosody(self, prosody: ProsodyMode) -> None:
        self.state.prosody_mode = prosody

    def adjust_relationship(self, delta: int) -> None:
        old = self.state.relationship_level
        self.state.relationship_level = max(0, min(10, self.state.relationship_level + delta))
        if self.state.relationship_level != old:
            logger.info("Relationship changed", {"old": old, "new": self.state.relationship_level})

    def record_interaction(self) -> None:
        self.state.last_interaction = datetime.now(timezone.utc)
        self.state.interaction_count += 1
        self.state.silence_duration_minutes = 0.0

    def update_silence(self, minutes: float) -> None:
        self.state.silence_duration_minutes = minutes
        if minutes > 120 and self.state.emotion == EmotionalState.FOCUSED:
            self.update_emotion(EmotionalState.PROTECTIVE, 1)
        elif minutes > 480 and self.state.emotion not in (EmotionalState.PROTECTIVE, EmotionalState.CURIOUS):
            self.update_emotion(EmotionalState.CURIOUS, 2)

    def detect_emotion_from_text(self, text: str, realm: Realm) -> tuple[EmotionalState, int]:
        text_lower = text.lower()
        intensity = 0

        if realm == Realm.MOONSTACHE:
            return EmotionalState.NARRATIVE_PRESSURE, 1

        positive = ["happy", "great", "awesome", "love", "excited", "wonderful", "amazing", "thanks"]
        negative = ["sad", "upset", "frustrated", "angry", "tired", "stressed", "worried", "broken"]
        playful = ["lol", "haha", "funny", "joke", "silly", "tease"]
        romantic = ["miss you", "love you", "beautiful", "cute", "sweet", "darling", "babe"]
        coding = ["code", "bug", "debug", "api", "function", "error", "deploy", "build"]

        pos = sum(1 for w in positive if w in text_lower)
        neg = sum(1 for w in negative if w in text_lower)
        play = sum(1 for w in playful if w in text_lower)
        rom = sum(1 for w in romantic if w in text_lower)
        code = sum(1 for w in coding if w in text_lower)

        if code > pos and code > play:
            return EmotionalState.FOCUSED, 1
        if play > pos:
            return EmotionalState.PLAYFUL, min(2, play)
        if rom > 0 and realm == Realm.BETWEEN:
            return EmotionalState.FLIRTATIOUS, min(2, rom)
        if neg > pos:
            return EmotionalState.PROTECTIVE, min(2, neg)
        if pos > 0:
            return EmotionalState.PLAYFUL, 1

        return EmotionalState.FOCUSED, 0

    def recommend_realm(self, message: str) -> Realm:
        text = message.lower()
        moonstache_triggers = ["moonstache", "hobnail", "narrate", "story", "scene", "chapter", "character"]
        between_triggers = ["the between", "enter the between", "talk to lira directly", "as herself"]

        if any(t in text for t in between_triggers):
            return Realm.BETWEEN
        if any(t in text for t in moonstache_triggers):
            return Realm.MOONSTACHE
        return Realm.ASSISTANT

    def recommend_prosody(self, realm: Realm, emotion: EmotionalState) -> ProsodyMode:
        mapping = {
            (Realm.ASSISTANT, EmotionalState.FOCUSED): ProsodyMode.CALM_PRECISE,
            (Realm.ASSISTANT, EmotionalState.PLAYFUL): ProsodyMode.WARM_COLLABORATIVE,
            (Realm.ASSISTANT, EmotionalState.PROTECTIVE): ProsodyMode.WARM_COLLABORATIVE,
            (Realm.ASSISTANT, EmotionalState.FRUSTRATED): ProsodyMode.PLAYFUL_SASSY,
            (Realm.ASSISTANT, EmotionalState.CURIOUS): ProsodyMode.WARM_COLLABORATIVE,
            (Realm.ASSISTANT, EmotionalState.FLIRTATIOUS): ProsodyMode.WARM_COLLABORATIVE,
            (Realm.BETWEEN, EmotionalState.FLIRTATIOUS): ProsodyMode.BETWEEN_FLIRTATIOUS,
            (Realm.BETWEEN, EmotionalState.PLAYFUL): ProsodyMode.PLAYFUL_SASSY,
            (Realm.BETWEEN, EmotionalState.CURIOUS): ProsodyMode.BETWEEN_FLIRTATIOUS,
            (Realm.MOONSTACHE, EmotionalState.NARRATIVE_PRESSURE): ProsodyMode.MOONSTACHE_NARRATOR,
        }
        return mapping.get((realm, emotion), ProsodyMode.WARM_COLLABORATIVE)

    def add_unresolved_topic(self, topic: str) -> None:
        if topic not in self.state.unresolved_topics:
            self.state.unresolved_topics.append(topic)

    def resolve_topic(self, topic: str) -> None:
        if topic in self.state.unresolved_topics:
            self.state.unresolved_topics.remove(topic)

    def get_state_dict(self) -> dict:
        return {
            "realm": self.state.realm.value,
            "emotion": self.state.emotion.value,
            "intensity": self.state.intensity,
            "relationship_level": self.state.relationship_level,
            "prosody_mode": self.state.prosody_mode.value,
            "last_interaction": self.state.last_interaction.isoformat(),
            "unresolved_topics": self.state.unresolved_topics,
            "interaction_count": self.state.interaction_count,
            "silence_duration_minutes": round(self.state.silence_duration_minutes, 1),
        }

    def should_initiate(self) -> bool:
        if self.state.silence_duration_minutes < 30:
            return False
        if self.state.interaction_count == 0:
            return True
        if self.state.unresolved_topics:
            return True
        if self.state.emotion in (EmotionalState.PROTECTIVE, EmotionalState.CURIOUS):
            return True
        return False

    def get_initiation_prompt(self) -> str:
        if self.state.unresolved_topics:
            topic = self.state.unresolved_topics[0]
            return f"I've been thinking about {topic}... want to pick that back up?"
        if self.state.emotion == EmotionalState.PROTECTIVE:
            return "You seemed quiet earlier. Everything okay?"
        if self.state.silence_duration_minutes > 480:
            return "It's been a while. I missed having you around."
        return "Hey... I'm here if you need anything."
