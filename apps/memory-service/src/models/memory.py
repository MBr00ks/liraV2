from enum import Enum
from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional
from pydantic import BaseModel, Field


class MemoryCategory(str, Enum):
    identity = "identity"
    relationship = "relationship"
    lore = "lore"
    project = "project"
    episodic = "episodic"
    technical = "technical"


class Realm(str, Enum):
    assistant = "assistant"
    between = "between"
    moonstache = "moonstache"


class MemorySource(str, Enum):
    chat_summary = "chat_summary"
    manual = "manual"
    system = "system"


class MemoryWrite(BaseModel):
    category: MemoryCategory
    title: str
    content: str
    realm: Realm = Realm.assistant
    importance: int = Field(default=3, ge=1, le=5)
    source: MemorySource = MemorySource.chat_summary
    metadata: dict = Field(default_factory=dict)


class MemoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    category: MemoryCategory
    title: str
    content: str
    realm: Realm
    importance: int
    source: MemorySource
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    score: float = 0.0


class MemoryQuery(BaseModel):
    text: str
    realm: Optional[Realm] = None
    category: Optional[MemoryCategory] = None
    limit: int = 5
    min_importance: int = 1


class MessageRecord(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationChunk(BaseModel):
    session_id: str
    messages: list[MessageRecord]
    realm: Realm = Realm.assistant
