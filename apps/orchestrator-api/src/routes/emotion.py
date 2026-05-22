import uuid
from fastapi import APIRouter, HTTPException

from src.models import EmotionStateResponse, EmotionUpdateRequest
from src.emotion_engine import EmotionEngine, EmotionalState, Realm, ProsodyMode
from src.logging import get_logger, log_request

logger = get_logger("emotion-route")

router = APIRouter()

_emotion_engine = None


def get_emotion_engine() -> EmotionEngine:
    global _emotion_engine
    if _emotion_engine is None:
        _emotion_engine = EmotionEngine()
    return _emotion_engine


@router.get("/state", response_model=EmotionStateResponse)
async def get_emotion_state():
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="emotion/state", method="GET")

    engine = get_emotion_engine()
    state = engine.get_state_dict()

    return EmotionStateResponse(
        realm=state.get("realm", Realm.ASSISTANT.value),
        emotion=state.get("emotion", EmotionalState.FOCUSED.value),
        intensity=state.get("intensity", 0),
        prosody_mode=state.get("prosody_mode", ProsodyMode.WARM_COLLABORATIVE.value),
        relationship_level=state.get("relationship_level", 0),
        last_interaction=state.get("last_interaction", ""),
        unresolved_topics=state.get("unresolved_topics", []),
    )


@router.post("/update", response_model=EmotionStateResponse)
async def update_emotion(request: EmotionUpdateRequest):
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="emotion/update", method="POST")

    engine = get_emotion_engine()

    if request.realm:
        try:
            realm = Realm(request.realm)
            engine.set_realm(realm)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid realm: {request.realm}")

    if request.emotion:
        try:
            emotion = EmotionalState(request.emotion)
            engine.update_emotion(emotion, request.intensity or 0)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid emotion: {request.emotion}")

    if request.prosody_mode:
        try:
            prosody = ProsodyMode(request.prosody_mode)
            engine.set_prosody(prosody)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid prosody mode: {request.prosody_mode}")

    if request.relationship_delta != 0:
        engine.adjust_relationship(request.relationship_delta)

    state = engine.get_state_dict()

    return EmotionStateResponse(
        realm=state.get("realm", Realm.ASSISTANT.value),
        emotion=state.get("emotion", EmotionalState.FOCUSED.value),
        intensity=state.get("intensity", 0),
        prosody_mode=state.get("prosody_mode", ProsodyMode.WARM_COLLABORATIVE.value),
        relationship_level=state.get("relationship_level", 0),
        last_interaction=state.get("last_interaction", ""),
        unresolved_topics=state.get("unresolved_topics", []),
    )


@router.post("/silence")
async def record_silence(minutes: float):
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="emotion/silence", method="POST")

    engine = get_emotion_engine()
    engine.update_silence(minutes)

    return {"silence_duration_minutes": minutes, "state": engine.get_state_dict()}


@router.post("/unresolved/add")
async def add_unresolved_topic(topic: str):
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="emotion/unresolved/add", method="POST")

    engine = get_emotion_engine()
    engine.add_unresolved_topic(topic)

    return {"unresolved_topics": engine.state.unresolved_topics}


@router.post("/unresolved/resolve")
async def resolve_topic(topic: str):
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="emotion/unresolved/resolve", method="POST")

    engine = get_emotion_engine()
    engine.resolve_topic(topic)

    return {"unresolved_topics": engine.state.unresolved_topics}


@router.get("/proactive")
async def check_proactive():
    request_id = str(uuid.uuid4())
    log_request(logger, request_id, endpoint="emotion/proactive", method="GET")

    engine = get_emotion_engine()

    if engine.should_initiate():
        prompt = engine.get_initiation_prompt()
        return {"should_initiate": True, "prompt": prompt}

    return {"should_initiate": False, "prompt": None}
