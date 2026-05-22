# SFX and Reactions

## Purpose

Lira's realism should come from a hybrid audio system, not TTS alone.

## Audio Layers

1. TTS voice
2. Human reaction sounds
3. breathing/idle presence
4. ambient environment
5. interface/tool sounds
6. avatar sync metadata

## Reaction Categories

### Positive
- soft laugh
- amused hum
- pleased breath
- playful giggle

### Frustrated
- small sigh
- restrained annoyed breath
- dry exhale
- quiet grr-like reaction if character-appropriate

### Thinking
- thoughtful hum
- small pause
- breath before response

### Intimate / Between
- softer laugh
- slower breath
- playful pause
- warmer vocal texture

## Triggering Principle

Do not insert SFX randomly. SFX must support emotional state and context.

## Stage Direction Conversion

Input:

```text
*She laughs softly.* You're not wrong.
```

Runtime output:

```json
{
  "spoken_text": "You're not wrong.",
  "sfx": "soft_laugh",
  "prosody": "playful_sassy"
}
```

## Audio Sprite / Long WAV Handling

If a WAV contains multiple reactions, the system should eventually support:
- manual slicing
- cue markers if available
- start/end timestamps
- normalized volume
- categorized metadata

Example catalog entry:

```json
{
  "id": "soft_laugh_01",
  "file": "female_reactions_pack_01.wav",
  "start_ms": 1820,
  "end_ms": 2840,
  "category": "positive",
  "intensity": 1
}
```

## Failure Modes

Avoid:
- too many giggles
- repetitive sighs
- mismatched reactions
- reactions that interrupt speech awkwardly
- NSFW-coded sounds leaking into normal assistant mode
