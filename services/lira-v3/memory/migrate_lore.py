"""One-time migration: import lore_data.json entries into ChromaDB."""
import json
import sys
import asyncio

sys.path.insert(0, ".")
from shared.settings import settings
from memory.chroma_store import ChromaMemoryStore


async def migrate():
    store = ChromaMemoryStore()

    # Load lore from JSON
    data = json.loads(open(settings.lore_path, encoding="utf-8").read())
    entries = data.get("entries", [])
    print(f"Found {len(entries)} lore entries")

    count = 0
    for entry in entries:
        text = entry.get("content", "")
        if not text.strip():
            continue
        metadata = {
            "title": entry.get("title", ""),
            "activation": entry.get("activation", "trigger"),
            "source_worldbook": entry.get("source_worldbook", ""),
            "priority": str(entry.get("priority", 0)),
            "enabled": str(entry.get("enabled", True)),
        }
        await store.store("lore", text, metadata)
        count += 1
        if count % 20 == 0:
            print(f"  {count}/{len(entries)}...")

    print(f"Migrated {count} lore entries to ChromaDB")

    # Verify
    for col in ["identity", "relationship", "projects", "episodes", "lore"]:
        n = store.count(col)
        print(f"  {col}: {n} entries")


if __name__ == "__main__":
    asyncio.run(migrate())
