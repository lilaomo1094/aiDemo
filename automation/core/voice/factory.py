# -*- coding: utf-8 -*-
"""ASR Provider 工厂."""

from typing import Any, Dict

from .base import ASRProvider
from .openai_whisper import OpenAIWhisperASR

_REGISTRY: Dict[str, Any] = {
    "openai_whisper": OpenAIWhisperASR,
}


def create_asr_provider(config: Dict[str, Any]) -> ASRProvider:
    """根据配置创建 ASR Provider."""
    provider = config.get("provider", "openai_whisper")
    provider_cls = _REGISTRY.get(provider)
    if provider_cls is None:
        raise ValueError(f"未知的 ASR provider: {provider}")
    return provider_cls(config)


def register_asr_provider(name: str, provider_cls):
    """注册自定义 ASR Provider."""
    _REGISTRY[name] = provider_cls
