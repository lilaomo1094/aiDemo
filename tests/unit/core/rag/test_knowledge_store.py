# -*- coding: utf-8 -*-
import pytest

from automation.core.rag import Document, TfidfKnowledgeStore


class TestTfidfKnowledgeStore:
    def test_add_and_search_documents(self):
        store = TfidfKnowledgeStore()
        docs = [
            Document(id="d1", content="API 测试用例设计方法"),
            Document(id="d2", content="UI 自动化测试最佳实践"),
            Document(id="d3", content="性能测试指标分析"),
        ]
        store.add_documents(docs)
        results = store.search("API 测试", top_k=2)
        assert len(results) > 0
        assert results[0].id == "d1"

    def test_search_empty_store(self):
        store = TfidfKnowledgeStore()
        assert store.search("任意查询") == []

    def test_clear_store(self):
        store = TfidfKnowledgeStore()
        store.add_documents([Document(id="d1", content="测试内容")])
        store.clear()
        assert store.search("测试") == []
