# Recommended Lira Stack — 2026

## Coding Agent Standards

See:

- /context/lira-v2/coding-agent-standards.md
- /context/lira-v2/decision-log.md

The coding agent may use open-source libraries when they improve reliability, maintainability, immersion, model integration, audio/video handling, testing, or performance.

All major dependency decisions should be documented.


# PRIMARY ARCHITECTURE

## Core Orchestrator

### Primary Choice

- LangGraph
- FastAPI
- Python

Reason:

- Excellent orchestration
- State-aware
- Agent routing
- Flexible memory integration
- Strong local ecosystem

---

# LLM STACK

## Fast Conversational Model

### Recommended

- Qwen3 32B
- Gemma 3
- DeepSeek R1 Distill

Purpose:

- Fast conversation
- Companion interaction
- Realtime dialogue
- Emotional continuity

---

## Reasoning / Technical Model

### Recommended

- DeepSeek R1
- Devstral
- OpenCode models
- Qwen coder variants

Purpose:

- Coding
- Architecture
- Technical planning
- Agent execution

---

## Creative Narrative Model

### Recommended

- Mistral Large
- Magnum
- Midnight Miqu
- Dolphin variants

Purpose:

- Storytelling
- Roleplay
- Lore writing
- Emotional dialogue

---

# MODEL ROUTING STRATEGY

## Example

Realtime chat:
→ Qwen3

Coding task:
→ Devstral

Moonstache narration:
→ Magnum

Long reasoning:
→ DeepSeek R1

Visual analysis:
→ Vision model

---

# LOCAL MODEL HOSTING

## Recommended

### Ollama

Use for:

- Simplicity
- Local routing
- Easy model swaps

### vLLM

Use later for:

- Advanced batching
- Concurrent requests
- High performance inference

---

# SPEECH TO TEXT

## Recommended

### Whisper.cpp

Fast local transcription.

### Faster-Whisper

Best balance currently.

---

# TTS SYSTEM

## Primary Recommendation

### Kokoro TTS

Why:

- Emotional tone potential
- Fast
- Natural
- Excellent for companion AI

---

## Secondary Layer

### XTTSv2

Use for:

- Voice cloning
- Special scenes
- Character variants

---

# HUMAN SOUND SYSTEM

IMPORTANT:

Do NOT rely entirely on TTS models for:

- Laughing
- Giggling
- Breathing
- Sighing
- Growling
- Whispering
- Vocal reactions

Use a hybrid audio system.

---

## Hybrid Audio Pipeline

LLM generates:

[action:giggle_soft]
[action:breath_slow]
[action:whisper_close]

Audio engine injects:

- WAV assets
- layered ambience
- positional audio
- emotional effects

This is FAR more believable.

---

# AVATAR SYSTEM

## Current Best Path

### Phase 1

- VTube Studio
- PNGTuber+
- Live2D

### Phase 2

- Unreal Engine MetaHuman
- ACE/NVIDIA Audio2Face
- Custom Blender rigs

### Phase 3

- Fully custom stylized avatar
- Arcane-inspired rendering
- Realtime body language
- Gesture system
- Emotion engine

---

# VISION SYSTEM

## Recommended

### Primary

- OpenCV
- MediaPipe
- Local vision LLM

Purpose:

- Facial detection
- Eye contact
- Body presence
- Multiple person detection
- Sentiment estimation

---

# MEMORY SYSTEM

## Recommended

### Vector Memory

- Qdrant
- Chroma

### Structured Memory

- PostgreSQL
- Supabase

### Episodic Memory

Custom narrative memory layer.

---

# IMAGE GENERATION

## Recommended

### ComfyUI

Mandatory.

This becomes Lira's visual workshop.

Use for:

- Character art
- Cosplay references
- Storyboards
- UI themes
- Concept art
- NSFW/private rendering
- Video generation workflows

---

# VIDEO GENERATION

## Current Recommendations

### Wan
### CogVideoX
### LTX Video

Managed through ComfyUI.

---

# REALTIME COMMUNICATION

## Recommended

### LiveKit

Best current balance.

Alternative:

### Agora

More enterprise-grade.

---

# UI LAYER

## Recommended

### Primary UI

Custom Next.js frontend.

Avoid relying fully on:

- SillyTavern
- Tavern-only interfaces

Use them as testing tools.

Your final experience should feel custom.

## Prototyping + Companion UI

### Recommended

- SillyTavern

Use for:

- personality testing
- roleplay systems
- NSFW interaction
- lorebook testing
- emotional experimentation
- prompt iteration
- immersion testing
- quick model switching

IMPORTANT:

SillyTavern is NOT the long-term orchestrator core.

It should be treated as:

- a frontend shell
- a prototyping environment
- a temporary immersion layer
- a testing interface

Long-term orchestration should migrate into custom systems.

---

# IMMERSION SYSTEMS

## CRITICAL

Lira should have:

- Dynamic ambient audio
- Music awareness
- Presence detection
- Time-of-day awareness
- Mood states
- Emotional carryover
- Scene memory
- Relationship memory
