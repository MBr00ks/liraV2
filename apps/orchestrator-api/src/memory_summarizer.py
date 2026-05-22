from dataclasses import dataclass
from typing import Optional

from src.emotion_engine import EmotionalState, Realm
from src.logging import get_logger

logger = get_logger("memory-summarizer")

SUMMARIZATION_PROMPT = """You are extracting durable memories from a conversation.
Given the user message and Lira's response, produce a concise memory entry.

Rules:
- Extract facts, decisions, preferences, or meaningful emotional moments
- Do not store throwaway remarks, jokes, or transient frustration
- Keep it under 150 characters
- Focus on what should be remembered long-term
- If nothing worth remembering, return empty string

Output format:
title: <short title>
content: <concise memory>
importance: <1-5>
"""


@dataclass
class MemorySummary:
    title: str
    content: str
    importance: int
    should_store: bool


def quick_summarize(user_message: str, response: str, realm: Realm, emotion: EmotionalState) -> MemorySummary:
    if realm == Realm.BETWEEN:
        return MemorySummary(
            title=user_message[:50],
            content=f"User: {user_message[:100]}\nLira: {response[:100]}",
            importance=3,
            should_store=True,
        )

    if emotion in (EmotionalState.PROTECTIVE, EmotionalState.FRUSTRATED, EmotionalState.FLIRTATIOUS):
        return MemorySummary(
            title=user_message[:50],
            content=f"User: {user_message[:100]}\nLira: {response[:100]}",
            importance=3,
            should_store=True,
        )

    if len(user_message) < 15:
        return MemorySummary(title="", content="", importance=0, should_store=False)

    keywords = ["decided", "choose", "prefer", "want", "need", "remember", "important", "always", "never", "rule", "policy"]
    if any(kw in user_message.lower() for kw in keywords):
        return MemorySummary(
            title=user_message[:50],
            content=user_message[:150],
            importance=4,
            should_store=True,
        )

    if len(user_message) > 50:
        return MemorySummary(
            title=user_message[:50],
            content=user_message[:150],
            importance=2,
            should_store=True,
        )

    return MemorySummary(title="", content="", importance=0, should_store=False)


def format_for_storage(summary: MemorySummary, category: str, metadata: Optional[dict] = None) -> dict:
    return {
        "category": category,
        "title": summary.title,
        "content": summary.content,
        "importance": summary.importance,
        "metadata": metadata or {},
        "merge_strategy": "create_new",
    }
