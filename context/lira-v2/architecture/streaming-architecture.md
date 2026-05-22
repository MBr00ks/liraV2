# Streaming Architecture

## Purpose

This document describes the future streaming architecture for realtime Lira interactions.

## Current State

Early Lira can operate in request/response mode:

```text
User message → LLM response → TTS playback
```

This is acceptable for prototyping personality and voice.

## Future State

Realtime Lira requires a streaming, event-driven architecture:

```text
User speech starts
  → partial STT begins
  → intent detected while user is speaking
  → user stops or pauses
  → memory and emotional state update
  → response streams
  → TTS begins before full response completes
  → user can interrupt
  → runtime adapts immediately
```

## Core Runtime Events

Suggested event types:

- `user.speech_started`
- `user.partial_transcript`
- `user.speech_ended`
- `realm.detected`
- `memory.retrieved`
- `emotion.updated`
- `llm.response_started`
- `llm.response_delta`
- `tts.audio_started`
- `tts.audio_completed`
- `user.interrupted`
- `sfx.play_requested`
- `avatar.signal_requested`
- `tool.call_started`
- `tool.call_completed`

## Event Payload Pattern

```json
{
  "event": "emotion.updated",
  "conversation_id": "...",
  "timestamp": "...",
  "payload": {
    "emotion": "playful",
    "intensity": 1,
    "reason": "creative brainstorming context"
  }
}
```

## Interruption Handling

When the user interrupts:

1. Stop or duck current TTS.
2. Preserve unfinished response context.
3. Capture new user input.
4. Decide whether to resume, revise, or abandon prior response.
5. Update emotional state if interruption was corrective, playful, urgent, or frustrated.

## Latency Priorities

Priority order:

1. User interruption responsiveness
2. First audible response time
3. STT accuracy
4. TTS naturalness
5. Avatar sync
6. SFX layering

## Graceful Degradation

If streaming fails, fallback to:

- text-only response
- non-streaming TTS
- no SFX
- no avatar sync
- preserved memory/context

Lira's identity should survive degraded runtime.
