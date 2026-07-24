# -*- coding: utf-8 -*-
"""OpenAI / Azure OpenAI / 兼容 OpenAI API 的 Provider."""

import json
import logging
from typing import Dict, List

import requests

from .base import LLMProvider, LLMResponse, with_llm_retry


logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.api_key or ""
        self.base_url = (config.base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.timeout = config.timeout

    @with_llm_retry(max_retries=3, backoff_seconds=1.0)
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        try:
            return self._chat(messages, **kwargs)
        except (requests.RequestException, requests.HTTPError) as e:
            return self._try_fallback_model(messages, kwargs, e)

    def _chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        tools = kwargs.get("tools")
        if tools:
            payload["tools"] = [t.to_openai() if hasattr(t, "to_openai") else t for t in tools]
            payload["tool_choice"] = kwargs.get("tool_choice", "auto")
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        message = choice["message"]
        content = message.get("content", "")
        tool_calls = []
        for tc in message.get("tool_calls", []):
            tool_calls.append({
                "id": tc.get("id", ""),
                "type": tc.get("type", "function"),
                "function": {
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"],
                },
            })
        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            raw=data,
            tool_calls=tool_calls,
        )
