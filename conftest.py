import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(scope="session")
def base_url():
    return "http://localhost:8000"


@pytest.fixture(scope="session")
def api_base_url():
    return "http://localhost:8000/api/v1"


@pytest.fixture
def mock_ai_response():
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-3.5-turbo",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "This is a mock AI response."
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }


@pytest.fixture
def sample_prompt():
    return "What is the capital of France?"


@pytest.fixture
def sample_user_input():
    return {
        "user_id": "test_user_123",
        "session_id": "test_session_456",
        "message": "Hello, how can you help me?",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def mock_model_config():
    return {
        "model_name": "gpt-3.5-turbo",
        "temperature": 0.7,
        "max_tokens": 1000,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0
    }
