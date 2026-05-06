import re
import hashlib
import json
from datetime import datetime


def sanitize_input(text):
    if not isinstance(text, str):
        return str(text)
    return text.strip()


def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def generate_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def format_response(data, status="success"):
    return {
        "status": status,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }


class Tokenizer:
    def __init__(self):
        self.vocab = {}

    def tokenize(self, text):
        return text.split()

    def encode(self, text):
        tokens = self.tokenize(text)
        return [hashlib.md5(t.encode()).hexdigest()[:8] for t in tokens]

    def decode(self, encoded):
        return " ".join(encoded)
