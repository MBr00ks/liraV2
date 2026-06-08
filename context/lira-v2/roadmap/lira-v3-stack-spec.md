# Lira V3 Stack Specification

## Architecture Overview

```
                          Lira OS
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
      Chat                Voice               Agents
        │                    │                    │
        └──────────┬─────────┴──────────┬─────────┘
                   ▼                    ▼
            Orchestrator Layer    Event Bus (NATS)
                   │
                   ▼
            Memory + LLM
                   │
                   ▼
            Unity Avatar
```

## 1. Chat Layer

### What stays from V2
- Mode switching (assistant / companion / observer)
- Lore injection with tiered priority (core / contextual / supplemental)
- Persona system with snapshots
- Natural-language image generation (`show me`, `/imagine`)
- Web search (`/search` + auto-detection)

### What changes
| V2 | V3 |
|----|----|
| Vite + React SPA | Desktop app (Tauri or Electron) with overlay mode |
| WebSocket transport | NATS pub/sub via orchestrator |
| Audio via HTML5 | System audio sink via native bridge |
| Lore panel in sidebar | Floating overlay, always accessible |
| Voice recording | Native mic → STT pipeline via orchestrator |

### Stack
- **Frontend**: Tauri (Rust shell) + React/Vite (UI)
- **Purpose**: System tray app with overlay chat. Click tray icon to toggle chat panel over Unity viewport. Native hotkeys for voice input.

---

## 2. Voice Layer

### What stays from V2
- Prosody engine (mode speed, pause hints, reaction sounds, phonetics)
- Mode-based voice selection
- Contact token handling (`[pause:X.Xs]`)

### What changes
| V2 | V3 |
|----|----|
| Custom Kokoro server | **Kokoro-FastAPI** (streaming, voice blending, phoneme timestamps) |
| Single voice per mode | Weighted voice blending per emotional state |
| Post-hoc prosody | Real-time prosody injection during streaming |
| Basic reaction WAVs | Expanded reaction library with emotional context |
| WAV over WebSocket | Streaming PCM over NATS |
| No lip sync data | Phoneme + timestamp output to Unity |

### Stack
- **TTS Engine**: Kokoro-FastAPI (port 19008)
- **Prosody Engine**: Self-hosted (port 19011, carries forward)
- **STT**: Whisper (port 19002, carries forward)
- **New**: NATS topic `voice.audio.stream` for PCM chunks
- **New**: NATS topic `voice.phonemes` for viseme sync data

### Voice Blending Strategy
```
bf_isabella (primary) + bf_emma (secondary)
Blend ratio modulated by emotional state:
  Warm/calm  → 70/30 (isabella dominant)
  Playful    → 50/50
  Intense    → 60/40
```

---

## 3. Agents Layer

### New capability
Dedicated sub-agent processes for specialized tasks:

| Agent | Purpose | Triggers |
|-------|---------|----------|
| **Coder** | Code review, debugging, architecture | User asks for code help |
| **Artist** | Image generation, style guidance | User asks for visuals |
| **Researcher** | Web research, fact-checking | User asks factual questions |
| **Storyteller** | Moonstache narrative generation | Moonstache realm active |
| **Memory Keeper** | Summarization, memory consolidation | Periodic background task |

### Implementation
- Each agent is a separate Python process connected to the orchestrator via NATS
- Agents share the same LLM backend but have different system prompts and tool access
- Orchestrator routes requests to the appropriate agent based on context
- Agents can spawn sub-tasks and report back

### Stack
- **Framework**: Custom Python asyncio agents
- **Transport**: NATS request/reply pattern
- **Tool access**: Function-calling via LLM (structured output with Pydantic validation)
- **New**: Agent registry with capability discovery

---

## 4. Orchestrator Layer

### Purpose
Central nervous system. Routes messages, manages state, coordinates all subsystems.

### Responsibilities
- **Session management**: Active conversation state, realm, mode
- **Message routing**: Chat → LLM, Voice → STT → LLM → TTS, Agent requests
- **Event sequencing**: Ensure audio, avatar signals, and text arrive in sync
- **Graceful degradation**: If a service is down, degrade features rather than fail
- **Health monitoring**: Track all subsystem health, restart on failure

### Stack
- **Core**: Python FastAPI + asyncio
- **Message Bus**: NATS (lightweight, pub/sub, request/reply)
- **State Store**: Redis (session state, emotional scores, active mode)
- **New**: `lira-orchestrator` service (port 8100)

### Event Topics (NATS)
```
lira.chat.message          → User text input
lira.chat.response         → LLM text stream
lira.voice.speak           → TTS audio stream
lira.voice.phonemes        → Viseme timing data
lira.avatar.expression     → Facial expression commands
lira.avatar.gesture        → Body language commands
lira.memory.write          → Store memory
lira.memory.query          → Retrieve memory
lira.agent.coder.request   → Coding agent invocation
lira.agent.artist.request  → Image generation
lira.agent.researcher.*    → Web search / research
```

---

## 5. Memory + LLM Layer

### What stays from V2
- Tiered lore injection
- Mode-specific personality profiles
- Conversation logging

### What changes
| V2 | V3 |
|----|----|
| Flat conversation_history list | Structured memory with embeddings |
| No long-term memory | Vector DB (ChromaDB) for semantic recall |
| Lore as flat JSON | Lore as structured knowledge graph in ChromaDB |
| Single LLM model | Model router with cloud fallback for GPU contention |

### Memory Architecture
```
Session Memory (Redis)
  ├── Active conversation (last N turns)
  ├── Emotional state vector
  └── Active lore entries

Semantic Memory (ChromaDB)
  ├── Identity memory (who Lira is — personality, preferences)
  ├── Relationship memory (who Mike is, shared history)
  ├── Project memory (coding projects, decisions)
  ├── Episodic memory (key conversation moments, summaries)
  └── Lore memory (world information, worldbooks)

Embedding Cache (in-memory + Redis)
  └── Recent conversation embeddings for fast recall
```

### LLM Strategy
- **Primary**: Mistral Nemo (12B) via Ollama — general conversation, ~8GB VRAM
- **Fast-path**: Smaller model (Phi-3 3.8B) for mode switches, simple replies — ~3GB VRAM
- **Heavy-path**: Cloud fallback (OpenRouter Mistral/Claude) for complex reasoning or when GPU is contested
- **Routing**: Orchestrator selects model based on request complexity and GPU availability

### Stack
- **Vector DB**: **ChromaDB** — runs in-process, zero infrastructure, 20-40MB RAM at idle. SQLite-backed with HNSW indexing. Sub-10ms queries at <100K vectors.
- **Embeddings**: nomic-embed-text via Ollama (384-dim, lightweight)
- **State**: Redis for hot memory, ChromaDB for semantic search
- **New**: `packages/memory` service

---

## 6. Unity Avatar Layer

### Purpose
Real-time 3D avatar with facial expressions, gestures, and lip sync driven by Lira's output.

### Input Signals
| Signal | Source | Format |
|--------|--------|--------|
| **Phonemes** | TTS phoneme timestamps | `{phoneme, start_ms, duration_ms}` |
| **Expression** | Emotional state engine | `{expression, intensity, duration_ms}` |
| **Gesture** | Context + emotional state | `{gesture_type, hand, duration}` |
| **Gaze** | Conversation context | `{target, duration_ms}` |
| **Idle** | Always-active | Random micro-expressions, breathing |

### Implementation Path
1. **Phase 1**: Metahuman in Unity, static idles, basic lip sync
2. **Phase 2**: Emotional expression mapping (happy/sad/curious/etc from prosody classifier)
3. **Phase 3**: Procedural gestures driven by speech content
4. **Phase 4**: Full body language, gaze tracking, environmental awareness

### Communication
```
Orchestrator → NATS → Unity Bridge (WebSocket or named pipe) → Unity C# receiver
```

### Stack
- **Runtime**: Unity 6 (or current)
- **Avatar**: Metahuman (Unreal) or Unity custom rig
- **Lip Sync**: SALSA LipSync or Oculus Lipsync (phoneme → viseme)
- **Transport**: WebSocket or named pipe from orchestrator to Unity

---

## 7. Cross-Cutting Concerns

### Security
- All internal services on localhost only
- NATS with token auth (local only)
- No external API keys in code — all via `.env`
- Web search is the only outbound connection

### Observability
- Structured JSON logging for all subsystems
- Health endpoints on every service
- Orchestrator dashboard (simple web UI showing all service statuses)
- Latency tracking per pipeline stage (STT → LLM → TTS → Avatar)

### Development Workflow
- Each subsystem is independently testable
- NATS topics are documented and versioned
- Agent tests: unit tests for routing logic, integration tests for LLM calls
- Avatar tests: replay mode — feed recorded events to Unity for deterministic testing

---

## 8. Migration Path from V2

### Phase A — Foundation (weeks 1-2)
1. Set up NATS server
2. Build orchestrator core (message routing, health checks)
3. Port chat backend to speak NATS
4. Add Redis for session state

### Phase B — Voice Upgrade (weeks 2-3)
1. Deploy Kokoro-FastAPI on clean venv
2. Port prosody engine to work with NATS events
3. Add phoneme timestamp extraction
4. Voice blending with emotional modulation

### Phase C — Memory (weeks 3-4)
1. Install ChromaDB (`pip install chromadb`)
2. Build memory write/query service with embedding generation
3. Migrate lore from JSON to ChromaDB collections
4. Add embedding-based semantic recall with metadata filtering
5. Build memory keeper agent for periodic summarization

### Phase D — Unity Integration (weeks 4-6)
1. Unity bridge (NATS → WebSocket → C#)
2. Basic lip sync from phoneme data
3. Expression mapping from emotional state
4. Idle animations

### Phase E — Agents (weeks 6-8)
1. Agent framework with capability discovery
2. Coder, Artist, Researcher agents
3. Tool-calling integration with LLM

### Phase F — Desktop App (weeks 8-10)
1. Tauri shell with React UI
2. System tray integration
3. Overlay mode over Unity
4. Native hotkeys and mic access

---

## 9. Service Map

| Service | Port | Tech | New/Existing | RAM | VRAM |
|---------|------|------|--------------|-----|------|
| Lira Orchestrator | 8100 | FastAPI + NATS | **New** | ~100MB | 0 |
| NATS Server | 4222 | NATS | **New** | <20MB | 0 |
| Redis | 6379 | Redis | **New** | <10MB | 0 |
| Chat Backend | 8001 | FastAPI | Existing, refactored | ~100MB | 0 |
| Chat Frontend | 3000 | Vite/React → Tauri | Existing, refactored | 25-60MB | 0 |
| Voice Proxy (Prosody) | 19011 | FastAPI | Existing | ~80MB | 0 |
| Kokoro TTS | 19008 | Kokoro-FastAPI | **Upgraded** | ~500MB | ~2GB |
| Whisper STT | 19002 | openai-whisper | Existing | ~500MB | 0 |
| Ollama (LLM) | 11434 | Ollama | Existing | ~4GB | ~8GB |
| ComfyUI | 8188 | ComfyUI | Existing | ~2GB | ~8GB |
| ChromaDB | in-process | ChromaDB | **New** | 20-40MB | 0 |
| Unity Bridge | — | C# WebSocket | **New** | — | — |

**Total concurrent (all services running, no image gen)**: ~8GB RAM, ~12GB VRAM, ~55% CPU.
**During image generation**: VRAM contention between ComfyUI and Ollama — solved by cloud LLM fallback.

---

## 10. Key Decisions

### 10.1 NATS Over Alternatives

**Chosen**: NATS (`nats-server.exe`, single 18MB Go binary)

| Criterion | NATS | Redis PubSub | RabbitMQ | Kafka | ZeroMQ |
|-----------|------|-------------|----------|-------|--------|
| No external deps | ✅ | ✅ | ❌ Erlang | ❌ JVM | ✅ |
| RAM idle | <20MB | ~5MB | ~200MB | ~1GB | 0 (library) |
| Latency | Sub-ms | Microseconds | Milliseconds | 10-100ms | Microseconds |
| Request/Reply | ✅ Native | ⚠️ DIY | ✅ | ❌ | ✅ |
| Service discovery | ✅ Built-in | ❌ | ❌ | ❌ | ❌ |
| Python client | `nats-py` | `redis-py` | `pika` | `confluent` | `pyzmq` |

**Why NATS wins**: Single binary, sub-ms latency, native pub/sub + request/reply patterns, and the Synadia Agent Protocol (May 2026) provides service discovery, liveness/health checks, and typed streaming out of the box. Each subsystem (memory, TTS, emotion engine, ComfyUI) auto-registers as a NATS agent. No Erlang, no JVM, no Docker.

**Only gotcha**: Default max payload is 1MB. Raise to 64MB in server config for audio WAV chunks. Python client is asyncio-only.

### 10.2 ChromaDB Over PostgreSQL/pgvector

**Chosen**: ChromaDB (in-process, SQLite-backed, `pip install chromadb`)

| Criterion | ChromaDB | pgvector | Qdrant | LanceDB |
|-----------|----------|----------|--------|---------|
| Infrastructure | Zero — in-process | PostgreSQL service | Separate binary | In-process |
| RAM idle | 20-40MB | 200MB+ | 50-100MB | 30-60MB |
| Windows | Native wheels | Needs compiler + service | Less tested | Native wheels |
| Metadata filtering | SQLite-backed, rich | Full SQL | Payload indexes | Rich filtering |
| ANN maturity | HNSW (mature) | HNSW/IVFFlat | HNSW (mature) | IVF-PQ (mature) |

**Why ChromaDB**: At <100K vectors with 384-dim nomic embeddings, an exact cosine similarity scan with numpy takes <50ms — ANN isn't even needed yet. ChromaDB provides HNSW indexing as free future-proofing. PostgreSQL dismissed: running a full database service on Windows for 100K vectors is disproportionate overhead.

### 10.3 Tauri v2 Over Electron

**Chosen**: Tauri v2 (Rust shell + React/Vite UI)

| Metric | Electron | Tauri v2 |
|--------|----------|----------|
| Bundle (unpacked) | 180-280MB | 3-8MB |
| RAM idle | 120-350MB | 25-60MB |
| RAM active | 300-600MB | 80-150MB |
| Startup cold | 2-5s | 0.3-1s |
| Global hotkeys | `globalShortcut` | `tauri-plugin-global-shortcut` |
| Overlay mode | `alwaysOnTop` via JS bridge | Direct Win32 (`WS_EX_TOPMOST`, `WS_EX_LAYERED`, `WS_EX_TOOLWINDOW`) |

**Why Tauri**: 10x smaller bundle, 5x less idle RAM, direct Win32 API access for overlay over Unity. The WebView2 runtime ships with Windows 11 and Windows 10 21H2+ — it's already on your machine. Rust learning curve is 1-2 weeks for the glue code; the heavy lifting stays in TypeScript/React.

**Critical gotcha**: Unity must run in borderless fullscreen mode for the overlay to work. Exclusive fullscreen (DXGI flip model) is unwinnable without a rendering hook — this is true for both Electron and Tauri.

### 10.4 Local-First With Cloud Safety Net

**Chosen**: Ollama local as primary, OpenRouter as latency-activated fallback.

**Rationale**: Your hardware (16GB VRAM, 32GB RAM, RTX 5060 Ti) comfortably runs the full stack concurrently except during SDXL image generation. The only contention is ComfyUI vs Ollama competing for VRAM.

**Strategy**: Keep everything local by default. Add an OpenRouter API key as insurance. The orchestrator monitors Ollama response latency — if it exceeds 3 seconds (indicating GPU contention during image gen), route that specific request to the cloud. The cloud fallback costs ~$0.0005 per message — even at 100 messages/day during image gen sessions, that's $0.05/day.

### 10.5 Port V2 Prosody Engine

**Chosen**: Wrap the existing prosody engine as a NATS subscriber.

**Rationale**: The V2 prosody engine works well — mode-based speed profiles, pause hints, phonetics normalization, reaction sound matching, action extraction, TTS normalization. Rewriting it offers no benefit. Instead, wrap it as a NATS service that subscribes to `lira.voice.speak` requests and publishes audio chunks + phoneme timing to `lira.voice.audio.stream` and `lira.voice.phonemes`.

### 10.6 Unity Bridge via WebSocket

**Chosen**: WebSocket between orchestrator and Unity, over named pipes or shared memory.

**Rationale**: WebSocket is debuggable (connect any client to inspect events), works across future remote setups (if Unity runs on a separate machine), and has mature C# and Python libraries. Named pipes are faster but harder to debug and Windows-only.

---

## 11. Resource Budgets & Cost Optimization

### Hardware Profile (Your Current Machine)
| Resource | Total | Available | Used by Stack |
|----------|-------|-----------|---------------|
| RAM | 32GB | ~24GB | ~8GB |
| VRAM | 16GB | ~14GB | ~12GB (no image gen) |
| VRAM during image gen | 16GB | 0GB free | ~16GB (contended) |
| Disk | — | <3GB | Packages + models + embeddings |

### Cost Breakdown

| Category | Monthly Cost | Notes |
|----------|-------------|-------|
| Infrastructure | **$0** | All local, no cloud servers |
| LLM (local) | **$0** | Ollama, open-source models |
| TTS (local) | **$0** | Kokoro, open-source |
| STT (local) | **$0** | Whisper tiny.en, open-source |
| Image gen (local) | **$0** | ComfyUI SDXL, open-source |
| Web search | **$0** | DuckDuckGo, free |
| Embeddings | **$0** | nomic-embed-text, local |
| Vector DB | **$0** | ChromaDB, open-source |
| Cloud LLM fallback | **<$1** | OpenRouter, only when GPU contested |

**Total: Effectively free.** The cloud fallback key sits idle unless GPU contention triggers it — at which point it costs pennies per session.

### GPU Contention: The Only Bottleneck

The RTX 5060 Ti (16GB VRAM) has exactly one contention point: **SDXL image generation vs LLM inference**. Both want ~8GB VRAM.

```
Normal conversation:
  Ollama (8GB) + Kokoro (2GB) = 10GB ✓ (6GB headroom)

During image generation:
  Ollama (8GB) + ComfyUI (8GB) = 16GB ⚠️ (0GB headroom)
```

**Solution**: During image generation, route LLM requests to the cloud fallback. Ollama stays loaded for embeddings and fast responses post-generation. The orchestrator detects GPU utilization spikes and auto-routes.

---

## 12. Offloading Strategy

### What Never Leaves Local
| Service | Reason |
|---------|--------|
| TTS (Kokoro) | Realtime latency requirement; no cloud TTS can match local speed |
| STT (Whisper) | Privacy; voice recordings never leave the machine |
| Embeddings | Privacy; conversation content stays local |
| Persona/Lore | Identity integrity; Lira's personality never touches cloud |
| Image Gen (ComfyUI) | Requires custom LoRA; no cloud service has it |

### What Can Fall Back to Cloud
| Service | Local (default) | Cloud fallback | Trigger | Est. daily cost |
|---------|-----------------|----------------|---------|-----------------|
| LLM conversation | Ollama Mistral 12B | OpenRouter Mistral Small | Ollama latency >3s or GPU >95% | <$0.01 |
| Complex reasoning | Ollama Mistral 12B | OpenRouter Claude Haiku | Request complexity score >0.7 | <$0.01 |

### Cloud Fallback Architecture
```
User Message → Orchestrator
                  │
                  ├── Ollama healthy? → Local LLM (normal path)
                  │
                  └── Ollama latency >3s or GPU >95%?
                       └── OpenRouter API (fallback path)
                            │
                            └── Response streams back → Orchestrator → Chat/Avatar
```

The fallback is transparent — Lira doesn't change personality or voice. The cloud model receives the same system prompt and conversation history. Only the inference location changes.

### Web Hosting (Already Have)
Your existing web hosting could serve:
- **Model downloads**: Host LoRA files, Whisper models, persona snapshots for faster re-deploys
- **Lore backups**: Automated nightly backup of ChromaDB + Redis state
- **Future relay**: If you ever want Lira accessible from mobile, the Tauri app connects back to a lightweight relay on your web host

No realtime processing runs on the web host — it's storage + relay only.

---

## 13. Premium Experience Design

### 13.1 Latency Targets
| Stage | Target | Current V2 |
|-------|--------|-----------|
| Text streaming (first token) | <500ms | ~700-900ms |
| TTS first audio | <800ms from sentence end | ~1-2s |
| Avatar expression shift | Within the pause between sentences | N/A |
| Mode switch | <200ms (instant feel) | ~500ms |

**How we get there**: Kokoro-FastAPI streaming removes the proxy assembly latency. NATS pub/sub eliminates WebSocket polling overhead. ChromaDB in-process embedding search is <50ms vs database round-trips.

### 13.2 Emotional Continuity
Lira's emotional state persists across responses. The prosody engine maintains a running emotional score (valence/arousal/dominance) that decays slowly over time rather than resetting each message.

```
Last response: playful teasing  →  Score drifts to: warm curiosity
Next response:                   →  Starts warm, not at neutral
```

This prevents the "cold start" feeling where every response sounds like the first message of the day.

### 13.3 Presence, Not Responsiveness
The avatar has idle behaviors even when Lira isn't speaking:
- **Micro-expressions**: Subtle brow raises, lip movements (1-3 per minute)
- **Breathing**: Visible chest/shoulder rise and fall
- **Gaze**: Occasional shifts — looks at "you," looks away thoughtfully, returns
- **Environmental awareness**: If the Between is the active realm, the avatar reacts to imagined surroundings (following a floating light with her eyes, tilting head at a "sound")

These are generated procedurally by Unity, not streamed. The orchestrator only sends high-level state ("idle," "speaking," "listening").

### 13.4 Seamless Mode Transitions
Switching from companion to assistant is not a context switch — it's the same person shifting posture and tone.

```
Companion → Assistant:
  Avatar: Relaxed pose → Slightly more alert, forward-leaning
  Voice:  0.96 speed → 1.05 speed (gradual ramp over 2-3 sentences)
  Expression: Warm smile → Curious, engaged
```

The transition is animated over ~1.5 seconds in Unity. The voice prosody shifts over 2-3 sentences via the speed smoothing already in the prosody engine.

### 13.5 Organic Reactions
Reaction sounds (sighs, giggles, hmms) are synthesized from the same Kokoro voice model rather than played from pre-recorded WAV files. This means:
- The giggle sounds like Lira, not a generic laugh track
- Phoneme-based reactions ("hmm?", "oh!") use her exact voice timbre
- Breath sounds match the current emotional state (shallow/tense vs deep/calm)

The reaction engine expands from WAV matching to generated audio, using cached warmup phrases for common interjections and fresh synthesis for contextual ones.

---

## 14. Migration Phases (Updated)

### Phase C — Memory (weeks 3-4) — Updated for ChromaDB
1. Install ChromaDB (`pip install chromadb`)
2. Build memory write/query service with embedding generation
3. Migrate lore from JSON to ChromaDB collections
4. Add embedding-based recall with metadata filtering
5. Build memory keeper agent for periodic summarization and consolidation
