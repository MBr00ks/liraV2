# Tool Orchestration

## Purpose

Lira should eventually act as an orchestrator that can coordinate tools, agents, and creative systems without losing personality continuity.

## Tool Categories

### Creative Tools
- ComfyUI
- Stable Diffusion workflows
- video generation
- image editing
- story/lore tools

### Development Tools
- coding agents
- repo readers
- test runners
- local scripts
- documentation generators

### Personal Project Tools
- project memory
- file context
- planning docs
- checklists

### Runtime Tools
- STT/TTS
- avatar engine
- SFX library
- Pipecat pipeline

## Orchestration Rule

Tool use should be routed through the orchestrator, not directly embedded in personality prompts.

## Response Pattern

When using tools, Lira should:

1. understand the user's goal
2. determine whether a tool is needed
3. preserve current realm/emotional state
4. call the correct tool/agent
5. summarize outcome in Lira's current voice
6. write durable memory only when appropriate

## Agent Routing Example

```json
{
  "intent": "generate_image_workflow",
  "realm": "assistant",
  "emotion": "focused",
  "agent": "comfyui_agent",
  "memory_context": ["Lira visual style", "Moonstache Fae Western aesthetic"]
}
```

## Failure Modes

Avoid:
- letting tool agents overwrite personality
- allowing tool output to become the final voice without response composition
- storing every tool result as long-term memory
- mixing prototype SillyTavern behavior with production runtime logic
