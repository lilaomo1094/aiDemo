import pytest
from unittest.mock import Mock, patch


class MockAIModel:
    def __init__(self, model_name="gpt-3.5-turbo"):
        self.model_name = model_name
        self.temperature = 0.7
        self.max_tokens = 1000

    def generate(self, prompt):
        return f"Response to: {prompt}"

    def batch_generate(self, prompts):
        return [self.generate(p) for p in prompts]


class TestAIModel:
    def test_model_initialization(self):
        model = MockAIModel()
        assert model.model_name == "gpt-3.5-turbo"
        assert model.temperature == 0.7

    def test_generate_response(self, sample_prompt):
        model = MockAIModel()
        response = model.generate(sample_prompt)
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

    def test_batch_generate(self):
        model = MockAIModel()
        prompts = ["Hello", "Hi", "Greetings"]
        responses = model.batch_generate(prompts)
        assert len(responses) == 3
        assert all(isinstance(r, str) for r in responses)
