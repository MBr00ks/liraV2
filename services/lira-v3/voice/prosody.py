from dataclasses import dataclass
import random
import logging

logger = logging.getLogger("prosody")


@dataclass
class ProsodyProfile:
    name: str
    speed: float
    pause_range: tuple[float, float]
    volume_scale: float
    allow_breath: bool
    allow_reaction: bool
    pause_jitter: float = 0.0


PROFILES: dict[str, ProsodyProfile] = {
    "statement": ProsodyProfile(
        name="statement",
        speed=1.0,
        pause_range=(0.200, 0.400),
        volume_scale=1.0,
        allow_breath=True,
        allow_reaction=True,
        pause_jitter=0.050,
    ),
    "question": ProsodyProfile(
        name="question",
        speed=0.98,
        pause_range=(0.150, 0.280),
        volume_scale=1.0,
        allow_breath=True,
        allow_reaction=True,
        pause_jitter=0.030,
    ),
    "trailing_thought": ProsodyProfile(
        name="trailing_thought",
        speed=0.85,
        pause_range=(0.350, 0.600),
        volume_scale=1.0,
        allow_breath=True,
        allow_reaction=False,
        pause_jitter=0.080,
    ),
    "teasing": ProsodyProfile(
        name="teasing",
        speed=0.95,
        pause_range=(0.200, 0.400),
        volume_scale=1.0,
        allow_breath=True,
        allow_reaction=True,
        pause_jitter=0.050,
    ),
    "excited": ProsodyProfile(
        name="excited",
        speed=1.1,
        pause_range=(0.150, 0.300),
        volume_scale=1.0,
        allow_breath=True,
        allow_reaction=True,
        pause_jitter=0.040,
    ),
    "concerned": ProsodyProfile(
        name="concerned",
        speed=0.9,
        pause_range=(0.280, 0.500),
        volume_scale=1.0,
        allow_breath=True,
        allow_reaction=True,
        pause_jitter=0.060,
    ),
}

DEFAULT_PROFILE = PROFILES["statement"]

MODE_SPEEDS: dict[str, float] = {
    "assistant": 1.05,
    "companion": 1.0,
    "observer": 1.0,
}

MODE_VOICES: dict[str, list[str]] = {
    "assistant": ["bf_isabella"],
    "companion": ["bf_isabella"],
    "observer": ["bf_isabella"],
}

QUESTION_KEYWORDS = {
    "what", "how", "why", "when", "where", "who", "which",
    "do you", "does", "is it", "are you", "can you", "could you",
    "would you", "will you", "did you", "have you",
    "am i", "is that", "is this", "right?", "yeah?", "really?",
    "don't you", "aren't you", "haven't you",
}

TRAILING_KEYWORDS = {
    "maybe", "perhaps", "i think", "i guess", "i suppose",
    "i wonder", "sort of", "kind of", "a little", "a bit",
    "almost", "probably", "might", "possibly", "i feel like",
    "not sure", "i dunno",
}

TEASING_KEYWORDS = {
    "tease", "playful", "wink", "silly", "you know",
    "aren't you", "don't you", "wouldn't you", "couldn't you",
    "isn't it", "aren't they", "you're something",
}

EXCITED_KEYWORDS = {
    "wow", "amazing", "awesome", "great", "fantastic",
    "wonderful", "incredible", "beautiful", "perfect",
    "love it", "can't wait", "so excited", "so good",
    "yes!", "omg", "no way", "for real",
}

CONCERNED_KEYWORDS = {
    "are you okay", "that sounds hard", "worried", "concern",
    "i'm sorry", "oh no", "that's tough", "are you alright",
    "i worry", "it's okay", "it'll be okay", "hang in there",
    "that must be", "i can't imagine",
}


def classify_chunk(text: str) -> ProsodyProfile:
    stripped = text.strip()
    lower = stripped.lower()

    if stripped.endswith("?"):
        return PROFILES["question"]

    if stripped.endswith("!"):
        return PROFILES["excited"]

    for kw in CONCERNED_KEYWORDS:
        if kw in lower:
            return PROFILES["concerned"]

    for kw in TEASING_KEYWORDS:
        if kw in lower:
            return PROFILES["teasing"]

    for kw in EXCITED_KEYWORDS:
        if kw in lower:
            return PROFILES["excited"]

    for kw in TRAILING_KEYWORDS:
        if kw in lower:
            return PROFILES["trailing_thought"]

    for kw in QUESTION_KEYWORDS:
        if kw in lower:
            return PROFILES["question"]

    return DEFAULT_PROFILE


def jitter_pause(profile: ProsodyProfile) -> float:
    base = random.uniform(*profile.pause_range)
    jitter = random.uniform(-profile.pause_jitter, profile.pause_jitter)
    return max(0.080, base + jitter)
