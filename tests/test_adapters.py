"""Tests for context_memory adapters (zero external deps)."""

import pytest
from agent_eval.context_memory.adapters.base import (
    ContextQualityServiceAdapter,
    MemoryServiceAdapter,
    RetrievalServiceAdapter,
)
from agent_eval.context_memory.adapters.local import LocalFunctionAdapter
from agent_eval.context_memory.adapters.mock import MockAdapter
from agent_eval.context_memory.models import (
    Document,
    MemoryAnswer,
    MemoryTurn,
    RankedDocument,
)


class TestMockAdapter:
    def test_retrieve_returns_fixed(self):
        adapter = MockAdapter(
            ranked_docs=[RankedDocument(doc_id="d1", score=0.9, rank=1)]
        )
        docs = [Document(doc_id="d1", text="text")]
        result = adapter.retrieve("query", docs, top_k=5)
        assert len(result) == 1
        assert result[0].doc_id == "d1"

    def test_store_and_query_memory(self):
        adapter = MockAdapter(memory_answer="stored answer")
        adapter.store_memory("s1", [MemoryTurn(role="user", content="Hi")])
        result = adapter.query_memory("s1", "What did I say?")
        assert result.answer == "stored answer"

    def test_compress_context(self):
        adapter = MockAdapter(compressed_context="compressed")
        result = adapter.compress_context([], budget_tokens=100)
        assert result == "compressed"

    def test_answer_with_context(self):
        adapter = MockAdapter(qa_answer="the answer")
        result = adapter.answer_with_context("some context", "question")
        assert result.answer == "the answer"

    def test_default_retrieve_empty(self):
        adapter = MockAdapter()
        result = adapter.retrieve("query", [], top_k=5)
        assert isinstance(result, list)

    def test_default_query_memory(self):
        adapter = MockAdapter()
        result = adapter.query_memory("s1", "What?")
        assert isinstance(result, MemoryAnswer)


class TestLocalFunctionAdapter:
    def test_retrieve_fn(self):
        def my_retrieve(query, corpus, top_k):
            return [RankedDocument(doc_id=corpus[0].doc_id, score=1.0, rank=1)]

        adapter = LocalFunctionAdapter(retrieve_fn=my_retrieve)
        docs = [Document(doc_id="d1", text="text")]
        result = adapter.retrieve("query", docs, top_k=5)
        assert result[0].doc_id == "d1"

    def test_memory_fns(self):
        store_called = []

        def store_fn(session_id, history):
            store_called.append(session_id)

        def query_fn(session_id, question):
            return MemoryAnswer(task_id="t1", answer=f"answer for {session_id}")

        adapter = LocalFunctionAdapter(store_fn=store_fn, query_fn=query_fn)
        adapter.store_memory("sess1", [])
        assert "sess1" in store_called
        result = adapter.query_memory("sess1", "Q?")
        assert "sess1" in result.answer

    def test_context_fns(self):
        adapter = LocalFunctionAdapter(
            compress_fn=lambda docs, budget: "compressed",
            answer_fn=lambda ctx, q: "answer",
        )
        assert adapter.compress_context(["doc"], 100) == "compressed"
        assert adapter.answer_with_context("ctx", "q") == "answer"

    def test_missing_fn_raises(self):
        adapter = LocalFunctionAdapter()
        with pytest.raises((NotImplementedError, AttributeError, TypeError)):
            adapter.retrieve("q", [], top_k=5)

    def test_protocol_compliance(self):
        adapter = MockAdapter()
        assert isinstance(adapter, RetrievalServiceAdapter)
        assert isinstance(adapter, MemoryServiceAdapter)
        assert isinstance(adapter, ContextQualityServiceAdapter)
