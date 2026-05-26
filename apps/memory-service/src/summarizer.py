from src.config import get_settings
from src.models.memory import ConversationChunk, MemoryCategory
from src.logging import get_logger

logger = get_logger("summarizer")


SUMMARIZE_PROMPT = """Summarize the following conversation into a concise memory entry.

Focus on:
- What happened (key events or decisions)
- What was said that matters (preferences, facts, emotional context)
- Any decisions or agreements made
- The emotional tone

Keep it to 2-3 sentences. Output only the summary, nothing else.

Conversation:
{messages}"""


EXTRACT_TITLE_PROMPT = """Given this conversation summary, give it a short title (5 words max).

Summary: {summary}

Title:"""


class Summarizer:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_memory_model

    async def summarize(self, chunk: ConversationChunk) -> tuple[str, MemoryCategory]:
        messages_text = "\n".join(
            f"{m.role}: {m.content}" for m in chunk.messages
        )

        summary = await self._generate(SUMMARIZE_PROMPT.format(messages=messages_text))
        title = await self._generate(EXTRACT_TITLE_PROMPT.format(summary=summary))
        category = self._infer_category(chunk, summary)

        return summary.strip(), category

    async def summarize_text(self, text: str) -> str:
        return await self._generate(SUMMARIZE_PROMPT.format(messages=text))

    def _infer_category(self, chunk: ConversationChunk, summary: str) -> MemoryCategory:
        lower = summary.lower()
        if any(w in lower for w in ["always", "never", "identity", "is a", "are a", "character"]):
            return MemoryCategory.identity
        if any(w in lower for w in ["relationship", "trust", "feel", "love", "bond", "connection"]):
            return MemoryCategory.relationship
        if any(w in lower for w in ["world", "realm", "lore", "magic", "universe", "moonstache"]):
            return MemoryCategory.lore
        if any(w in lower for w in ["project", "build", "code", "feature", "implement", "fix"]):
            return MemoryCategory.project
        if any(w in lower for w in ["technical", "api", "config", "setting", "server"]):
            return MemoryCategory.technical
        return MemoryCategory.episodic

    async def _generate(self, prompt: str) -> str:
        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 200,
                    },
                },
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
