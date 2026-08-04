# -*- coding: utf-8 -*-
"""RAG 检索抽象层."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Document:
    id: str
    content: str
    metadata: Dict = field(default_factory=dict)
    score: float = 0.0


class BaseRetriever(ABC):
    @abstractmethod
    def add_documents(self, documents: List[Document]) -> None:
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 3) -> List[Document]:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass
