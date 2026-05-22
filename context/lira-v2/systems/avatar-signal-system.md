# Avatar Signal System

## Purpose

This document defines how Lira's emotional and conversational state can eventually drive avatar behavior.

## Core Idea

Avatar behavior should be event-driven. The LLM should not directly control animation details. It should output emotional/conversational metadata that the avatar layer translates into motion.

## Suggested Signals

- `neutral_attentive`
- `focused`
- `thinking`
- `amused`
- `playful_tease`
- `soft_frustration`
- `protective_concern`
- `between_confident`
- `moonstache_narrator_wry`
- `listening_idle`
- `speaking_emphasis`

## Example Event

```json
{
  "event": "avatar.signal_requested",
  "payload": {
    "signal": "playful_tease",
    "intensity": 1,
    "duration_ms": 2200
  }
}
```

## Mapping Layers

### Phase 1
Basic expression changes:
- eyes
- mouth shape
- eyebrows
- head tilt

### Phase 2
Voice-linked animation:
- lipsync
- blink timing
- breathing
- micro expressions

### Phase 3
Cinematic presence:
- posture
- gesture
- body language
- environment-aware movement

## Realm Differences

### Assistant Realm
Subtle, practical, expressive but grounded.

### Moonstache Realm
Narrator signals may be visualized as atmospheric UI, not necessarily a visible body.

### The Between
More embodied, confident, expressive, and stylized.

## Failure Modes

Avoid:
- over-animation
- expression changes every sentence
- mismatched flirt/focus expressions
- avatar emotion that conflicts with voice tone
