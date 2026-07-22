# -*- coding: utf-8 -*-
"""Agent 抽象基类."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict

from automation.core.config import LLMConfig
from automation.core.llm import create_llm_provider


class BaseAgent(ABC):
    def __init__(self, config):
        self.config = config
        self.llm = None
        if hasattr(config, "llm") and config.llm and config.llm.api_key:
            self.llm = create_llm_provider(config.llm)

    @abstractmethod
    def execute(self, task, context) -> Dict[str, Any]:
        pass

    def _call_llm_json(self, prompt: str, system: str = None, fallback: Any = None) -> Any:
        if not self.llm:
            return fallback
        try:
            resp = self.llm.complete(prompt, system=system)
            text = self.llm.extract_json(resp.content)
            return json.loads(text)
        except Exception:
            return fallback

    def _call_llm_text(self, prompt: str, system: str = None, fallback: str = "") -> str:
        if not self.llm:
            return fallback
        try:
            return self.llm.complete(prompt, system=system).content
        except Exception:
            return fallback
