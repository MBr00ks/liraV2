import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class LoreEntry:
    id: str
    title: str
    content: str
    enabled: bool = True
    activation: str = "trigger"  # always | mode | trigger | manual
    modes: list[str] | None = None
    trigger_keywords: list[str] | None = None
    source_worldbook: str = ""
    priority: int = 0


class LoreManager:
    def __init__(self, path: str = ""):
        self._entries: list[LoreEntry] = []
        self._wb_priority: dict[str, int] = {}
        self._path: str = path
        if path:
            self.load(path)

    def load(self, path: str):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self._entries = []
        for entry in raw.get("entries", []):
            self._entries.append(LoreEntry(
                id=entry.get("id", ""),
                title=entry.get("title", ""),
                content=entry.get("content", ""),
                enabled=entry.get("enabled", True),
                activation=entry.get("activation", "trigger"),
                modes=entry.get("modes"),
                trigger_keywords=entry.get("trigger_keywords", entry.get("keys", [])),
                source_worldbook=entry.get("source_worldbook", ""),
                priority=entry.get("priority", 0),
            ))
        self._wb_priority = raw.get("worldbook_priority", {})

    def save(self, path: str | None = None):
        save_path = Path(path or self._path)
        output = {
            "version": "1.0",
            "description": "Consolidated lore from SillyTavern worldbooks for Lira Chat UI",
            "worldbook_priority": self._wb_priority,
            "entries": [asdict(e) for e in self._entries],
        }
        save_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    def _mode_matches(self, e: LoreEntry, mode: str) -> bool:
        return e.modes is None or len(e.modes) == 0 or mode in e.modes

    def get_active(self, context_text: str, mode: str) -> list[LoreEntry]:
        results: list[LoreEntry] = []
        context_lower = context_text.lower()
        for e in self._entries:
            if not e.enabled or not self._mode_matches(e, mode):
                continue
            if e.activation == "always":
                results.append(e)
            elif e.activation == "mode":
                results.append(e)
            elif e.activation in ("trigger", "keyword") and e.trigger_keywords:
                if any(kw.lower() in context_lower for kw in e.trigger_keywords):
                    results.append(e)
        results.sort(key=lambda x: (self._wb_priority.get(x.source_worldbook, 0), x.priority), reverse=True)
        return results

    def all_entries(self) -> list[LoreEntry]:
        return sorted(self._entries, key=lambda x: (self._wb_priority.get(x.source_worldbook, 0), x.priority), reverse=True)

    def worldbook_order(self) -> list[str]:
        """Return worldbook names sorted by priority descending, then alphabetically."""
        books = set(e.source_worldbook for e in self._entries)
        return sorted(books, key=lambda b: (self._wb_priority.get(b, 0), b), reverse=True)

    def _ensure_wb_priority(self):
        """Assign default priorities to worldbooks that don't have one."""
        max_p = max(self._wb_priority.values()) if self._wb_priority else 0
        for e in self._entries:
            if e.source_worldbook not in self._wb_priority:
                max_p += 1
                self._wb_priority[e.source_worldbook] = max_p

    def move_entry(self, entry_id: str, direction: str) -> LoreEntry | None:
        """Move an entry up or down within its worldbook by swapping priority."""
        target = None
        for i, e in enumerate(self._entries):
            if e.id == entry_id:
                target = i
                break
        if target is None:
            return None

        entry = self._entries[target]
        wb = entry.source_worldbook

        # Find siblings in the same worldbook, sorted by priority descending
        siblings = sorted(
            [(i, e) for i, e in enumerate(self._entries) if e.source_worldbook == wb],
            key=lambda x: x[1].priority,
            reverse=True,
        )

        idx = next(i for i, (si, _) in enumerate(siblings) if si == target)
        swap_idx = idx - 1 if direction == "up" else idx + 1
        if swap_idx < 0 or swap_idx >= len(siblings):
            return entry

        neighbor_idx, neighbor = siblings[swap_idx]

        # Swap priorities; if equal, bump the moving entry
        if entry.priority == neighbor.priority:
            entry.priority += 1 if direction == "up" else -1
        else:
            entry.priority, self._entries[neighbor_idx].priority = (
                self._entries[neighbor_idx].priority,
                entry.priority,
            )
        return entry

    def move_worldbook(self, name: str, direction: str) -> bool:
        """Move a worldbook up or down in the ordering."""
        self._ensure_wb_priority()
        order = self.worldbook_order()
        idx = next((i for i, b in enumerate(order) if b == name), None)
        if idx is None:
            return False

        swap_idx = idx - 1 if direction == "up" else idx + 1
        if swap_idx < 0 or swap_idx >= len(order):
            return False

        # Swap priorities
        a, b = name, order[swap_idx]
        self._wb_priority[a], self._wb_priority[b] = (
            self._wb_priority.get(b, 0),
            self._wb_priority.get(a, 0),
        )
        return True

    def toggle_entry(self, entry_id: str, mode: str | None = None) -> LoreEntry | None:
        for e in self._entries:
            if e.id == entry_id:
                if mode:
                    if e.modes is None:
                        e.modes = []
                    if mode in e.modes:
                        e.modes = [m for m in e.modes if m != mode]
                    else:
                        e.modes.append(mode)
                else:
                    e.enabled = not e.enabled
                return e
        return None

    def toggle_worldbook(self, worldbook: str, mode: str, active: bool) -> list[LoreEntry]:
        updated = []
        for e in self._entries:
            if e.source_worldbook == worldbook:
                if e.modes is None:
                    e.modes = []
                if active and mode not in e.modes:
                    e.modes.append(mode)
                    updated.append(e)
                elif not active and mode in e.modes:
                    e.modes = [m for m in e.modes if m != mode]
                    updated.append(e)
        return updated

    def delete_entry(self, entry_id: str) -> bool:
        for i, e in enumerate(self._entries):
            if e.id == entry_id:
                self._entries.pop(i)
                return True
        return False

    def delete_worldbook(self, name: str) -> int:
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.source_worldbook != name]
        self._wb_priority.pop(name, None)
        return before - len(self._entries)

    def update_entry(self, entry_id: str, data: dict) -> LoreEntry | None:
        for i, e in enumerate(self._entries):
            if e.id == entry_id:
                updated = LoreEntry(
                    id=e.id,
                    title=data.get("title", e.title),
                    content=data.get("content", e.content),
                    enabled=data.get("enabled", e.enabled),
                    activation=data.get("activation", e.activation),
                    modes=data.get("modes", e.modes),
                    trigger_keywords=data.get("trigger_keywords", e.trigger_keywords),
                    source_worldbook=data.get("source_worldbook", e.source_worldbook),
                    priority=data.get("priority", e.priority),
                )
                self._entries[i] = updated
                return updated
        return None

    def create_entry(self, title: str, content: str, activation: str = "trigger",
                     modes: list[str] | None = None, trigger_keywords: list[str] | None = None,
                     source_worldbook: str = "", priority: int = 0) -> LoreEntry:
        # Auto-assign priority: one higher than the current max in this worldbook
        if priority == 0:
            wb_entries = [e for e in self._entries if e.source_worldbook == source_worldbook]
            priority = max((e.priority for e in wb_entries), default=0) + 1
        entry = LoreEntry(
            id=str(__import__("uuid").uuid4()),
            title=title,
            content=content,
            enabled=True,
            activation=activation,
            modes=modes or [],
            trigger_keywords=trigger_keywords or [],
            source_worldbook=source_worldbook,
            priority=priority,
        )
        self._entries.append(entry)
        self._ensure_wb_priority()
        if source_worldbook not in self._wb_priority:
            self._wb_priority[source_worldbook] = max(self._wb_priority.values(), default=0) + 1
        return entry

    def create_worldbook(self, name: str, modes: list[str] | None = None) -> str:
        self._ensure_wb_priority()
        self._wb_priority[name] = max(self._wb_priority.values(), default=0) + 1
        return name

    def replace_all(self, entries: list[dict]):
        self._entries = [
            LoreEntry(**{k: v for k, v in e.items() if k in LoreEntry.__dataclass_fields__})
            for e in entries
        ]
        self._ensure_wb_priority()

    @property
    def worldbooks(self) -> dict[str, list[str]]:
        books: dict[str, list[str]] = {}
        for e in self._entries:
            if e.source_worldbook not in books:
                books[e.source_worldbook] = []
            if e.modes and e.modes not in books[e.source_worldbook]:
                books[e.source_worldbook] = list(set(books[e.source_worldbook] + (e.modes or [])))
        return books

    def as_dict(self, entries: list[LoreEntry]) -> list[dict]:
        return [asdict(e) for e in entries]
