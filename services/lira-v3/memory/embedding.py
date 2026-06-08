"""Local embedding generation via sentence-transformers."""
from sentence_transformers import SentenceTransformer

_model = None


def _load():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


async def embed(text: str | list[str]) -> list[list[float]]:
    """Generate embeddings for one or more texts. Async-compatible wrapper."""
    model = _load()
    inputs = [text] if isinstance(text, str) else text
    result = model.encode(inputs, normalize_embeddings=True)
    return result.tolist()
