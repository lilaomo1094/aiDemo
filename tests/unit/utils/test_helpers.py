import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "unit" / "utils"))
from helpers import sanitize_input, validate_email, generate_hash, format_response, Tokenizer


class TestSanitizeInput:
    def test_sanitize_string(self):
        result = sanitize_input("  hello  ")
        assert result == "hello"

    def test_sanitize_non_string(self):
        result = sanitize_input(123)
        assert result == "123"


class TestValidateEmail:
    def test_valid_email(self):
        assert validate_email("test@example.com") is True

    def test_invalid_email(self):
        assert validate_email("invalid-email") is False


class TestGenerateHash:
    def test_generate_hash_consistency(self):
        hash1 = generate_hash("test")
        hash2 = generate_hash("test")
        assert hash1 == hash2

    def test_generate_hash_uniqueness(self):
        hash1 = generate_hash("test1")
        hash2 = generate_hash("test2")
        assert hash1 != hash2


class TestFormatResponse:
    def test_format_response_default(self):
        result = format_response({"key": "value"})
        assert result["status"] == "success"
        assert result["data"]["key"] == "value"
        assert "timestamp" in result

    def test_format_response_custom_status(self):
        result = format_response({}, status="error")
        assert result["status"] == "error"


class TestTokenizer:
    def test_tokenize(self):
        tokenizer = Tokenizer()
        result = tokenizer.tokenize("hello world")
        assert result == ["hello", "world"]

    def test_encode_decode(self):
        tokenizer = Tokenizer()
        original = "hello world"
        encoded = tokenizer.encode(original)
        assert len(encoded) == 2
        assert all(isinstance(e, str) for e in encoded)
