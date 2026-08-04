import pytest


class AIService:
    def __init__(self, model):
        self.model = model

    def chat(self, user_message):
        return self.model.generate(user_message)

    def stream_chat(self, user_message):
        response = self.model.generate(user_message)
        for char in response:
            yield char


class TestAIService:
    def test_chat_returns_response(self, mock_ai_response):
        from unittest.mock import Mock
        mock_model = Mock()
        mock_model.generate.return_value = "Test response"

        service = AIService(mock_model)
        result = service.chat("Hello")

        assert result == "Test response"
        mock_model.generate.assert_called_once_with("Hello")

    def test_stream_chat_yields_chars(self):
        from unittest.mock import Mock
        mock_model = Mock()
        mock_model.generate.return_value = "ABC"

        service = AIService(mock_model)
        result = list(service.stream_chat("Hello"))

        assert result == ["A", "B", "C"]
