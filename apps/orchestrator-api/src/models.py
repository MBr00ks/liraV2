from pydantic import BaseModel, Field
from typing import Optional


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: bool = True
    mode: Optional[str] = None


class ChatResponse(BaseModel):
    content: str
    session_id: str
    realm: str
    emotion: str
    intensity: int
    prosody_mode: str
    model_used: str
    latency_ms: float
    internal_thoughts: list[str] = Field(default_factory=list)
    avatar_signal: Optional[dict] = None
    sfx_event: Optional[dict] = None
    spoken_text: Optional[str] = None


class StreamChunk(BaseModel):
    content: str
    done: bool


class MemoryCreate(BaseModel):
    category: str
    title: str
    content: str
    importance: int = Field(ge=1, le=5, default=3)
    metadata: dict = Field(default_factory=dict)


class MemoryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    importance: Optional[int] = Field(default=None, ge=1, le=5)
    metadata: Optional[dict] = None


class MemoryResponse(BaseModel):
    id: int
    category: str
    title: str
    content: str
    importance: int
    metadata: dict
    created_at: str
    updated_at: str


class MemorySearchRequest(BaseModel):
    query: str
    categories: Optional[list[str]] = None
    limit: int = 10


class EmotionStateResponse(BaseModel):
    realm: str
    emotion: str
    intensity: int
    prosody_mode: str
    relationship_level: int = Field(ge=0, le=10, default=0)
    last_interaction: str
    unresolved_topics: list[str] = Field(default_factory=list)


class EmotionUpdateRequest(BaseModel):
    realm: Optional[str] = None
    emotion: Optional[str] = None
    intensity: Optional[int] = Field(default=None, ge=0, le=4)
    prosody_mode: Optional[str] = None
    relationship_delta: int = Field(default=0, ge=-2, le=2)


class IntentResponse(BaseModel):
    intent: str
    confidence: float
    categories: list[str] = Field(default_factory=list)
