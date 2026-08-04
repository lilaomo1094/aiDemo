import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio


class AIPipeline:
    def __init__(self, model, preprocessor, postprocessor):
        self.model = model
        self.preprocessor = preprocessor
        self.postprocessor = postprocessor

    def process(self, user_input):
        processed = self.preprocessor.process(user_input)
        raw_response = self.model.generate(processed)
        final_response = self.postprocessor.process(raw_response)
        return final_response


class Preprocessor:
    def process(self, text):
        return text.strip().lower()


class Postprocessor:
    def process(self, text):
        return {"response": text, "tokens": len(text.split())}


@pytest.mark.integration
class TestAIPipeline:
    def test_full_pipeline_execution(self):
        mock_model = Mock()
        mock_model.generate.return_value = "This is a response"

        pipeline = AIPipeline(
            model=mock_model,
            preprocessor=Preprocessor(),
            postprocessor=Postprocessor()
        )

        result = pipeline.process("  Hello World  ")
        assert "response" in result
        assert "tokens" in result
        mock_model.generate.assert_called_once()

    def test_pipeline_with_empty_input(self):
        mock_model = Mock()
        mock_model.generate.return_value = "Response"

        pipeline = AIPipeline(
            model=mock_model,
            preprocessor=Preprocessor(),
            postprocessor=Postprocessor()
        )

        result = pipeline.process("   ")
        assert result["response"] == "Response"


@pytest.mark.integration
class TestPreprocessor:
    def test_preprocessor_trims_and_lowers(self):
        preprocessor = Preprocessor()
        result = preprocessor.process("  HELLO WORLD  ")
        assert result == "hello world"


@pytest.mark.integration
class TestPostprocessor:
    def test_postprocessor_formats_response(self):
        postprocessor = Postprocessor()
        result = postprocessor.process("hello world test")
        assert result["response"] == "hello world test"
        assert result["tokens"] == 3
