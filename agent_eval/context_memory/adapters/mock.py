"""MockAdapter：固定返回值的 Adapter，用于框架自身单测与快速冒烟测试。"""

from __future__ import annotations

from typing import List, Optional

from agent_eval.context_memory.models import (
    ContextQualityResult,
    Document,
    MemoryAnswer,
    MemoryTurn,
    RankedDocument,
)


class MockAdapter:
    """固定返回预设数据的 Adapter，适用于单测与冒烟测试。

    Parameters
    ----------
    ranked_docs:
        ``retrieve`` 调用的固定返回值（默认：corpus 前 top_k 个，score=1.0）。
    memory_answer:
        ``query_memory`` 调用的固定返回答案文本（默认："mock_answer"）。
    compressed_context:
        ``compress_context`` 调用的固定返回（默认：文档文本拼接）。
    qa_answer:
        ``answer_with_context`` 调用的固定返回答案文本（默认："mock_answer"）。
    """

    def __init__(
        self,
        ranked_docs: Optional[List[RankedDocument]] = None,
        memory_answer: str = "mock_answer",
        compressed_context: Optional[str] = None,
        qa_answer: str = "mock_answer",
    ) -> None:
        self._ranked_docs = ranked_docs
        self._memory_answer = memory_answer
        self._compressed_context = compressed_context
        self._qa_answer = qa_answer
        self._stored_sessions: dict = {}

    def retrieve(self, query: str, corpus: List[Document], top_k: int = 10) -> List[RankedDocument]:
        if self._ranked_docs is not None:
            return self._ranked_docs[:top_k]
        return [
            RankedDocument(doc_id=d.doc_id, score=1.0, rank=i + 1, text=d.text)
            for i, d in enumerate(corpus[:top_k])
        ]

    def store_memory(self, session_id: str, history: List[MemoryTurn]) -> None:
        self._stored_sessions[session_id] = history

    def query_memory(self, session_id: str, question: str) -> MemoryAnswer:
        return MemoryAnswer(task_id="", answer=self._memory_answer)

    def compress_context(self, documents: List[Document], budget_tokens: int) -> str:
        if self._compressed_context is not None:
            return self._compressed_context
        return " ".join(d.text for d in documents)[:budget_tokens]

    def answer_with_context(self, context: str, question: str) -> ContextQualityResult:
        return ContextQualityResult(
            task_id="",
            answer=self._qa_answer,
            context_used=context,
        )
