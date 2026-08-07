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

    def test_add_documents_in_multiple_batches_indexes_correctly(self):
        """回归测试：多次调用 add_documents 时索引不能重复累加 start_idx.

        之前的实现 ``idx = start_idx + len(self.documents)`` 在 store 非空时
        会让所有新文档的索引整体偏移 start_idx，导致 search() 取到错误文档或
        抛 IndexError。本测试构造第二批文档并查询只出现在第二批中的词项。
        """
        store = TfidfKnowledgeStore()
        store.add_documents([
            Document(id="d1", content="API 测试用例设计方法"),
            Document(id="d2", content="UI 自动化测试最佳实践"),
        ])
        # 第二批：包含独有词项 "kubernetes"，仅出现在 d4
        store.add_documents([
            Document(id="d3", content="性能测试指标分析"),
            Document(id="d4", content="kubernetes 集群压测"),
        ])
        results = store.search("kubernetes", top_k=1)
        assert len(results) == 1
        assert results[0].id == "d4", f"expected d4, got {results[0].id if results else None}"

    def test_add_documents_in_multiple_batches_does_not_raise_index_error(self):
        """回归测试：分批添加后查询不应抛 IndexError（旧实现会越界）."""
        store = TfidfKnowledgeStore()
        store.add_documents([Document(id="d1", content="alpha")])
        store.add_documents([Document(id="d2", content="beta")])
        store.add_documents([Document(id="d3", content="gamma")])
        # 任一词项查询都不应抛 IndexError
        for term in ("alpha", "beta", "gamma"):
            results = store.search(term, top_k=3)
            assert all(r.id for r in results)
