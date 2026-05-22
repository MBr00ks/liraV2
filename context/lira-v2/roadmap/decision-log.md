# Lira V2 Decision Log

## Purpose

This file records important architecture and tooling decisions for Lira V2.

Use this when a decision affects:

- architecture
- dependencies
- model selection
- memory design
- audio design
- avatar design
- orchestration
- privacy
- realtime behavior

---

## Decision Entry Template

### YYYY-MM-DD — Decision Title

#### Decision

Describe the decision.

#### Reason

Explain why this was chosen.

#### Alternatives Considered

- Option 1
- Option 2
- Option 3

#### Tradeoffs

List the tradeoffs.

#### Follow-up Work

List anything that needs to happen later.

---

## Initial Decisions

### 2026-05-18 — Lira is an Orchestrated Entity, Not a Single Model

#### Decision

Lira will be built as an orchestrated companion system rather than a single chatbot or single LLM wrapper.

#### Reason

The project requires realtime voice, memory, avatar control, image/video generation, agent routing, lore management, and emotional continuity.

No single model or frontend can own all of that cleanly.

#### Alternatives Considered

- Single Ollama chatbot
- SillyTavern-only implementation
- Cloud-only assistant

#### Tradeoffs

More complex architecture, but far more extensible.

#### Follow-up Work

Build model router, memory layers, and realtime audio runtime.

---

### 2026-05-18 — Local-First, Cloud-Optional

#### Decision

Use open-source local tooling wherever practical, with cloud/external services only when quality or performance requires it.

#### Reason

Lira should remain private, flexible, unrestricted, and cost-controlled.

#### Alternatives Considered

- Full cloud stack
- Fully local-only without exceptions

#### Tradeoffs

Local tooling requires more setup and tuning, but protects privacy and long-term control.

#### Follow-up Work

Define dependency review policy and service fallback rules.

---

### 2026-05-19 — Ollama Adapter as Default LLM Client

#### Decision

The orchestrator uses `OllamaClient` as the default LLM adapter, communicating via `http://localhost:11434/api/chat` with `qwen3:32b`.

#### Reason

Ollama is already running locally, supports streaming, and provides the model we use for prototyping. The adapter exposes `chat()` and `stream_chat()` methods that match the companion loop interface.

#### Alternatives Considered

- Direct OpenAI-compatible API calls
- LiteLLM as a multi-provider router
- Hardcoded httpx calls in companion loop

#### Tradeoffs

Ollama adds ~29s latency for 32B on RTX 3060 Ti. Streaming reduces perceived latency. The adapter is swappable when we introduce Pipecat or a model router.

#### Follow-up Work

- Add model router for fallback/switching
- Wire memory retriever/writer (Postgres + Qdrant)
- Optimize first-token latency with smaller model for fast responses

---

### 2026-05-20 — Streaming SFX/Avatar Event Injection

#### Decision

SSE stream emits typed events: `avatar_signal` (once at start), `sfx_event` (when action markers detected), and `message` (content chunks). Action markers stripped from spoken content in real-time.

#### Reason

Streaming clients need to react to avatar changes and play SFX before TTS generates the cleaned speech. Typed events allow the client to handle each signal type independently without parsing content.

#### Alternatives Considered

- Single event type with metadata field
- Post-stream SFX/avatar (loses realtime benefit)
- Client-side marker parsing (duplicates logic)

#### Tradeoffs

SSE stream now has 3 event types instead of 1. Client must handle event routing. Partial action markers (unclosed `*`) are stripped to prevent leaking stage directions into TTS. Memory write happens at stream end, not per-chunk.

#### Follow-up Work

- Add per-sentence SFX injection for longer responses
- Implement avatar signal duration tracking across sentences
- Add breathing/ambient audio layer signals

---

#### Decision

Memory writes pass through a lightweight summarizer that filters transient content and extracts durable facts. Rules-based approach (no LLM call) for speed.

#### Reason

Raw transcripts bloat memory and dilute retrieval quality. Summarization ensures only meaningful facts, decisions, preferences, and emotional moments are stored. Between realm and high-emotion states always store (relationship continuity).

#### Alternatives Considered

- LLM-based summarization (adds latency)
- Store everything and rely on importance filtering
- No summarization, just truncate

#### Tradeoffs

Rules-based approach is fast but less nuanced than LLM summarization. May miss subtle emotional context. Can be upgraded to LLM summarizer later when latency budget allows.

#### Follow-up Work

- Add LLM summarization for high-importance memories
- Implement memory decay/forgetting policy
- Add cross-reference linking between related memories

---

#### Decision

Memory uses Postgres for structured storage (6 categories: identity, relationship, project, lore, episodic, technical) and Qdrant for semantic vector search. Embeddings generated via Ollama's `nomic-embed-text` model.

#### Reason

Postgres provides reliable ACID storage for structured memory with importance weighting. Qdrant enables semantic retrieval across categories. Hybrid approach ensures memory works even if one service fails.

#### Alternatives Considered

- Postgres-only with pgvector
- Qdrant-only with payload filtering
- SQLite + FAISS for fully local setup

#### Tradeoffs

Requires two services running. Qdrant collection auto-created on first upsert. Embedding model adds ~2s overhead per write. Graceful fallback to category search if vector search fails.

#### Follow-up Work

- Add memory summarization before write
- Implement memory decay/forgetting policy
- Add cross-category retrieval with importance weighting

---

#### Decision

Companion responses include `avatar_signal` and `sfx_event` payloads derived from emotion/realm state and LLM output text.

#### Reason

Avatar behavior and reaction sounds must be event-driven, not random. Stage directions (`*action*`) are stripped from spoken text and mapped to SFX categories. Emotion/realm state drives avatar signal selection with intensity/duration scaling.

#### Alternatives Considered

- LLM outputs JSON with explicit SFX/avatar commands
- Hardcoded SFX per emotion
- No SFX layer (TTS only)

#### Tradeoffs

Parsing stage directions is fragile but matches how LLMs naturally express physical presence. Dedicated SFX mapping ensures consistency. Avatar signals are decoupled from TTS timing for future lipsync integration.

#### Follow-up Work

- Add SFX audio files to `public/audio/reactions/`
- Implement avatar signal consumer (LiveKit or custom)
- Add per-sentence SFX injection for streaming mode

---

#### Decision

SillyTavern may be used for early immersion, prompt, roleplay, NSFW, and lorebook testing, but it will not be the core Lira architecture.

#### Reason

Lira needs orchestration, realtime interruption, camera awareness, agent routing, emotional state, and custom memory systems beyond SillyTavern’s core strengths.

#### Alternatives Considered

- Make SillyTavern the main app
- Avoid SillyTavern entirely

#### Tradeoffs

Using SillyTavern speeds experimentation but requires a later migration path.

#### Follow-up Work

Create a SillyTavern bridge strategy and define what data can migrate from Tavern into Lira Core.