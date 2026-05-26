import re
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.logging import get_logger

logger = get_logger("speech-parser")


class UtteranceType(Enum):
    QUESTION = "question"
    STATEMENT = "statement"
    COMMAND = "command"
    BACKCHANNEL = "backchannel"
    EXCLAMATION = "exclamation"
    INTERRUPTION = "interruption"
    UNKNOWN = "unknown"


class SpeakingRate(Enum):
    VERY_SLOW = "very_slow"
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"
    VERY_FAST = "very_fast"
    UNKNOWN = "unknown"


class SpeechEmotion(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    THOUGHTFUL = "thoughtful"
    PLAYFUL = "playful"
    FRUSTRATED = "frustrated"
    SURPRISED = "surprised"
    ANXIOUS = "anxious"


@dataclass
class ParsedInput:
    text: str
    cleaned_text: str
    utterance_type: UtteranceType
    speaking_rate: SpeakingRate
    emotion: SpeechEmotion
    confidence: float
    words_per_minute: Optional[float] = None


@dataclass
class SpeechChunk:
    text: str
    prosody_markup: Optional[str] = None
    is_emphasis: bool = False
    is_question: bool = False
    pause_after_ms: int = 0


@dataclass
class ParsedOutput:
    chunks: list[SpeechChunk] = field(default_factory=list)
    normalized_text: str = ""
    estimated_duration_ms: float = 0.0
    prosody_annotation: Optional[str] = None


FILLER_PATTERNS = [
    (r"\bum(?![-\w])", ""),
    (r"\buh(?![-\w])", ""),
    (r"\buhh(?![-\w])", ""),
    (r"\b like \b", " "),
    (r"\byou know\b", ""),
    (r"\bi mean\b", ""),
    (r"\bkind of\b", "somewhat"),
    (r"\bsort of\b", "somewhat"),
    (r"\b actually \b", " "),
    (r"\bbasically\b", ""),
    (r"\bliterally\b", ""),
    (r"\bhonestly\b", ""),
    (r"\bfrankly\b", ""),
    (r"\bright\?*", ""),
    (r"\byou see\b", ""),
]

DISFLUENCY_PATTERN = re.compile(
    r"\b(\w+)(?:-\1|\s+\1\s+|\1\s+\1)\b",
    re.IGNORECASE,
)

QUESTION_WORDS = re.compile(r"\b(what|why|how|when|where|who|which|do|does|did|is|are|was|were|can|could|will|would|shall|should|may|might|have|has|had)\b", re.IGNORECASE)

COMMAND_WORDS = re.compile(r"^(give|show|tell|do|make|stop|start|play|say|send|go|come|find|create|write|draw|imagine|generate)\b", re.IGNORECASE)

EMOTION_KEYWORDS: dict[SpeechEmotion, list[str]] = {
    SpeechEmotion.HAPPY: ["happy", "glad", "wonderful", "great", "love", "amazing", "fantastic", "yay", "woohoo", "delight", "joy", "excited", "beautiful", "lovely", "nice", "fun"],
    SpeechEmotion.THOUGHTFUL: ["hmm", "let me see", "i wonder", "maybe", "perhaps", "consider", "think", "suppose", "possibility", "curious", "reflecting", "pondering"],
    SpeechEmotion.PLAYFUL: ["hehe", "silly", "goofy", "mischievous", "tease", "playful", "funny", "joke", "wink", "giggle", "chuckle"],
    SpeechEmotion.FRUSTRATED: ["ugh", "sigh", "annoying", "frustrating", "tired", "exhausting", "why always", "again", "enough", "come on", "seriously", "ridiculous", "nonsense"],
    SpeechEmotion.SURPRISED: ["wow", "oh", "really", "no way", "seriously", "unexpected", "surprising", "amazing", "incredible", "whoa", "what the", "oh my"],
    SpeechEmotion.ANXIOUS: ["nervous", "worried", "anxious", "unsure", "uncertain", "afraid", "scared", "concerned", "hope", "please", "careful", "worried"],
}

PROSODY_BY_EMOTION: dict[SpeechEmotion, str] = {
    SpeechEmotion.NEUTRAL: "rate=medium pitch=medium",
    SpeechEmotion.HAPPY: "rate=slightly-fast pitch=high",
    SpeechEmotion.THOUGHTFUL: "rate=slow pitch=low",
    SpeechEmotion.PLAYFUL: "rate=medium pitch=high",
    SpeechEmotion.FRUSTRATED: "rate=fast pitch=low",
    SpeechEmotion.SURPRISED: "rate=fast pitch=very-high",
    SpeechEmotion.ANXIOUS: "rate=slightly-fast pitch=medium",
}


def normalize_speech_text(text: str) -> str:
    text = re.sub(r"\$(\d+)\.(\d+)", lambda m: f"{_expand_number(m.group(1))} dollars and {_expand_digits(m.group(2))} cents", text)
    text = re.sub(r"\$(\d+)", lambda m: f"{_expand_number(m.group(1))} dollars", text)
    text = re.sub(r"\b(\d+)\.(\d+)\b", lambda m: f"{m.group(1)} point {_expand_digits(m.group(2))}", text)
    text = re.sub(r"\b(\d{1,3}(?:,\d{3})+)\b", lambda m: _expand_number(m.group(0).replace(",", "")), text)
    text = re.sub(r"(\d+)\s*%", lambda m: f"{_expand_number(m.group(1))} percent", text)
    text = re.sub(r"\b(\d+)\b", lambda m: _expand_number(m.group(1)), text)
    text = re.sub(r"\b(\d{1,2}):(\d{2})\b", lambda m: f"{m.group(1)} {m.group(2)}", text)
    text = re.sub(r"\b(\d)[xX](\d)\b", lambda m: f"{_expand_number(m.group(1))} by {_expand_number(m.group(2))}", text)

    abbreviations = {
        r"\bMr\.\b": "mister",
        r"\bMrs\.\b": "misses",
        r"\bMs\.\b": "miz",
        r"\bDr\.\b": "doctor",
        r"\bProf\.\b": "professor",
        r"\bJr\.\b": "junior",
        r"\bSr\.\b": "senior",
        r"\bSt\.\b": "saint",
        r"\bAve\b": "avenue",
        r"\bBlvd\b": "boulevard",
        r"\bvs\.\b": "versus",
        r"\betc\.?\b": "etcetera",
        r"\bi\.e\.\b": "that is",
        r"\be\.g\.\b": "for example",
    }
    for pattern, replacement in abbreviations.items():
        text = re.sub(pattern, replacement, text)

    vocalizations = {
        r"\bmmm+\b": "mm",
        r"\bmm['-]?hmm\b": "mm-hmm",
        r"\buh['-]?huh\b": "uh-huh",
        r"\buh['-]?uh\b": "uh-uh",
        r"\bah+\b": "ah",
        r"\boh+h?\b": "oh",
        r"\baw+w?\b": "aw",
        r"\bheh+\b": "heh",
        r"\bhmm+\b": "hmm",
        r"\bwhoa+\b": "whoa",
        r"\booh+\b": "ooh",
        r"\bee+y+\b": "eep",
        r"\bmm['-]?kay\b": "mmkay",
        r"\bnuh-?uh\b": "nuh-uh",
        r"\byep+\b": "yep",
        r"\bnop+\b": "nope",
        r"\byeah+\b": "yeah",
        r"\bnah+\b": "nah",
    }
    for pattern, replacement in vocalizations.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = re.sub(r"https?://\S+", "link", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _expand_number(n: str) -> str:
    num = int(n)
    if num < 0:
        return f"minus {_expand_number(str(abs(num)))}"
    if num < 20:
        return ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"][num]
    if num < 100:
        tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
        ten = tens[num // 10]
        remainder = _expand_number(str(num % 10))
        return f"{ten} {remainder}" if remainder != "zero" else ten
    if num < 1000:
        hundreds = _expand_number(str(num // 100))
        remainder = _expand_number(str(num % 100))
        return f"{hundreds} hundred {remainder}" if remainder != "zero" else f"{hundreds} hundred"
    return str(num)


def _expand_digits(s: str) -> str:
    digit_names = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    return " ".join(digit_names[int(d)] for d in s if d.isdigit())


VOCAL_PROTECT: list[tuple[str, str, str]] = [
    (r"mm['-]?hmm\b", "VOCAL_MMHMM", "mm-hmm"),
    (r"uh['-]?huh\b", "VOCAL_UHHUH", "uh-huh"),
    (r"uh['-]?uh\b", "VOCAL_UHUH", "uh-uh"),
    (r"nuh['-]?uh\b", "VOCAL_NUHUH", "nuh-uh"),
    (r"mm['-]?kay\b", "VOCAL_MMKAY", "mmkay"),
]


def clean_asr_text(raw: str) -> str:
    cleaned = raw
    for pattern, token, _canonical in VOCAL_PROTECT:
        cleaned = re.sub(r"\b" + pattern, token, cleaned, flags=re.IGNORECASE)
    for pattern, replacement in FILLER_PATTERNS:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    for _pattern, token, canonical in VOCAL_PROTECT:
        cleaned = cleaned.replace(token, canonical)
    cleaned = cleaned.replace("..", ".").replace("  ", " ").strip()
    return cleaned


def restore_punctuation(text: str) -> str:
    text = text.strip()
    if not text:
        return text

    if any(text.rstrip().endswith(p) for p in {".", "!", "?", "..."}):
        pass
    elif re.search(QUESTION_WORDS, text):
        text = text.rstrip() + "?"
    elif text.rstrip().endswith(","):
        text = text.rstrip()[:-1] + "."
    else:
        text = text.rstrip() + "."

    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    return text


def classify_utterance_type(text: str) -> UtteranceType:
    stripped = text.strip()
    if not stripped:
        return UtteranceType.UNKNOWN
    if stripped.endswith("?"):
        return UtteranceType.QUESTION
    if stripped.endswith("!"):
        return UtteranceType.EXCLAMATION
    if re.match(COMMAND_WORDS, stripped):
        return UtteranceType.COMMAND
    if len(stripped.split()) <= 3 and not stripped.endswith("."):
        return UtteranceType.BACKCHANNEL
    return UtteranceType.STATEMENT


def detect_emotion(text: str) -> SpeechEmotion:
    lower = text.lower()
    scores: dict[SpeechEmotion, int] = {e: 0 for e in SpeechEmotion}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                scores[emotion] += 1

    best = SpeechEmotion.NEUTRAL
    best_score = 0
    for emotion, score in scores.items():
        if score > best_score:
            best_score = score
            best = emotion

    return best


def estimate_speaking_rate(word_count: float, duration_seconds: Optional[float] = None) -> SpeakingRate:
    if duration_seconds is None or duration_seconds <= 0:
        return SpeakingRate.UNKNOWN
    wpm = (word_count / duration_seconds) * 60.0
    if wpm < 100:
        return SpeakingRate.VERY_SLOW
    if wpm < 130:
        return SpeakingRate.SLOW
    if wpm < 170:
        return SpeakingRate.NORMAL
    if wpm < 220:
        return SpeakingRate.FAST
    return SpeakingRate.VERY_FAST


def parse_input(text: str, duration_seconds: Optional[float] = None) -> ParsedInput:
    raw_word_count = len(text.split())
    cleaned = clean_asr_text(text)
    cleaned = restore_punctuation(cleaned)
    utterance_type = classify_utterance_type(cleaned)
    emotion = detect_emotion(text)
    speaking_rate = estimate_speaking_rate(raw_word_count, duration_seconds)

    return ParsedInput(
        text=text,
        cleaned_text=cleaned,
        utterance_type=utterance_type,
        speaking_rate=speaking_rate,
        emotion=emotion,
        confidence=0.8 if utterance_type != UtteranceType.UNKNOWN else 0.3,
        words_per_minute=(raw_word_count / duration_seconds * 60.0) if duration_seconds and duration_seconds > 0 else None,
    )


DEFAULT_PAUSE_MS = 200
SENTENCE_PAUSE_MS = 350
PARAGRAPH_PAUSE_MS = 600
COMMA_PAUSE_MS = 150

CHARS_PER_SECOND = 15.0


def chunk_for_speech(text: str, max_chars: int = 200) -> list[SpeechChunk]:
    text = normalize_speech_text(text)
    if not text:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[SpeechChunk] = []

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        if len(sent) > max_chars:
            clauses = re.split(r"(?<=[,;:])\s+", sent)
            for clause in clauses:
                clause = clause.strip()
                if not clause:
                    continue
                if len(clause) > max_chars:
                    parts = _split_by_breath(clause, max_chars)
                    for part in parts:
                        chunks.append(SpeechChunk(
                            text=part,
                            is_question=part.endswith("?"),
                            pause_after_ms=SENTENCE_PAUSE_MS if part.endswith((".", "!", "?")) else DEFAULT_PAUSE_MS,
                        ))
                else:
                    chunks.append(SpeechChunk(
                        text=clause,
                        is_question=clause.endswith("?"),
                        pause_after_ms=SENTENCE_PAUSE_MS if clause.endswith((".", "!", "?")) else COMMA_PAUSE_MS,
                    ))
        else:
            chunks.append(SpeechChunk(
                text=sent,
                is_question=sent.endswith("?"),
                pause_after_ms=PARAGRAPH_PAUSE_MS if sent.endswith(("!", "?")) else SENTENCE_PAUSE_MS,
            ))

    return chunks


def _split_by_breath(text: str, max_chars: int) -> list[str]:
    words = text.split()
    parts: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > max_chars and current:
            parts.append(current.strip())
            current = word
        else:
            current += " " + word if current else word
    if current:
        parts.append(current.strip())
    return parts


def detect_emphasis(text: str) -> list[SpeechChunk]:
    chunks = chunk_for_speech(text)
    for chunk in chunks:
        chunk.is_emphasis = bool(re.search(r"\*[^*]+\*|\"[^\"]+\"|'[^']+'", chunk.text))
        chunk.text = chunk.text.replace("*", "")
    return chunks


def estimate_duration_ms(chunks: list[SpeechChunk]) -> float:
    total_chars = sum(len(c.text) for c in chunks)
    total_pauses = sum(c.pause_after_ms for c in chunks)
    speech_ms = (total_chars / CHARS_PER_SECOND) * 1000.0
    return speech_ms + total_pauses


def format_for_speech(
    text: str,
    emotion: Optional[SpeechEmotion] = None,
    max_chunk_chars: int = 200,
) -> ParsedOutput:
    normalized = normalize_speech_text(text)
    chunks = detect_emphasis(normalized)
    for chunk in chunks:
        if len(chunk.text) > max_chunk_chars:
            chunks = chunk_for_speech(normalized, max_chunk_chars)
            break

    duration = estimate_duration_ms(chunks)
    prosody = PROSODY_BY_EMOTION.get(emotion) if emotion else None

    return ParsedOutput(
        chunks=chunks,
        normalized_text=" ".join(c.text for c in chunks),
        estimated_duration_ms=duration,
        prosody_annotation=prosody,
    )
