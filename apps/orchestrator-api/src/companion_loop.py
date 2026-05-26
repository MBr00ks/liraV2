import asyncio
from dataclasses import dataclass, field
from typing import Optional

from src.emotion_engine import EmotionEngine, EmotionalState, Realm, ProsodyMode
from src.prompt_composer import compose_full_prompt, compose_full_prompt_with_history, PromptContext
from src.internal_thoughts import generate_internal_thoughts
from src.avatar_signals import emotion_to_avatar_signal, format_avatar_event
from src.sfx_converter import convert_response, format_sfx_event
from src.memory_summarizer import quick_summarize, format_for_storage
from src.logging import get_logger

logger = get_logger("companion-loop")


@dataclass
class CompanionResponse:
    content: str
    realm: str
    emotion: str
    intensity: int
    prosody_mode: str
    model_used: str
    latency_ms: float
    internal_thoughts: list[str] = field(default_factory=list)
    avatar_signal: Optional[dict] = None
    sfx_event: Optional[dict] = None
    spoken_text: Optional[str] = None


class CompanionLoop:
    def __init__(self, emotion_engine: EmotionEngine, model_client, memory_retriever, memory_writer):
        self.emotion = emotion_engine
        self.model_client = model_client
        self.memory_retriever = memory_retriever
        self.memory_writer = memory_writer
        self._active = False

    async def process_message(self, message: str, session_id: Optional[str] = None, mode: Optional[str] = None, history: Optional[list[dict]] = None) -> CompanionResponse:
        import time
        start = time.time()

        self.emotion.record_interaction()

        from src.intent_detector import detect_realm_transition
        current = self.emotion.state.realm
        realm = detect_realm_transition(message, current_realm=current)
        if mode:
            try:
                realm = Realm(mode)
            except ValueError:
                pass
        self.emotion.set_realm(realm)

        detected_emotion, intensity = self.emotion.detect_emotion_from_text(message, realm)
        self.emotion.update_emotion(detected_emotion, intensity)

        prosody = self.emotion.recommend_prosody(realm, detected_emotion)
        self.emotion.set_prosody(prosody)

        memory_context = await self._retrieve_memory(message, realm)

        internal_thoughts = generate_internal_thoughts(
            message=message,
            realm=realm,
            emotion=detected_emotion,
            relationship_level=self.emotion.state.relationship_level,
        )

        context = PromptContext(
            realm=realm,
            emotion=detected_emotion,
            intensity=intensity,
            prosody_mode=prosody,
            memory_context=memory_context,
            relationship_level=self.emotion.state.relationship_level,
            unresolved_topics=self.emotion.state.unresolved_topics,
            internal_thoughts=internal_thoughts,
        )

        messages = compose_full_prompt_with_history(message, context, history) if history else compose_full_prompt(message, context)

        try:
            response = await self.model_client.chat(messages)
            content = response.get("content", "")
            model_used = response.get("model", "unknown")
        except Exception as e:
            logger.error("Model call failed", {"error": str(e)})
            content = "I'm having trouble reaching my thoughts right now. Give me a moment."
            model_used = "fallback"

        latency_ms = (time.time() - start) * 1000

        avatar_event = emotion_to_avatar_signal(detected_emotion, realm, intensity, prosody)
        avatar_signal = format_avatar_event(avatar_event)

        converted = convert_response(content, detected_emotion, realm, prosody)
        sfx_event = format_sfx_event(converted.sfx) if converted.sfx else None

        asyncio.create_task(self._maybe_store_memory(message, content, realm, detected_emotion))
        self._update_relationship(message, content)

        return CompanionResponse(
            content=content,
            realm=realm.value,
            emotion=detected_emotion.value,
            intensity=intensity,
            prosody_mode=prosody.value,
            model_used=model_used,
            latency_ms=latency_ms,
            internal_thoughts=internal_thoughts,
            avatar_signal=avatar_signal,
            sfx_event=sfx_event,
            spoken_text=converted.spoken_text,
        )

    async def process_stream(self, message: str, session_id: Optional[str] = None, mode: Optional[str] = None, history: Optional[list[dict]] = None):
        self.emotion.record_interaction()

        from src.intent_detector import detect_realm_transition
        realm = detect_realm_transition(message)
        if mode:
            try:
                realm = Realm(mode)
            except ValueError:
                pass
        self.emotion.set_realm(realm)

        detected_emotion, intensity = self.emotion.detect_emotion_from_text(message, realm)
        self.emotion.update_emotion(detected_emotion, intensity)

        prosody = self.emotion.recommend_prosody(realm, detected_emotion)
        self.emotion.set_prosody(prosody)

        memory_context = await self._retrieve_memory(message, realm)

        internal_thoughts = generate_internal_thoughts(
            message=message,
            realm=realm,
            emotion=detected_emotion,
            relationship_level=self.emotion.state.relationship_level,
        )

        context = PromptContext(
            realm=realm,
            emotion=detected_emotion,
            intensity=intensity,
            prosody_mode=prosody,
            memory_context=memory_context,
            relationship_level=self.emotion.state.relationship_level,
            unresolved_topics=self.emotion.state.unresolved_topics,
            internal_thoughts=internal_thoughts,
        )

        messages = compose_full_prompt_with_history(message, context, history) if history else compose_full_prompt(message, context)

        avatar_event = emotion_to_avatar_signal(detected_emotion, realm, intensity, prosody)
        yield {"type": "avatar_signal", "payload": format_avatar_event(avatar_event)["payload"]}

        accumulated = ""
        sfx_emitted = set()
        try:
            async for chunk in self.model_client.stream_chat(messages):
                content = chunk.get("content", "")
                done = chunk.get("done", False)

                if content:
                    accumulated += content
                    new_sfx = self._detect_streaming_sfx(accumulated, sfx_emitted, detected_emotion, realm)
                    if new_sfx:
                        sfx_emitted.add(new_sfx["payload"]["sfx"])
                        yield {"type": "sfx_event", "payload": new_sfx["payload"]}
                    cleaned = self._strip_partial_markers(content)
                    if cleaned:
                        yield {"type": "content", "content": cleaned, "done": False}

                if done:
                    final_converted = convert_response(accumulated, detected_emotion, realm, prosody)
                    asyncio.create_task(self._maybe_store_memory(message, accumulated, realm, detected_emotion))
                    self._update_relationship(message, accumulated)
                    yield {"type": "content", "content": "", "done": True, "spoken_text": final_converted.spoken_text}
        except Exception as e:
            logger.error("Stream failed", {"error": str(e)})
            yield {"type": "content", "content": "I lost my train of thought. Can you try again?", "done": True}

    def _detect_streaming_sfx(self, text: str, emitted: set, emotion: EmotionalState, realm: Realm) -> Optional[dict]:
        from src.sfx_converter import detect_sfx_from_text, format_sfx_event
        sfx = detect_sfx_from_text(text, emotion, realm)
        if sfx and sfx.sfx.value not in emitted:
            return format_sfx_event(sfx)
        return None

    def _strip_partial_markers(self, text: str) -> str:
        import re
        if "*" in text or "(" in text:
            text = re.sub(r"\*[^*]*\*", "", text)
            text = re.sub(r"\([^)]*\)", "", text)
            if "*" in text:
                text = re.sub(r"\*[^*]*$", "", text)
            if "(" in text and ")" not in text:
                text = re.sub(r"\([^)]*$", "", text)
        return text.strip()

    async def check_proactive(self) -> Optional[str]:
        if not self.emotion.should_initiate():
            return None
        prompt = self.emotion.get_initiation_prompt()
        logger.info("Proactive check-in initiated", {"prompt": prompt})
        return prompt

    async def _retrieve_memory(self, message: str, realm: Realm) -> str:
        try:
            categories = self._realm_to_categories(realm)
            results = await self.memory_retriever.retrieve({
                "query": message,
                "categories": categories,
                "limit": 5,
                "min_importance": 2,
                "include_embeddings": True,
            })
            if not results:
                return ""
            parts = []
            for r in results:
                parts.append(f"[{r['category']}] {r['title']}: {r['content']}")
            return "\n".join(parts)
        except Exception as e:
            logger.warn("Memory retrieval failed", {"error": str(e)})
            return ""

    def _realm_to_categories(self, realm: Realm) -> list[str]:
        mapping = {
            Realm.ASSISTANT: ["project", "technical", "relationship"],
            Realm.MOONSTACHE: ["lore", "identity"],
            Realm.BETWEEN: ["relationship", "episodic", "identity"],
        }
        return mapping.get(realm, ["episodic", "relationship"])

    async def _maybe_store_memory(self, user_message: str, response: str, realm: Realm, emotion: EmotionalState) -> None:
        summary = quick_summarize(user_message, response, realm, emotion)
        if not summary.should_store:
            return
        try:
            category = self._realm_to_categories(realm)[0]
            memory_data = format_for_storage(summary, category, {
                "realm": realm.value,
                "emotion": emotion.value,
            })
            await self.memory_writer.write(category, memory_data)
            logger.info("Memory stored", {"category": category, "title": summary.title, "importance": summary.importance})
        except Exception as e:
            logger.warn("Memory write failed", {"error": str(e)})

    def _should_store(self, message: str, realm: Realm, emotion: EmotionalState) -> bool:
        if realm == Realm.BETWEEN:
            return True
        if emotion in (EmotionalState.PROTECTIVE, EmotionalState.FRUSTRATED, EmotionalState.FLIRTATIOUS):
            return True
        if len(message) > 30:
            return True
        return False

    def _update_relationship(self, user_message: str, response: str) -> None:
        text = user_message.lower()
        if any(w in text for w in ["thank", "thanks", "appreciate", "love", "great"]):
            self.emotion.adjust_relationship(1)
        elif any(w in text for w in ["stop", "wrong", "no", "bad", "annoying"]):
            self.emotion.adjust_relationship(-1)
