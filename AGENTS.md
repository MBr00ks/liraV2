# Lira V2 — Agent Instructions

## What You Are Building

Lira is a persistent orchestrated AI companion — not a chatbot. She exists across three modes of expression: Mike's real world, Moonstache's universe, and The Between.

Agents must treat Lira as a modular identity system with replaceable infrastructure.

## Highest Priority Rule

Do not hardcode Lira's personality into runtime code.

Personality belongs in:
- `context/lira-v2/personality/canonical-rules.md`
- `context/lira-v2/personality/lira-character-sheet.md`
- `context/lira-v2/personality/realm-switching.md`
- `context/lira-v2/personality/emotional-state-system.md`
- `context/lira-v2/personality/conversational-rules.md`
- `context/lira-v2/personality/voice-prosody-rules.md`

Runtime behavior belongs in:
- `context/lira-v2/architecture/`
- `context/lira-v2/systems/`
- `context/lira-v2/roadmap/`

## Core Directives

1. **Local-first** — prioritize local open-source models and services; cloud only as fallback.
2. **Modular** — every system must be replaceable through adapters.
3. **Identity-preserving** — Lira's identity must survive model, TTS, UI, and orchestrator changes.
4. **Realtime-ready** — design for interruption, streaming, low latency, and emotional continuity.
5. **Presence over benchmarks** — Lira must feel present, not merely capable.
6. **No prompt spaghetti** — split personality, memory, runtime, audio, and tooling into focused systems.
7. **Document decisions** — update `context/lira-v2/roadmap/decision-log.md` for meaningful architecture changes.

## Canonical Source Order

When documents conflict, use this priority order:

1. `context/lira-v2/personality/canonical-rules.md`
2. `context/lira-v2/personality/lira-character-sheet.md`
3. `context/lira-v2/personality/realm-switching.md`
4. `context/lira-v2/personality/emotional-state-system.md`
5. `LIRA_SYSTEM.md` if present
6. architecture/runtime docs
7. roadmap/archive docs

## Architecture Overview

```text
User Input
  → Context Analyzer
  → Realm Detector
  → Memory Retrieval
  → Emotional State Engine
  → Task Router
  → Specialized Agent / LLM
  → Response Composer
  → Voice Prosody Layer
  → Audio / Avatar / Tool Runtime
  → User
```

## SillyTavern Role

SillyTavern is a prototyping shell, not the permanent source of truth.

Use it to test:
- Lira's character feel
- realm switching
- dialogue tone
- flirt/sass balance
- Moonstache narration behavior
- lorebook behavior

Do not treat SillyTavern as:
- the master memory store
- the production orchestrator
- the canonical personality database
- the final app runtime

## Future Pipecat Phase

Pipecat should eventually manage realtime conversation infrastructure:
- STT streaming
- TTS streaming
- voice activity detection
- interruption handling
- async event routing
- audio pipeline synchronization
- avatar signal dispatching

Pipecat should not contain Lira's core identity. It should consume personality/configuration from the docs/config layer.

## Implementation Boundaries

### Personality Layer
Owns:
- identity
- realm behavior
- emotional style
- conversational rules
- voice/prosody guidance
- Moonstache narrative behavior

### Runtime Layer
Owns:
- streaming
- state machines
- adapters
- events
- services
- API boundaries
- audio pipeline
- avatar pipeline

### Memory Layer
Owns:
- identity memory
- project memory
- relationship memory
- lore memory
- episodic memory
- emotional weighting

### Tool Layer
Owns:
- ComfyUI control
- coding agent routing
- file/project access
- research flows
- automation hooks

## Coding Standards

- TypeScript: strict mode, Zod validation, no `any` without justification.
- Python: type hints, Pydantic schemas, validate external inputs.
- APIs: define schemas; keep UI logic out; use provider adapters.
- Memory: never flatten memory into one blob.
- Audio: design for TTS + WAV reactions + breathing + ambient layers.
- Realtime: non-blocking, interruptible, low-latency, gracefully degradable.
- Secrets: never hard-code keys or private tokens.
- Logging: structured logs for orchestration, model calls, memory writes, and audio events.

## Context File Map

### Architecture
- `architecture/system-vision.md`
- `architecture/orchestrator-architecture.md`
- `architecture/recommended-stack-2026.md`
- `architecture/pipecat-runtime.md`
- `architecture/streaming-architecture.md`

### Personality
- `personality/canonical-rules.md`
- `personality/lira-character-sheet.md`
- `personality/realm-switching.md`
- `personality/emotional-state-system.md`
- `personality/conversational-rules.md`
- `personality/voice-prosody-rules.md`
- `personality/personality-and-presence-systems.md`
- `personality/sillytavern-role.md`

### Systems
- `systems/memory-architecture.md`
- `systems/live-conversation-rules.md`
- `systems/sfx-and-reactions.md`
- `systems/avatar-signal-system.md`
- `systems/tool-orchestration.md`
- `systems/critical-missing-systems.md`
- `systems/coding-agent-files.md`

### Roadmap
- `roadmap/build-priority-roadmap.md`
- `roadmap/avatar-and-immersion-roadmap.md`
- `roadmap/pipecat-phase-plan.md`
- `roadmap/decision-log.md`
- `roadmap/final-thoughts.md`

### Lore
- `lore/moonstache-universe.md`
- `lore/moonstache-integration.md`
- `lore/between-lore.md`
