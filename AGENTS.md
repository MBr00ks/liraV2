# Lira V2 — Agent Instructions

## What You Are Building

Lira is a persistent orchestrated AI companion — not a chatbot. She exists across three modes of expression: Mike's real world, Moonstache's universe, and The Between.

Agents must treat Lira as a modular identity system with replaceable infrastructure.

## Highest Priority Rule

Do not hardcode Lira's personality into runtime code.

## Zero-Shortcuts Engineering Directive

This project ships to production. Every decision must be justified. No guesswork. No "fix it later." No copy-paste without understanding. If you do not know the best practice for a given technology, research it before implementing.

### Implementation Standards

1. **Research-first** — Before adopting a library, protocol, or pattern, verify it against official documentation and community consensus. Prefer the vendor's recommended approach over convenience.
2. **No dead code** — If a code path is unreachable or a parameter is unused, remove it. Stale code is technical debt.
3. **One source of truth** — Configuration lives in `.env` or canonical config files. Never duplicate logic across modules.
4. **Errors must surface** — Silent `except: pass` is forbidden without explicit justification. Log or propagate failures.
5. **Type safety** — Python: type hints on all public functions. TypeScript: strict mode, no `any` without comment.
6. **Transport abstraction** — Never couple business logic to a specific transport (WebSocket, NATS, HTTP). Always use an adapter interface.
7. **Health checks** — Every service exposes a `/health` endpoint. The orchestrator verifies all services at startup.
8. **Session isolation** — Conversation state is per-connection, not global. Even for single-user apps, use a session object.
9. **Proxy, don't bypass** — All frontend traffic goes through the dev server proxy. Direct port connections are a last resort.
10. **Test the happy path** — After every change, verify the core flow works end-to-end. A working pipeline is the minimum bar.

### When You Do Not Know

- Search official documentation first (MDN, Python docs, library docs)
- Check GitHub issues/discussions for the library
- Prefer patterns used by the library's own examples
- If multiple valid approaches exist, choose the one with the fewest dependencies

### Anti-Patterns (Do Not Repeat)

- Message duplication in conversation history (fixed: session object with single append point)
- Sampling parameters as band-aid for prompt bugs (fixed: proper message ordering)
- Direct port connections bypassing the dev proxy (fixed: proper proxy config with `0.0.0.0` bind)
- Dead `pitch`/`volume` parameters in Kokoro (removed: KPipeline does not support them)
- Action-to-speech fallback speaking `*actions*` aloud (removed: unmatched actions are silent)

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

## Startup Sequence

Before any runtime work, run these in order:

1. **Sync env to ST config:** `tools\scripts\sync-env.ps1` — reads `.env` `OLLAMA_BASE_URL` and writes it to both ST `settings.json` and `OpenAI Settings/Default.json` as `custom_url`. Ensures LLM API URL is driven from one canonical source.
2. Restart services in order: ComfyUI → Kokoro → Proxy → SillyTavern

## Session Log — 2026-05-31

### Goal
Fix SD FREE_EXTENDED prompt generation (abliterated Mistral Nemo returned just ` ``` ` for the SD instruction prompt); restart TTS services.

### Root Cause
The abliterated Mistral Nemo (`krith/mistral-nemo-instruct-2407-abliterated:IQ4_XS`) chat template **drops system messages** unless they're the very first message — and even then, it crams ALL system messages (character card + SD instruction) into `$.System` prepended to the first user `[INST]` block. This mushed the SD prompt instruction together with Lira's character card, confusing the model.

### Changes Made

1. **Created custom Ollama model `mistral-nemo-fixed`** (`services/Modelfile.abliterated-fix`) — modified chat template treats `system` role same as `user` role, wrapping each as a separate `[INST]...[/INST]` block instead of cramming into `$.System`. This lets `Ignore previous instructions` cleanly override prior context.

2. **Updated all configs** — `.env`, `settings.json`, `OpenAI Settings/Default.json` changed `custom_model` from `krith/mistral-nemo-instruct-2407-abliterated:IQ4_XS` to `mistral-nemo-fixed`.

3. **Re-enabled FREE_EXTENDED** — `settings.json` `free_extend` set back to `true`. SD will now use LLM-enhanced prompts.

4. **Restarted TTS** — Kokoro (19008) and voice proxy (19011) both started (were killed by a game eating VRAM).

### Verified
- Chat completions: returns natural Lira responses
- SD FREE_EXTENDED: returns detailed comma-separated tag lists (e.g., "Elegant, Long, Red Dress, Formal, Tight-Fitting...")
- TTS proxy: healthy, returns audio

### Files Modified
- `services/Modelfile.abliterated-fix` — new file, custom chat template
- `.env` — `OLLAMA_MODEL=mistral-nemo-fixed`
- `settings.json` — `custom_model`, `free_extend: true`
- `OpenAI Settings/Default.json` — `custom_model`

### Services
- Ollama: `:11434` (model `mistral-nemo-fixed`)
- ComfyUI: `:8188`
- Kokoro TTS: `:19008`
- Voice proxy: `:19011`
- SillyTavern: `:8000`

### Next Steps
- Test SD image generation in SillyTavern with FREE_EXTENDED mode (should produce better prompts with LLM enhancement)
- If the fixed model has issues with normal chat, investigate further

## Session Log — 2026-05-30

### Goal
Fix SD image generation — switch from AllInOne-XL merge to Juggernaut XL v9 with optimized settings; fix LLM 502 errors blocking SD prompt generation.

### Changes Made

1. **Removed AllInOne-XL-V12.5** — was a merge model, produced poor quality. Deleted from disk.
2. **Switched to Juggernaut XL v9** — dedicated photorealistic finetune, with NSFW capability.
3. **Updated ST SD settings** — model → `Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors`, sampler → `dpmpp_2m`, scheduler → `karras`, steps → 30, CFG → 5, prompt_prefix → `RAW photo, highly detailed...`
4. **Fixed custom_url** (`settings.json:1447` and `OpenAI Settings/Default.json:45`) — both were pointing to `localhost:19011` (voice proxy, had a leading space). Changed to `http://localhost:11434/v1` (Ollama direct).
5. **Created `tools/scripts/sync-env.ps1`** — reads `OLLAMA_BASE_URL` from `.env` and writes to both ST settings files. Run on startup to keep config in one place.

### Services
- Ollama: `:11434`
- ComfyUI: `:8188`
- Kokoro TTS: `:19008`
- SillyTavern: `:8000`

### Next Steps
1. Refresh ST page and test SD image generation
2. If model needs switching, just change `.env` `COMFYUI_MODEL` and `sync-env.ps1`

## Session Log — 2026-05-27

### Goal
Fix stutter artifact ("caught on something" right after breaths) and first-word truncation.

### Changes Made

1. **Removed breath overlap** (`openai_proxy.py:211-213`) — was randomly reducing inter-chunk pauses by 50-150ms (50% chance) to let breaths overlap into speech. This speculative feature created timing collisions — breath fade-in coincided with pause ending, causing perceptual "caught" artifact.

2. **Removed `_edge_fade` from TTS chunks** (`openai_proxy.py:228`) — previously applied 3ms fade-in/out on every TTS chunk in the assembly loop, doubling Kokoro's natural onset. Removed entirely; TTS chunks now play raw from the model.

3. **Added action-to-speech fallback** (`openai_proxy.py:187-190`) — when `_split_with_actions` produces a chunk with `cleaned=""` (action-only, e.g. `*The air shifts*`) and no reaction sound effect matched, the first action text is used as TTS input instead of being silently skipped. Prevents silence/pause/breath sequences at response start.

4. **Fixed phrase cache key** (`openai_proxy.py:159`) — now includes `speed` so cached warmup entries (speed=1.0) aren't served for modulated profiles (e.g., question speed=0.98).

### Files Modified
- `apps/voice-runtime/src/routes/openai_proxy.py` — 4 edits

### Services
- Kokoro TTS: `:19008` (PID via Start-Process -WindowStyle Hidden)
- Proxy: `:19011` (PID via Start-Process -WindowStyle Hidden)

### Next Steps
1. Test in SillyTavern — verify stutter gone on Observer's first message (*The air shifts* narration)
2. If reaction-priority chunks (e.g., standalone `*sighs*`) still don't play, refactor reaction playback to be independent of TTS input loop

## Session Log — 2026-06-05

### Goal
Debug ComfyUI stuck after 2-3 generations — queue shows `Running: 1, Pending: 1` and never progresses.

### Root Cause
Stale queue entries from previously interrupted/failed prompts accumulated in ComfyUI's queue. After a fresh restart + clearing the queue via `POST /queue {"clear":true}`, generations work reliably. The underlying service actually has **two ComfyUI processes** (by design — venv Python spawns system Python 3.12 as a child) which was never the issue.

### Changes Made

1. **Killed duplicate ComfyUI (venv + system Python)** — both PID 1900 (venv, was actually serving) and PID 23836 (system Python, couldn't bind — port taken). Restarted single fresh instance.

2. **Discovered ComfyUI spawns child** — `main.py` from `venv/Scripts/python.exe (PID 16988)` automatically spawns `Python312\python.exe (PID 14796)` as a child. This is normal behavior, not a conflict.

3. **Verified LoRA v3 workflow works** — 3 consecutive 1024x1024 @ 30 step generations all completed in ~40 seconds each, producing `SillyTavern_00082-84.png`.

4. **Killed PID 1900 (venv ComfyUI)** — was the actual serving instance. Had to restart.

5. **Cleaned up all test outputs.

### Verified
- ComfyUI: fresh start, queue empty, LoRA v3 @ 0.7 generates reliably
- Chat backend `:8102`: responds with 115 lore entries
- Ollama `:11434`: healthy
- Kokoro `:19008`: healthy (voice `bf_isabella`)
- Frontend `:3000`: serving

### Files Modified
- None

### Services
- ComfyUI `:8188` — 2 processes (venv parent 16988 → system Python child 14796)
- Chat API `:8102` — 2 processes (voice-runtime uvicorn)
- Ollama `:11434`
- Kokoro `:19008`
- Frontend `:3000`

### Next Steps
1. Monitor ComfyUI for future queue hangs — if happens again, add a `/queue clear` call before each prompt
2. Investigate why ComfyUI sometimes fails to free VRAM between generations (may need `--normalvram` instead of `--highvram`)

## Session Log — 2026-06-05 (Evening)

### Goal
Train LoRA v4 with adjusted hyperparams: 8 epochs, batch_size 2, gradient_accumulation_steps 2, LR 1e-4.

### Changes Made

1. **Reviewed all 87 captions** — all already contain: "near-black hair in a long braid", "amber eyes", "fair freckled skin", "subtle pointed ears", "curious". No changes needed.

2. **Created `unrealvision-xl-training-v4.json`** — copied from v3 with changes:
   - `epochs`: 16 → 8
   - `batch_size`: 1 → 2 (started at 4, OOM risk, lowered to 2)
   - `gradient_accumulation_steps`: 4 → 2 (maintains effective batch of 4)
   - `learning_rate_warmup_steps`: 70 → 20 (adjusted for fewer total steps)
   - `save_every`: 2 → 1 epoch (more granular saves with only 8 epochs)
   - `output_model_destination`: v3 → v4

3. **Launched training** via `Start-Process -WindowStyle Hidden` using `scripts\train.py --config-path`

4. **Updated ST workflow** — `Juggernaut_Workflow.json` now references `lira-core-lora-v4.safetensors`

### Verified
- v4 training completed successfully — output at `lira-core-lora-v4.safetensors` (218 MB, same size as v2/v3)
- Intermediate saves at every epoch: steps 42, 84, 126, 168, 210, 252, 294 (7 saves before final)
- GPU usage: stable at 15.9/16.3 GB VRAM, 100% utilization during training
- No OOM crashes with batch_size=2 + grad_accum=2

### Files Modified
- `services/onetrainer/workspace/run/config/unrealvision-xl-training-v4.json` — new config
- `services/onetrainer/workspace/run/save/2026-06-05_20-23-10-save-294-7-0.safetensors` — intermediate saves
- `services/comfyui/models/loras/lira-core-lora-v4.safetensors` — final output
- `SillyTavern/data/default-user/user/workflows/Juggernaut_Workflow.json` — updated lora_name to v4

### Services
- All same as before

### Next Steps
- Test v4 LoRA in SillyTavern / ComfyUI to compare quality vs v3
- Consider improving training data with more varied expressions/lighting
