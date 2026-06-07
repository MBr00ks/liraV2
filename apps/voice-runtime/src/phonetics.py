import re
from typing import Pattern

Rule = tuple[Pattern[str], str]

RULES: list[Rule] = [
    # Haha/hahaha → spaced laughter
    (re.compile(r"\b(?:ha){2,}\b", re.I), "ha ha"),
    # Standalone "ha" → "hah"
    (re.compile(r"\bha\b", re.I), "hah"),
    # Ahhh/ahh variants → normalize
    (re.compile(r"\ba+h+\b", re.I), "ah"),
    # Hmm variants → normalize
    (re.compile(r"\bh+m+\b", re.I), "hmm"),
    # Mmm variants → normalize
    (re.compile(r"\bm{2,}\b", re.I), "mmm"),
    # Ugh → phonetic
    (re.compile(r"\bugh\b", re.I), "uhg"),
    # shhh / shh → normalize
    (re.compile(r"\bsh+h+\b", re.I), "shh"),
    # mmhmm / mhmm → normalize
    (re.compile(r"\bm+h+m+\b", re.I), "mm-hmm"),
    # tsk / tskk → normalize
    (re.compile(r"\btsk+\b", re.I), "tsk"),
    # pfft / pff → normalize
    (re.compile(r"\bpff+t?\b", re.I), "pfft"),
    # mmmm → normalize (prolonged mmm)
    (re.compile(r"\bm{3,}\b", re.I), "mmm"),
    # hmmm → normalize
    (re.compile(r"\bhmm+\b", re.I), "hmm"),
    # nnh / nngh → normalize
    (re.compile(r"\bnn+[gh]?\b", re.I), "nnh"),
    # ahh → normalize
    (re.compile(r"\bah+h\b", re.I), "ah"),
    # ohh → normalize
    (re.compile(r"\boh+h\b", re.I), "oh"),
]


def apply_phonetics(text: str) -> str:
    result = text
    for pattern, replacement in RULES:
        result = pattern.sub(replacement, result)
    return result


def normalize_for_tts(text: str) -> str:
    """Preprocess text for natural TTS output."""
    # Strip stray asterisks (emphasis markers, any missed by action extraction)
    result = re.sub(r"\*(\w[\w\s]*\w)\*", r"\1", text)
    # Normalize repeated punctuation: !! → !, ?? → ?
    result = re.sub(r"!{2,}", "!", result)
    result = re.sub(r"\?{2,}", "?", result)
    # Lowercase ALL CAPS words (Kokoro over-emphasizes them)
    result = re.sub(r"\b([A-Z]{2,})\b", lambda m: m.group(1).lower(), result)
    return result


PAUSE_TOKEN = re.compile(r"\[pause:(\d+\.?\d*)s\]", re.IGNORECASE)


def extract_pause(text: str) -> tuple[str, float | None]:
    """Extract [pause:X.Xs] token from text. Returns (cleaned_text, seconds_or_None)."""
    m = PAUSE_TOKEN.search(text)
    if m:
        duration = float(m.group(1))
        return PAUSE_TOKEN.sub("", text).strip(), duration
    return text, None
