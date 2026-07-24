# -*- coding: utf-8 -*-
"""Anthropic Claude Provider."""

import logging
from typing import Dict, List

import requests

from .base import LLMProvider, LLMResponse, with_llm_retry


logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.api_key or ""
        self.base_url = (config.base_url or "https://api.anthropic.com").rstrip("/")
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
        system = ""
        conversation = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                conversation.append({"role": m["role"], "content": m["content"]})

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": conversation,
            "system": system,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
        }
        response = requests.post(
            f"{self.base_url}/v1/messages",
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            raw=data,
        )
