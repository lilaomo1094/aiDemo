# -*- coding: utf-8 -*-
"""LLM Provider 工厂."""

from .anthropic_provider import AnthropicProvider
from .base import LLMProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider


class CustomProvider(LLMProvider):
    """占位：用户可通过 extra 注册自定义 Provider."""

    def chat(self, messages, **kwargs):
        raise NotImplementedError("自定义 Provider 需要实现 chat 方法")


_PROVIDER_MAP = {
    "openai": OpenAIProvider,
    "azure_openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "custom": CustomProvider,
}


def create_llm_provider(config) -> LLMProvider:
    provider_cls = _PROVIDER_MAP.get(config.provider)
    if provider_cls is None:
        raise ValueError(f"未知的 LLM provider: {config.provider}")
    return provider_cls(config)


def register_provider(name: str, provider_cls):
    _PROVIDER_MAP[name] = provider_cls
