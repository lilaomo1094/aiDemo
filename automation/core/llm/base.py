# -*- coding: utf-8 -*-
"""LLM Provider 抽象基类."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class LLMResponse:
    content: str
    model: str = ""
    usage: Dict[str, int] = None
    raw: Any = None

    def __post_init__(self):
        if self.usage is None:
            self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


class LLMProvider(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """传入消息列表，返回 LLMResponse."""
        pass

    def complete(self, prompt: str, system: Optional[str] = None, **kwargs) -> LLMResponse:
        """单轮 completion 快捷方法."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, **kwargs)

    def extract_json(self, text: str) -> str:
        """从 LLM 输出中提取 JSON 字符串（支持 markdown 代码块）."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text
