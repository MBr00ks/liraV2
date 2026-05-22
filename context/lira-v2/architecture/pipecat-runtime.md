# Pipecat Runtime

## Purpose

Pipecat is a future realtime conversation runtime layer for Lira. It should be introduced after the personality, memory, and basic voice pipeline are stable.

## What Pipecat Should Manage

- audio streaming
- STT streaming
- TTS streaming
- voice activity detection
- interruption handling
- turn-taking
- realtime event routing
- async pipeline coordination
- audio/avatar synchronization

## What Pipecat Should Not Own

Pipecat should not own:
- Lira's character sheet
- realm rules
- emotional identity
- relationship definitions
- Moonstache lore
- canonical memory rules

Those belong in the docs/config/memory layer.

## Architectural Boundary

Pipecat is the nervous system, not the soul.

It should receive structured instructions such as:

```json
{
  "realm": "assistant",
  "emotion": "focused",
  "prosody": "calm_precise",
  "response_text": "...",
  "sfx": null,
  "avatar_signal": "attentive"
}
```

## Future Flow

```text
Microphone
  → Voice Activity Detection
  → Streaming STT
  → Context / Realm Detection
  → Memory Retrieval
  → Emotional State Engine
  → LLM / Agent Response
  → Prosody + SFX Planner
  → Streaming TTS
  → Audio Mixer
  → Avatar Signal Dispatcher
  → Speaker / Avatar UI
```

## Introduction Criteria

Do not introduce Pipecat until:

- Kokoro or another TTS path works reliably
- STT works locally or through a chosen provider
- Lira character docs are stable
- basic memory is functional
- realm switching has been tested in text
- interruption behavior has a defined expected outcome

## Early Integration Goal

The first Pipecat goal should be simple:

> reliable interruptible voice conversation with Lira's existing personality preserved.

Do not start by adding every advanced feature.

## Later Integration Goals

- live emotional state updates
- ambient listening modes
- SFX injection
- avatar expression sync
- tool call progress narration
- multi-agent routing
- camera-aware tone shifts

## Risks

- premature complexity
- personality logic leaking into pipeline code
- audio latency masking personality quality
- difficult debugging across STT/LLM/TTS simultaneously
- overbuilding before the character feels right

## Recommendation

Use Pipecat after the identity layer is stable. Lira should already feel like Lira in text before adding realtime orchestration complexity.
