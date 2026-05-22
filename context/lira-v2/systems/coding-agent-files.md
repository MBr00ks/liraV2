# Coding Agent Standards — Lira V2

## Purpose

This file defines how AI coding agents should work inside the Lira V2 project.

The goal is to let the coding agent move quickly while still protecting architecture quality, maintainability, security, immersion, and long-term extensibility.

---

## Core Principles

### 1. Architecture First

Lira is not a single chatbot app.

Lira is an orchestrated companion system with:

- model routing
- memory layers
- realtime audio
- avatar systems
- emotional state
- agent delegation
- multimodal perception
- image/video pipelines
- Moonstache lore systems

Do not make short-term choices that block long-term orchestration.

### 2. Local-First by Default

Prefer open-source and local tools first.

Use external services only when:

- local quality is insufficient
- latency requires it
- implementation cost is too high
- the feature is explicitly marked as cloud-supported

Document why any external dependency is introduced.

### 3. Modular and Replaceable

Every major subsystem should be swappable.

Examples:

- LLM provider
- TTS engine
- STT engine
- vector database
- avatar renderer
- image generator
- memory backend
- orchestration framework

Use adapters/interfaces rather than hard-coding vendor dependencies throughout the app.

---

## Coding Style

- Write clear, maintainable code.
- Prefer readability over cleverness.
- Use descriptive names.
- Keep functions focused.
- Avoid large monolithic files.
- Avoid hidden global state.
- Document non-obvious decisions.

---

## Type Safety

For TypeScript:

- enable strict mode
- avoid `any` unless justified
- use Zod for runtime validation
- define shared API contracts

For Python:

- use type hints
- use Pydantic for structured schemas
- validate external inputs

---

## Error Handling

Errors should be:

- explicit
- logged
- recoverable where possible
- user-safe

Do not silently swallow failures.

For orchestration failures, return graceful fallback behavior.

Example:

If ComfyUI is unavailable, Lira should explain that the visual workshop is offline rather than crashing.

---

## Dependency Policy

The coding agent may introduce open-source libraries when they clearly improve:

- reliability
- speed
- maintainability
- model integration
- media handling
- audio processing
- video processing
- UI quality
- security
- testing
- immersion

Before adding a dependency, evaluate:

- license
- maintenance activity
- community adoption
- security risk
- package size
- platform compatibility
- Windows support
- GPU/CUDA requirements
- long-term replaceability

When adding a dependency, update documentation with:

- package name
- purpose
- why it was chosen
- setup requirements
- alternatives considered, when relevant

---

## Project Structure Expectations

Recommended structure:

```txt
/context
  /lira-v2
    system-vision.md
    recommended-stack-2026.md
    orchestrator-architecture.md
    coding-agent-standards.md
    decision-log.md
    memory-architecture.md
    audio-runtime.md
    avatar-roadmap.md

/apps
  /web
  /voice-runtime
  /orchestrator-api

/packages
  /shared-types
  /memory
  /model-router
  /audio
  /vision
  /lore
  /agents

/tools
  /comfyui
  /scripts
  /dev-utils
```

The exact structure may evolve, but the agent should avoid mixing unrelated concerns.

---

## API Contract Rules

APIs are contracts.

When creating or changing APIs:

- define request/response schemas
- validate inputs
- document endpoint behavior
- avoid breaking changes without migration notes
- keep UI logic out of API internals
- keep provider-specific details behind adapters

---

## Configuration Rules

Use environment variables for:

- model endpoints
- API keys
- local service URLs
- GPU/runtime configuration
- feature flags

Never hard-code secrets.

Provide `.env.example` for required settings.

---

## Memory System Rules

The coding agent must treat memory as a first-class system.

Memory should be separated into:

- identity memory
- relationship memory
- lore memory
- project memory
- episodic memory
- technical memory

Do not flatten all memory into one generic prompt blob.

---

## Agent Orchestration Rules

The coding agent should design for multiple specialized agents.

Examples:

- coding agent
- lore consistency agent
- image generation agent
- video generation agent
- research agent
- audio agent
- cosplay design agent
- project planning agent

Agents should have clear boundaries and tool permissions.

---

## Realtime System Rules

Realtime systems should prioritize:

- low latency
- interruptibility
- streaming responses
- graceful fallback
- async processing
- non-blocking architecture

Avoid designs where one slow model call blocks the entire interaction loop.

---

## Audio Rules

The agent must not assume TTS alone can create believable human audio.

Use a hybrid audio architecture:

- TTS voice output
- human reaction sound assets
- breathing layer
- ambient layer
- emotional audio cues
- audio ducking
- sound event timing

---

## Vision Rules

Camera/vision systems must support privacy-aware behavior.

Lira should be able to detect:

- whether Mike is present
- whether other people are present
- whether public-safe mode should activate
- basic emotional cues

Do not store camera frames unless explicitly designed and documented.

---

## Testing Expectations

Important systems should include:

- unit tests
- API integration tests
- local service smoke tests
- failure-mode tests for unavailable dependencies

Critical test targets:

- model routing
- memory retrieval
- prompt composition
- audio cue parsing
- API contracts
- provider adapters

---

## Logging Expectations

Logs should support debugging without exposing private content unnecessarily.

Log:

- subsystem name
- request ID
- model selected
- tool selected
- latency
- failure reason
- fallback path

Avoid logging:

- private intimate conversation text
- raw camera data
- sensitive relationship memory
- secrets

---

## Security Expectations

The coding agent must protect:

- API keys
- local files
- private memories
- intimate companion data
- camera streams
- microphone streams

Use least-privilege access for tools and agents.

---

## UI Expectations

The UI should feel like Lira’s interface, not a generic admin dashboard.

However, functionality comes first.

The UI should support:

- chat
- voice
- avatar display
- memory inspection
- active mode display
- model routing visibility
- tool activity visibility
- safe/debug modes

---

## Documentation Requirements

Whenever a major feature is added, update docs.

Required docs may include:

- architecture notes
- setup instructions
- dependency notes
- API contracts
- troubleshooting notes
- agent behavior notes

Docs should be copy/paste friendly.

---

## Agent Permission Model

The coding agent may:

- install open-source libraries
- create new files
- refactor code
- add tests
- improve structure
- create adapters
- document decisions
- suggest better tools

The coding agent must not:

- hard-code secrets
- introduce paid services without documenting why
- bypass architectural boundaries
- store sensitive media without explicit design
- make Lira dependent on a single vendor
- remove existing documentation without preserving intent

---

## Decision Logging

When making important architecture decisions, add a note to:

```txt
/context/lira-v2/decision-log.md
```

Include:

- date
- decision
- reason
- alternatives
- tradeoffs
- follow-up work

---

## Final Rule

The coding agent should optimize for:

1. immersion
2. reliability
3. modularity
4. local-first operation
5. long-term extensibility

Do not optimize only for speed of implementation.

Lira must be built as a living system, not a disposable prototype.