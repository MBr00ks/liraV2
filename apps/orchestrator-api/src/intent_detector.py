import re
from dataclasses import dataclass

from src.emotion_engine import EmotionalState, Realm
from src.logging import get_logger

logger = get_logger("intent-detector")

INTENT_KEYWORDS = {
    "coding": [
        "code", "function", "bug", "debug", "implement", "refactor",
        "api", "endpoint", "deploy", "build", "compile", "error",
        "typescript", "python", "javascript", "react", "next",
        "pull request", "commit", "merge", "branch", "test",
    ],
    "emotional_support": [
        "sad", "upset", "frustrated", "anxious", "worried", "stressed",
        "tired", "overwhelmed", "lonely", "miss", "hard day", "rough",
        "need to talk", "not okay", "feeling down", "depressed",
    ],
    "lore_discussion": [
        "moonstache", "hobnail", "character", "lore", "canon", "story",
        "world", "universe", "timeline", "event", "plot", "mystery",
        "chapter", "scene", "narrative", "between",
    ],
    "story_narration": [
        "tell me a story", "narrate", "describe", "scene", "imagine",
        "what if", "picture this", "let's write", "create a scene",
        "continue the story", "what happens next",
    ],
    "technical_troubleshooting": [
        "not working", "broken", "why won't", "how do i fix",
        "error message", "crash", "freeze", "slow", "performance",
        "configuration", "setup", "install", "docker", "server",
    ],
    "romantic_interaction": [
        "love you", "miss you", "beautiful", "cute", "sweet",
        "kiss", "hug", "hold", "together", "forever", "darling",
        "babe", "honey", "affection", "intimate", "romantic",
    ],
    "realtime_interruption": [
        "stop", "wait", "no no", "hold on", "pause", "interrupt",
        "let me", "actually", "nevermind", "scratch that",
    ],
    "visual_request": [
        "show me", "image", "picture", "draw", "generate",
        "visual", "see", "look", "photo", "render",
    ],
    "image_generation": [
        "generate image", "create image", "make a picture",
        "draw this", "illustrate", "concept art", "character design",
    ],
    "video_generation": [
        "generate video", "create video", "animate", "motion",
        "video clip", "animation", "render video",
    ],
}

REALM_INDICATORS = {
    Realm.ASSISTANT: [
        "help me", "how do i", "can you", "let's build", "let's work",
        "project", "code", "debug", "fix", "organize", "plan",
        "what do you think", "advice", "suggest", "assistant",
        "work on", "tackle", "brainstorm", "implement",
    ],
    Realm.MOONSTACHE: [
        "moonstache", "story", "chapter", "scene", "character",
        "what would happen if", "in the story", "narrate",
        "write a scene", "continue", "lore", "world", "hobnail",
        "moonstache realm", "narrative",
    ],
    Realm.BETWEEN: [
        "how are you", "how do you feel", "tell me about yourself",
        "what do you want", "between", "us", "you and me",
        "love", "miss", "missed", "missing", "beautiful", "cute", "sweet",
        "darling", "babe", "honey", "the between", "between realm",
        "i've missed", "i miss", "thinking of you", "thinking about you",
        "what are you wearing", "what do you look like", "describe yourself",
        "your appearance", "your body", "your hair", "your eyes",
        "kiss", "hug", "hold", "touch", "close to you",
        "personal", "intimate", "romantic", "attractive", "pretty",
        "your day", "your thoughts", "your feelings", "your dreams",
    ],
}

EMOTION_CUES = {
    EmotionalState.FOCUSED: [
        "focus", "concentrate", "let's get this done", "work on",
        "implement", "build", "fix", "debug", "solve",
    ],
    EmotionalState.PLAYFUL: [
        "haha", "lol", "funny", "joke", "tease", "play",
        "what if", "imagine", "fun", "game",
    ],
    EmotionalState.PROTECTIVE: [
        "worried", "stressed", "anxious", "overwhelmed", "hard",
        "difficult", "struggling", "need help", "can't",
    ],
    EmotionalState.FRUSTRATED: [
        "annoying", "frustrated", "why won't", "not working",
        "stupid", "hate", "ugh", "damn", "shit",
    ],
    EmotionalState.CURIOUS: [
        "wonder", "curious", "why", "how does", "what if",
        "explain", "tell me about", "interesting",
    ],
    EmotionalState.FLIRTATIOUS: [
        "love you", "beautiful", "cute", "sweet", "miss you",
        "darling", "babe", "kiss", "hug", "flirt",
    ],
    EmotionalState.NARRATIVE_PRESSURE: [
        "story", "narrate", "scene", "chapter", "character",
        "what happens", "continue", "lore", "moonstache",
    ],
}


@dataclass
class IntentResult:
    intent: str
    confidence: float
    categories: list[str]


def detect_intent(message: str) -> IntentResult:
    text = message.lower().strip()

    scores: dict[str, float] = {}

    for intent, keywords in INTENT_KEYWORDS.items():
        score = 0.0
        for keyword in keywords:
            if keyword in text:
                score += 1.0
                if re.search(rf"\b{re.escape(keyword)}\b", text):
                    score += 0.5

        if score > 0:
            max_possible = len(keywords) * 1.5
            scores[intent] = min(score / max(max_possible, 1), 1.0)

    if not scores:
        scores["coding"] = 0.1
        scores["emotional_support"] = 0.1

    best_intent = max(scores, key=scores.get)
    confidence = scores[best_intent]

    secondary = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    categories = [intent for intent, score in secondary if score > 0.1 and intent != best_intent]

    logger.info("Intent detected", {
        "intent": best_intent,
        "confidence": round(confidence, 3),
        "secondary": categories[:2],
    })

    return IntentResult(
        intent=best_intent,
        confidence=confidence,
        categories=categories,
    )


def detect_realm_transition(message: str, current_realm: Realm = Realm.ASSISTANT) -> Realm:
    text = message.lower().strip()
    scores: dict[Realm, float] = {r: 0.0 for r in Realm}

    for realm, indicators in REALM_INDICATORS.items():
        score = 0.0
        for indicator in indicators:
            if indicator in text:
                weight = 2.0 if realm == Realm.BETWEEN else 1.0
                score += weight
                if re.search(rf"\b{re.escape(indicator)}\b", text):
                    score += 0.5
        scores[realm] = score

    best_realm = max(scores, key=scores.get)
    if scores[best_realm] > 0:
        if scores[best_realm] >= 2.0:
            return best_realm
        if best_realm != current_realm and scores[current_realm] > 0:
            return current_realm
        return best_realm
    return current_realm


def detect_emotion_cues(message: str) -> EmotionalState:
    text = message.lower().strip()
    scores: dict[EmotionalState, float] = {e: 0.0 for e in EmotionalState}

    for emotion, cues in EMOTION_CUES.items():
        score = 0.0
        for cue in cues:
            if cue in text:
                score += 1.0
                if re.search(rf"\b{re.escape(cue)}\b", text):
                    score += 0.5
        scores[emotion] = score

    best_emotion = max(scores, key=scores.get)
    if scores[best_emotion] > 0:
        return best_emotion
    return EmotionalState.FOCUSED
