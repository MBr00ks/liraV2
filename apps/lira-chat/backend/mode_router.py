import json
import os
from pathlib import Path

PERSONALITY_DIR = Path(__file__).resolve().parent.parent / "data" / "personalities"
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "data" / "snapshots"


def _load_personality(mode: str) -> dict:
    path = PERSONALITY_DIR / f"{mode}.json"
    if not path.exists():
        return {"mode": mode, "label": mode.capitalize(), "system_prompt": "", "style_guide": ""}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_personality(data: dict):
    path = PERSONALITY_DIR / f"{data['mode']}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_system_prompt(mode: str, override: str | None = None) -> str:
    if override:
        return override
    return _load_personality(mode).get("system_prompt", "")


def get_style_guide(mode: str) -> str:
    return _load_personality(mode).get("style_guide", "")


def list_personalities() -> list[dict]:
    profiles = []
    for f in sorted(PERSONALITY_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        profiles.append(data)
    return profiles


def update_personality(mode: str, data: dict) -> dict:
    current = _load_personality(mode)
    current["system_prompt"] = data.get("system_prompt", current.get("system_prompt", ""))
    current["style_guide"] = data.get("style_guide", current.get("style_guide", ""))
    if "label" in data:
        current["label"] = data["label"]
    if "description" in data:
        current["description"] = data["description"]
    _save_personality(current)
    return current


def save_snapshot(name: str, lore_path: str) -> dict:
    snapshot = {
        "name": name,
        "personalities": {},
    }
    for mode in ["assistant", "companion", "observer"]:
        snapshot["personalities"][mode] = _load_personality(mode)

    if lore_path and os.path.exists(lore_path):
        snapshot["lore"] = json.loads(Path(lore_path).read_text(encoding="utf-8"))

    stamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = name.lower().replace(" ", "_").replace("/", "_")
    filename = f"{stamp}_{safe_name}.json"
    path = SNAPSHOT_DIR / filename
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"name": name, "file": filename, "timestamp": stamp}


def list_snapshots() -> list[dict]:
    snaps = []
    for f in sorted(SNAPSHOT_DIR.glob("*.json"), reverse=True):
        data = json.loads(f.read_text(encoding="utf-8"))
        stamps = f.stem.split("_", 1)
        snaps.append({
            "name": data.get("name", f.stem),
            "file": f.name,
            "timestamp": stamps[0] if stamps else "",
            "modes": list(data.get("personalities", {}).keys()),
        })
    return snaps


def load_snapshot(file: str) -> dict | None:
    path = SNAPSHOT_DIR / file
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    for mode, personality in data.get("personalities", {}).items():
        _save_personality(personality)
    return data
