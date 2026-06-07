import json
from datetime import datetime, timezone
from pathlib import Path


class ConversationLogger:
    def __init__(self, log_dir: str = "logs"):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._messages: list[dict] = []

    def log_message(self, role: str, content: str, metadata: dict | None = None):
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            entry.update(metadata)
        self._messages.append(entry)
        self._flush()

    def _flush(self):
        path = self._log_dir / f"{self._session_id}.json"
        path.write_text(json.dumps({
            "session_id": self._session_id,
            "messages": self._messages,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    def recent(self, n: int = 10) -> list[dict]:
        return self._messages[-n:]
