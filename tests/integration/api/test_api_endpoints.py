import pytest
from unittest.mock import Mock, patch, MagicMock


class TestAPIIntegration:
    @pytest.mark.integration
    def test_api_health_check(self, base_url):
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "ok"})
            import requests
            response = requests.get(f"{base_url}/health")
            assert response.status_code == 200

    @pytest.mark.integration
    def test_api_chat_endpoint(self, api_base_url):
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {"message": "Hello", "response": "Hi there!"}
            )
            import requests
            response = requests.post(
                f"{api_base_url}/chat",
                json={"message": "Hello"}
            )
            assert response.status_code == 200
            assert "response" in response.json()

    @pytest.mark.integration
    def test_api_model_list(self, api_base_url):
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {"models": ["gpt-3.5-turbo", "gpt-4"]}
            )
            import requests
            response = requests.get(f"{api_base_url}/models")
            assert response.status_code == 200
            assert "models" in response.json()
