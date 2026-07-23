# -*- coding: utf-8 -*-
"""Agent 专家库知识加载：将 agents/ 目录下的 markdown 提示词加载为可检索知识."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from .base import Document
from .knowledge_store import TfidfKnowledgeStore


class AgentKnowledgeStore:
    """管理 agents/ 目录下的专家提示词知识库."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir or Path(__file__).parents[3]) / "agents"
        self.retriever = TfidfKnowledgeStore()
        self._loaded = False

    def load(self) -> int:
        """加载所有 markdown 提示词到检索库，返回加载文档数."""
        documents = []
        index_file = self.base_dir / "index.json"
        index = self._load_index(index_file)

        for md_path in sorted(self.base_dir.rglob("*.md")):
            relative = md_path.relative_to(self.base_dir)
            doc_id = str(relative).replace("\\", "/")
            content = md_path.read_text(encoding="utf-8")
            metadata = {
                "path": doc_id,
                "category": "testing" if "testing" in doc_id else "engineering",
                **index.get(doc_id, {}),
            }
            documents.append(Document(id=doc_id, content=content, metadata=metadata))

        self.retriever.clear()
        self.retriever.add_documents(documents)
        self._loaded = True
        return len(documents)

    def search(self, query: str, top_k: int = 3) -> List[Document]:
        if not self._loaded:
            self.load()
        return self.retriever.search(query, top_k=top_k)

    def _load_index(self, index_file: Path) -> Dict[str, Dict]:
        if not index_file.exists():
            return {}
        try:
            data = json.loads(index_file.read_text(encoding="utf-8"))
            return {item.get("path", ""): item for item in data if item.get("path")}
        except Exception:
            return {}
