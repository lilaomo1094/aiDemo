# -*- coding: utf-8 -*-
"""Agent 抽象基类."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict

from automation.core.config import LLMConfig
from automation.core.llm import create_llm_provider
from automation.core.rag import BaseRetriever


class BaseAgent(ABC):
    def __init__(self, config, knowledge_store: BaseRetriever = None):
        self.config = config
        self.llm = None
        self.knowledge_store = knowledge_store
        if hasattr(config, "llm") and config.llm and config.llm.api_key:
            self.llm = create_llm_provider(config.llm)

    @abstractmethod
    def execute(self, task, context) -> Dict[str, Any]:
        pass

    def _retrieve_knowledge(self, query: str, top_k: int = 2) -> str:
        """从 RAG 知识库检索相关内容，为空则返回空字符串."""
        if not self.knowledge_store:
            return ""
        docs = self.knowledge_store.search(query, top_k=top_k)
        if not docs:
            return ""
        parts = [f"【参考知识 {i+1}】{d.content[:800]}" for i, d in enumerate(docs)]
        return "\n\n".join(parts)

    def _build_system_prompt(self, base_prompt: str, query: str = "") -> str:
        """将 RAG 检索到的知识与基础 system prompt 合并."""
        knowledge = self._retrieve_knowledge(query) if query else ""
        if knowledge:
            return f"{base_prompt}\n\n可参考以下领域知识：\n{knowledge}"
        return base_prompt

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
