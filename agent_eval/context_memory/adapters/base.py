"""Service Adapter 协议：连接评测框架与任意被测上下文/记忆服务。

本模块定义三个 Protocol，用户通过实现其中一个或多个来对接自己的系统。
框架不绑定任何特定服务（ContextAgent 或其他系统均可通过实现 Protocol 接入）。

典型用法::

    class MyRetrievalAdapter:
        def retrieve(self, query, corpus, top_k):
            # 调用你自己的检索服务
            ...

    harness = ContextMemoryEvalHarness(adapter=MyRetrievalAdapter())
"""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable

from agent_eval.context_memory.models import (
    ContextQualityResult,
    Document,
    MemoryAnswer,
    MemoryTurn,
    RankedDocument,
)


@runtime_checkable
class RetrievalServiceAdapter(Protocol):
    """对接检索能力的服务 Adapter 协议。

    适用场景：BEIR、UC004（即时上下文检索）、UC005（混合式召回）、UC012（混合检索）。
    """

    def retrieve(
        self,
        query: str,
        corpus: List[Document],
        top_k: int = 10,
    ) -> List[RankedDocument]:
        """执行检索，返回按相关性降序排列的文档列表。

        Parameters
        ----------
        query:
            检索查询字符串。
        corpus:
            候选文档语料库。
        top_k:
            返回前 k 个结果。

        Returns
        -------
        List[RankedDocument]
            排序后的文档列表，长度不超过 top_k。
        """
        ...


@runtime_checkable
class MemoryServiceAdapter(Protocol):
    """对接长期记忆能力的服务 Adapter 协议。

    适用场景：LongMemEval、UC004、UC008（记忆异步处理）、UC010（工作记忆）、UC013（版本管理）。
    """

    def store_memory(self, session_id: str, history: List[MemoryTurn]) -> None:
        """将对话历史存入记忆系统。

        Parameters
        ----------
        session_id:
            会话 ID，用于隔离不同用户/会话的记忆。
        history:
            需要存储的对话历史。
        """
        ...

    def query_memory(self, session_id: str, question: str) -> MemoryAnswer:
        """从记忆系统中检索并回答问题。

        Parameters
        ----------
        session_id:
            会话 ID。
        question:
            需要回答的问题。

        Returns
        -------
        MemoryAnswer
            包含答案文本及可选的置信度/来源信息。
        """
        ...


@runtime_checkable
class ContextQualityServiceAdapter(Protocol):
    """对接上下文质量能力的服务 Adapter 协议。

    适用场景：LongBench v2、UC001（多源聚合）、UC007（接口调用）、UC009（压缩/摘要）。
    """

    def compress_context(self, documents: List[Document], budget_tokens: int) -> str:
        """对文档列表进行压缩/摘要，返回压缩后的上下文字符串。

        Parameters
        ----------
        documents:
            需要压缩的原始文档列表。
        budget_tokens:
            目标 token 预算（压缩后上下文的最大长度估计）。

        Returns
        -------
        str
            压缩后的上下文文本。
        """
        ...

    def answer_with_context(self, context: str, question: str) -> ContextQualityResult:
        """基于给定上下文回答问题。

        Parameters
        ----------
        context:
            喂给模型的上下文内容（可能是原始 / 压缩 / 检索注入后的）。
        question:
            需要回答的问题。

        Returns
        -------
        ContextQualityResult
            包含答案、token 使用量等信息。
        """
        ...
