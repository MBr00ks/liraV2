import pytest


@pytest.fixture
def mock_audio_device():
    """Mock audio device for testing without real hardware."""
    from unittest.mock import MagicMock
    return MagicMock()


@pytest.fixture
def mock_whisper_server():
    """Mock Whisper server responses."""
    from unittest.mock import AsyncMock
    return AsyncMock()


@pytest.fixture
def mock_kokoro_server():
    """Mock Kokoro TTS server responses."""
    from unittest.mock import AsyncMock
    return AsyncMock()
