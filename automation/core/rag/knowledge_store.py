# -*- coding: utf-8 -*-
"""基于 TF-IDF 的轻量知识库检索，无需外部向量数据库依赖."""

import math
import re
from collections import Counter
from typing import Dict, List, Set

from .base import BaseRetriever, Document


class TfidfKnowledgeStore(BaseRetriever):
    """使用 TF-IDF 进行文档检索的轻量知识库.

    适合中小规模文档（< 1万篇），无需安装额外依赖。
    如需大规模向量化检索，可替换为 VectorKnowledgeStore。
    """

    def __init__(self):
        self.documents: List[Document] = []
        self.term_index: Dict[str, List[int]] = {}
        self.idf: Dict[str, float] = {}

    def clear(self) -> None:
        self.documents = []
        self.term_index = {}
        self.idf = {}

    def add_documents(self, documents: List[Document]) -> None:
        start_idx = len(self.documents)
        for doc in documents:
            idx = start_idx + len(self.documents)
            self.documents.append(doc)
            terms = self._tokenize(doc.content)
            for term in set(terms):
                self.term_index.setdefault(term, []).append(idx)
        self._recompute_idf()

    def search(self, query: str, top_k: int = 3) -> List[Document]:
        if not self.documents:
            return []
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        scores = Counter()
        query_tf = Counter(query_terms)
        for term, qtf in query_tf.items():
            if term not in self.term_index:
                continue
            idf = self.idf.get(term, 0.0)
            for doc_idx in self.term_index[term]:
                doc_terms = self._tokenize(self.documents[doc_idx].content)
                dtf = doc_terms.count(term)
                scores[doc_idx] += qtf * idf * dtf * idf

        top_indices = scores.most_common(top_k)
        results = []
        for idx, score in top_indices:
            doc = self.documents[idx]
            results.append(Document(
                id=doc.id,
                content=doc.content,
                metadata=doc.metadata,
                score=round(score, 4),
            ))
        return results

    def _tokenize(self, text: str) -> List[str]:
        """简单分词：中文字符 + 英文单词."""
        text = text.lower()
        # 中文按字切分
        chinese = re.findall(r"[\u4e00-\u9fff]", text)
        # 英文按单词切分
        english = re.findall(r"[a-z0-9_]+", text)
        return chinese + english

    def _recompute_idf(self) -> None:
        N = len(self.documents)
        if N == 0:
            return
        self.idf = {}
        for term, doc_ids in self.term_index.items():
            df = len(set(doc_ids))
            self.idf[term] = math.log((N + 1) / (df + 1)) + 1.0
