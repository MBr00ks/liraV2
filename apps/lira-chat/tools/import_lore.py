"""Import SillyTavern worldbook JSONs into consolidated lore format."""
import json
from pathlib import Path

ST_WORLDS = Path(r"C:\Users\Mike Brooks\Documents\SillyTavern\data\default-user\worlds")
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "lore" / "lore_data.json"

# Map worldbook filenames (without .json) to mode(s)
MODE_LORE_MAP = {
    "Lira - Assistant": ["assistant"],
    "Lira \u2014 Core Presence & Conversational Cadence": ["assistant", "companion", "observer"],
    "Lira - The Companion": ["companion"],
    "Lira - The Observer": ["observer"],
    "The Between": ["companion"],
    "Moonstache Canon": ["observer"],
    "Moonstache Universe": ["observer"],
    # "Eldoria": ["assistant"],  -- removed, was default ST content
}


def convert_entry(entry_id: str, raw: dict, modes: list[str]) -> dict:
    keys = raw.get("key") or raw.get("keysecondary") or []
    if isinstance(keys, str):
        keys = [keys]

    # Determine activation type
    if raw.get("constant"):
        activation = "always"
    elif raw.get("role"):
        activation = "mode"
    elif keys:
        activation = "trigger"
    else:
        activation = "always"

    return {
        "id": f"{raw.get('uid', entry_id)}",
        "title": raw.get("comment") or raw.get("title", f"Entry {entry_id}"),
        "content": raw.get("content", ""),
        "enabled": not raw.get("disable", False),
        "activation": activation,
        "modes": modes,
        "trigger_keywords": keys if activation == "trigger" else None,
        "source_worldbook": raw.get("source_worldbook", ""),
    }


def main():
    all_entries = []
    seen_ids: set[str] = set()

    for filepath in sorted(ST_WORLDS.glob("*.json")):
        name = filepath.stem  # filename without .json
        if name not in MODE_LORE_MAP:
            continue  # skip worldbooks not in the mapping (e.g. default ST content)
        modes = MODE_LORE_MAP[name]
        raw = json.loads(filepath.read_text(encoding="utf-8"))
        entries = raw.get("entries", {})
        if isinstance(entries, dict):
            items = entries.items()
        elif isinstance(entries, list):
            items = [(str(i), e) for i, e in enumerate(entries) if e]
        else:
            continue

        for entry_id, entry_data in items:
            if not isinstance(entry_data, dict):
                continue
            converted = convert_entry(entry_id, entry_data, modes)
            converted["source_worldbook"] = name
            # Deduplicate by content (same lore might be in different worldbooks)
            content_key = converted["content"].strip().lower()[:100]
            if content_key and content_key not in seen_ids:
                seen_ids.add(content_key)
                all_entries.append(converted)

    consolidated = {
        "version": "1.0",
        "description": "Consolidated lore from SillyTavern worldbooks for Lira Chat UI",
        "entries": all_entries,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(consolidated, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Imported {len(all_entries)} lore entries from {sum(1 for _ in ST_WORLDS.glob('*.json'))} worldbooks")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
