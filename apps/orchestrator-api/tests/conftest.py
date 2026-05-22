import pytest


@pytest.fixture
def mock_httpx_client():
    """Mock HTTPX client for testing external service calls."""
    from unittest.mock import AsyncMock
    return AsyncMock()


@pytest.fixture
def mock_settings():
    """Mock settings for testing without real env vars."""
    from unittest.mock import patch
    with patch.dict("os.environ", {
        "LLM_PROVIDER": "ollama",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "qwen3:32b",
    }):
        yield
