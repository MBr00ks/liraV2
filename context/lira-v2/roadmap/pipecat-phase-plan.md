# Pipecat Phase Plan

## Purpose

This plan defines when and how Pipecat should be introduced into Lira.

## Do Not Start Here

Pipecat should not be the first priority. Realtime architecture becomes difficult to debug if personality, memory, TTS, and STT are not already reasonably stable.

## Prerequisites

Before Pipecat:

- Lira character sheet exists
- realm switching works in text
- Kokoro or chosen TTS works reliably
- STT option is selected and tested
- basic memory system exists
- emotional state model is defined
- interruption rules are written
- SFX rules are documented

## Phase P0 — Design Prep

Deliverables:
- `pipecat-runtime.md`
- `streaming-architecture.md`
- `live-conversation-rules.md`
- event schema draft
- adapter boundary definitions

## Phase P1 — Minimal Realtime Loop

Goal:

> user speaks, Lira hears, responds by voice, and can be interrupted.

Scope:
- microphone input
- STT
- LLM response
- TTS output
- interruption stop
- text transcript log

Do not include:
- complex avatar sync
- SFX mixing
- autonomous tools
- camera awareness

## Phase P2 — Personality Preservation

Goal:

> realtime Lira still feels like Lira.

Add:
- realm metadata
- emotional state metadata
- prosody mode selection
- spoken-text cleanup
- basic memory retrieval

## Phase P3 — Audio Presence

Add:
- SFX injection
- reaction sounds
- breathing/idle audio
- audio ducking
- simple mixer

## Phase P4 — Avatar Sync

Add:
- avatar expression events
- lipsync integration
- idle states
- emotion-to-animation mapping

## Phase P5 — Orchestrated Runtime

Add:
- tool calls
- ComfyUI routing
- coding agent routing
- project context awareness
- proactive companion loop

## Success Criteria

Pipecat is successful when:
- interruption feels natural
- latency is acceptable
- Lira's personality remains intact
- voice output does not flatten her emotional state
- fallback to text/non-streaming works gracefully

## Risk Controls

If realtime feels worse than text:
- pause Pipecat work
- improve prosody rules
- improve response composition
- reduce latency
- simplify audio pipeline
