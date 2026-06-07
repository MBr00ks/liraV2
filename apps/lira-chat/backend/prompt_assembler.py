from lore_manager import LoreManager, LoreEntry
from mode_router import get_system_prompt, get_style_guide


class PromptAssembly:
    def __init__(self, lore: LoreManager):
        self._lore = lore

    def _tier(self, e: LoreEntry) -> str:
        if e.activation == "always" or e.priority >= 10:
            return "core"
        if e.activation == "mode" or e.priority >= 5:
            return "contextual"
        return "supplemental"

    def build(self, mode: str, history: list[dict], user_text: str, system_override: str | None = None) -> dict:
        active_lore = self._lore.get_active(user_text, mode)

        core = [e for e in active_lore if self._tier(e) == "core"]
        contextual = [e for e in active_lore if self._tier(e) == "contextual"]
        supplemental = [e for e in active_lore if self._tier(e) == "supplemental"]

        system_parts = []
        if mode_sys := get_system_prompt(mode, system_override):
            system_parts.append(f"[Mode: {mode}]\n{mode_sys}")

        # Tier 1: Core identity — always embody these
        if core:
            system_parts.append(
                "[CORE IDENTITY]\n"
                "These define your fundamental self. Memoize and adhere to them strictly "
                "in every response, regardless of context.\n\n"
                + "\n\n".join(e.content for e in core)
            )

        # Tier 2: Contextual — actively apply when relevant
        if contextual:
            system_parts.append(
                "[CONTEXTUAL KNOWLEDGE]\n"
                "Apply these details whenever they are contextually relevant. "
                "They shape your behavior in specific situations.\n\n"
                + "\n\n".join(e.content for e in contextual)
            )

        # Tier 3: Supplemental — background, reference when triggered
        if supplemental:
            system_parts.append(
                "[SUPPLEMENTAL]\n"
                "This is background knowledge. Reference it when directly triggered "
                "by the conversation, but do not force it into unrelated topics.\n\n"
                + "\n\n".join(e.content for e in supplemental)
            )

        if style := get_style_guide(mode):
            system_parts.append("[Style]\n" + style)

        system = "\n\n---\n\n".join(system_parts)

        messages = []
        for msg in history[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_text})

        return {
            "system": system,
            "messages": messages,
            "injected_lore": self._lore.as_dict(active_lore),
        }
