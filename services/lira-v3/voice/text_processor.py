"""Text preprocessing for TTS — sentence splitting, abbreviation protection, action extraction."""
import re

ACTION_PATTERN = re.compile(r"\*(.+?)\*")

# Abbreviations whose period should not trigger a sentence split
_ABBREV_TITLES = re.compile(r"\b(Dr|Mr|Mrs|Ms|Prof|Sr|Jr|St)\.(?=\s)", re.IGNORECASE)
_ABBREV_INITIAL = re.compile(r"\b([A-Z])\.(?=\s*[A-Z])", re.IGNORECASE)
_ABBREV_OTHER = re.compile(r"\b(vs|etc|inc|ltd|dept|est|approx|vol|no|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.(?=\s[a-z0-9]|\s*$)", re.IGNORECASE)
_ABBREV_DOTTED = re.compile(r"\b([ap]\.m\.|i\.e\.|e\.g\.)(?=\s[a-z0-9]|\s*$)", re.IGNORECASE)

_ABBREV_PLACEHOLDER = "\x00P\x00"
_ABBREV_PERIOD = re.compile(r"\x00P\x00")

SENTENCE_PATTERN = re.compile(r"(.*?[.?!\n]+\s*|.+)")
MIN_CHUNK_CHARS = 12


def protect_abbreviations(text: str) -> str:
    text = _ABBREV_TITLES.sub(lambda m: m.group(0).replace(".", _ABBREV_PLACEHOLDER), text)
    text = _ABBREV_INITIAL.sub(lambda m: m.group(0).replace(".", _ABBREV_PLACEHOLDER), text)
    text = _ABBREV_OTHER.sub(lambda m: m.group(0).replace(".", _ABBREV_PLACEHOLDER), text)
    text = _ABBREV_DOTTED.sub(lambda m: m.group(0).replace(".", _ABBREV_PLACEHOLDER), text)
    return text


def restore_abbreviations(text: str) -> str:
    return _ABBREV_PERIOD.sub(".", text)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, merging short chunks."""
    raw = SENTENCE_PATTERN.findall(text)
    raw = [s.strip() for s in raw if s.strip()]
    chunks = []
    for segment in raw:
        if not chunks:
            chunks.append(segment)
        elif len(chunks[-1]) < MIN_CHUNK_CHARS:
            chunks[-1] += " " + segment
        else:
            chunks.append(segment)
    return chunks


def extract_actions(text: str) -> tuple[str, list[str]]:
    """Extract *action* patterns from text. Returns (cleaned_text, list_of_actions)."""
    actions = ACTION_PATTERN.findall(text)
    cleaned = ACTION_PATTERN.sub("", text).strip()
    return cleaned, [a.strip().lower() for a in actions]


def split_with_actions(text: str) -> list[tuple[str, list[str]]]:
    """Split text into chunks, extracting *actions* from each. Returns list of (cleaned_text, [actions])."""
    text = protect_abbreviations(text)
    raw = SENTENCE_PATTERN.findall(text)
    raw = [s.strip() for s in raw if s.strip()]

    chunks = []
    for segment in raw:
        if not chunks:
            chunks.append(segment)
        elif len(chunks[-1]) < MIN_CHUNK_CHARS:
            chunks[-1] += " " + segment
        else:
            chunks.append(segment)

    result = []
    for chunk in chunks:
        chunk = restore_abbreviations(chunk)
        actions = ACTION_PATTERN.findall(chunk)
        cleaned = restore_abbreviations(ACTION_PATTERN.sub("", chunk).strip())
        if cleaned or actions:
            result.append((cleaned, [a.strip().lower() for a in actions]))
    return result
