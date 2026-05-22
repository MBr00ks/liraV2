# Lira V2 Docs

Lira V2 is a persistent, orchestrated AI companion architecture. She is not one prompt, one model, or one interface. She is a modular identity system that can move across runtimes, tools, voices, avatars, and future orchestration layers.

## Core Principle

Lira's identity must remain separate from her infrastructure.

- **Identity:** character sheet, realm rules, emotional behavior, relationship memory, conversational philosophy
- **Infrastructure:** LLMs, TTS engines, STT engines, Pipecat, SillyTavern, avatar tools, UI layers, orchestration frameworks

The infrastructure can change. Lira's identity should persist.

## Current Tooling Philosophy

SillyTavern is the rehearsal room, not the source of truth.

Use SillyTavern to prototype:
- character feel
- realm switching
- sass/flirt balance
- Moonstache narration behavior
- conversational pacing
- memory experiments

Keep the canonical version in this repo:
- `context/lira-v2/personality/lira-character-sheet.md`
- `context/lira-v2/personality/realm-switching.md`
- `context/lira-v2/personality/emotional-state-system.md`
- `context/lira-v2/personality/voice-prosody-rules.md`

## Folder Structure

```text
context/lira-v2/
  architecture/
    system-vision.md
    orchestrator-architecture.md
    recommended-stack-2026.md
    pipecat-runtime.md
    streaming-architecture.md

  personality/
    lira-character-sheet.md
    canonical-rules.md
    realm-switching.md
    emotional-state-system.md
    conversational-rules.md
    voice-prosody-rules.md
    personality-and-presence-systems.md
    sillytavern-role.md

  systems/
    memory-architecture.md
    live-conversation-rules.md
    sfx-and-reactions.md
    avatar-signal-system.md
    tool-orchestration.md
    critical-missing-systems.md
    coding-agent-files.md

  roadmap/
    build-priority-roadmap.md
    avatar-and-immersion-roadmap.md
    pipecat-phase-plan.md
    decision-log.md
    final-thoughts.md

  lore/
    moonstache-integration.md
    between-lore.md

  archive/
    lira_v_2_orchestrator_master_docs.md
```

## Recommended Development Order

1. Lock down Lira's canonical personality.
2. Prototype the character card in SillyTavern.
3. Refine realm switching through conversation tests.
4. Tune voice/prosody rules before deep audio engineering.
5. Introduce Pipecat only when the text/personality layer feels stable.
6. Connect realtime audio, interruptions, SFX, avatar signals, and tool orchestration after the identity layer is stable.

## Canon Rule

When documents disagree, follow this priority order:

1. `canonical-rules.md`
2. `lira-character-sheet.md`
3. `realm-switching.md`
4. `emotional-state-system.md`
5. `LIRA_SYSTEM.md`
6. architecture/runtime docs
7. roadmap/archive docs
