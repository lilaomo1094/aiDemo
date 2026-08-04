# -*- coding: utf-8 -*-
"""Ollama 本地模型 Provider."""

import logging
from typing import Dict, List

import requests

from .base import LLMProvider, LLMResponse, with_llm_retry


logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    def __init__(self, config):
        super().__init__(config)
        self.base_url = (config.base_url or "http://localhost:11434").rstrip("/")
        self.model = config.model
        self.temperature = config.temperature
        self.timeout = config.timeout

    @with_llm_retry(max_retries=3, backoff_seconds=1.0)
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        try:
            return self._chat(messages, **kwargs)
        except (requests.RequestException, requests.HTTPError) as e:
            return self._try_fallback_model(messages, kwargs, e)

    def _chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
            },
        }
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            model=kwargs.get("model", self.model),
            raw=data,
        )
