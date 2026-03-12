"""LocalFunctionAdapter：将本地 Python 函数直接包装为 Service Adapter。

适用于本地模块集成测试或冒烟测试（不走 HTTP）。

用法::

    def my_retrieve(query, corpus, top_k):
        # 你的本地检索逻辑
        return [RankedDocument(doc_id="d1", score=0.9, rank=1)]

    adapter = LocalFunctionAdapter(retrieve_fn=my_retrieve)
    harness = ContextMemoryEvalHarness(adapter=adapter)
"""

from __future__ import annotations

from typing import Callable, List, Optional

from agent_eval.context_memory.models import (
    ContextQualityResult,
    Document,
    MemoryAnswer,
    MemoryTurn,
    RankedDocument,
)

RetrieveFn = Callable[[str, List[Document], int], List[RankedDocument]]
StoreMemoryFn = Callable[[str, List[MemoryTurn]], None]
QueryMemoryFn = Callable[[str, str], MemoryAnswer]
CompressFn = Callable[[List[Document], int], str]
AnswerFn = Callable[[str, str], ContextQualityResult]


class LocalFunctionAdapter:
    """将本地 Python 函数包装为 Service Adapter。

    未配置的函数调用时抛出 ``NotImplementedError``。

    Parameters
    ----------
    retrieve_fn:
        ``(query, corpus, top_k) -> List[RankedDocument]``
    store_fn:
        ``(session_id, history) -> None``
    query_fn:
        ``(session_id, question) -> MemoryAnswer``
    compress_fn:
        ``(documents, budget_tokens) -> str``
    answer_fn:
        ``(context, question) -> ContextQualityResult``
    """

    def __init__(
        self,
        retrieve_fn: Optional[RetrieveFn] = None,
        store_fn: Optional[StoreMemoryFn] = None,
        query_fn: Optional[QueryMemoryFn] = None,
        compress_fn: Optional[CompressFn] = None,
        answer_fn: Optional[AnswerFn] = None,
    ) -> None:
        self._retrieve_fn = retrieve_fn
        self._store_fn = store_fn
        self._query_fn = query_fn
        self._compress_fn = compress_fn
        self._answer_fn = answer_fn

    def retrieve(self, query: str, corpus: List[Document], top_k: int = 10) -> List[RankedDocument]:
        if self._retrieve_fn is None:
            raise NotImplementedError("retrieve_fn 未配置")
        return self._retrieve_fn(query, corpus, top_k)

    def store_memory(self, session_id: str, history: List[MemoryTurn]) -> None:
        if self._store_fn is None:
            raise NotImplementedError("store_fn 未配置")
        self._store_fn(session_id, history)

    def query_memory(self, session_id: str, question: str) -> MemoryAnswer:
        if self._query_fn is None:
            raise NotImplementedError("query_fn 未配置")
        return self._query_fn(session_id, question)

    def compress_context(self, documents: List[Document], budget_tokens: int) -> str:
        if self._compress_fn is None:
            raise NotImplementedError("compress_fn 未配置")
        return self._compress_fn(documents, budget_tokens)

    def answer_with_context(self, context: str, question: str) -> ContextQualityResult:
        if self._answer_fn is None:
            raise NotImplementedError("answer_fn 未配置")
        return self._answer_fn(context, question)
