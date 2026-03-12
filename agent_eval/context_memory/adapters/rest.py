"""RESTServiceAdapter：通用 HTTP REST Adapter，对接任意基于 REST API 的上下文/记忆服务。

用法示例::

    adapter = RESTServiceAdapter(
        base_url="http://localhost:8080",
        endpoints={
            "retrieve": "/api/v1/context/retrieve",
            "store_memory": "/api/v1/memory/store",
            "query_memory": "/api/v1/memory/query",
            "compress": "/api/v1/context/compress",
            "answer": "/api/v1/context/answer",
        },
        headers={"Authorization": "Bearer <token>"},
        timeout=30,
    )
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from agent_eval.context_memory.models import (
    ContextQualityResult,
    Document,
    MemoryAnswer,
    MemoryTurn,
    RankedDocument,
)


class RESTServiceAdapter:
    """通用 HTTP REST Service Adapter（零外部依赖，仅用标准库 urllib）。

    若安装了 ``requests`` 库则自动切换为更健壮的实现（支持 session / connection pool）。

    Parameters
    ----------
    base_url:
        被测服务的根 URL，如 ``http://localhost:8080``。
    endpoints:
        端点路径映射，支持以下 key：
        ``retrieve`` / ``store_memory`` / ``query_memory`` / ``compress`` / ``answer``。
        未配置的端点调用时会抛出 ``NotImplementedError``。
    headers:
        HTTP 请求头（如 Authorization）。
    timeout:
        单次请求超时秒数（默认 30）。
    max_retries:
        失败重试次数（默认 2）。
    """

    def __init__(
        self,
        base_url: str,
        endpoints: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.endpoints: Dict[str, str] = endpoints or {}
        self.headers: Dict[str, str] = {"Content-Type": "application/json", **(headers or {})}
        self.timeout = timeout
        self.max_retries = max_retries
        self._use_requests = self._check_requests()

    @staticmethod
    def _check_requests() -> bool:
        try:
            import requests  # noqa: F401
            return True
        except ImportError:
            return False

    def _post(self, endpoint_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """向指定端点发 POST 请求，返回解析后的 JSON 响应体。"""
        if endpoint_key not in self.endpoints:
            raise NotImplementedError(
                f"端点 '{endpoint_key}' 未配置。请在 RESTServiceAdapter 的 endpoints 参数中添加该端点。"
            )
        url = self.base_url + self.endpoints[endpoint_key]
        body = json.dumps(payload).encode("utf-8")

        last_exc: Optional[Exception] = None
        for _ in range(max(1, self.max_retries + 1)):
            try:
                if self._use_requests:
                    return self._post_requests(url, payload)
                return self._post_urllib(url, body)
            except Exception as e:
                last_exc = e
        raise RuntimeError(f"请求失败（{url}）：{last_exc}") from last_exc

    def _post_urllib(self, url: str, body: bytes) -> Dict[str, Any]:
        req = urllib.request.Request(url, data=body, headers=self.headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _post_requests(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        import requests

        resp = requests.post(url, json=payload, headers=self.headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # RetrievalServiceAdapter 接口
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        corpus: List[Document],
        top_k: int = 10,
    ) -> List[RankedDocument]:
        """调用检索端点，返回排序后的文档列表。

        请求体格式::

            {"query": str, "corpus": [{"doc_id": str, "text": str, ...}], "top_k": int}

        期望响应格式::

            {"results": [{"doc_id": str, "score": float, "rank": int, "text": str}]}
        """
        payload = {
            "query": query,
            "corpus": [{"doc_id": d.doc_id, "text": d.text, "title": d.title} for d in corpus],
            "top_k": top_k,
        }
        resp = self._post("retrieve", payload)
        ranked = []
        for i, item in enumerate(resp.get("results", [])):
            ranked.append(
                RankedDocument(
                    doc_id=item["doc_id"],
                    score=float(item.get("score", 0.0)),
                    rank=item.get("rank", i + 1),
                    text=item.get("text", ""),
                )
            )
        return ranked

    # ------------------------------------------------------------------
    # MemoryServiceAdapter 接口
    # ------------------------------------------------------------------

    def store_memory(self, session_id: str, history: List[MemoryTurn]) -> None:
        """调用记忆存储端点。

        请求体格式::

            {"session_id": str, "history": [{"role": str, "content": str, "timestamp": str|null}]}
        """
        payload = {
            "session_id": session_id,
            "history": [
                {"role": t.role, "content": t.content, "timestamp": t.timestamp}
                for t in history
            ],
        }
        self._post("store_memory", payload)

    def query_memory(self, session_id: str, question: str) -> MemoryAnswer:
        """调用记忆查询端点。

        请求体格式::

            {"session_id": str, "question": str}

        期望响应格式::

            {"answer": str, "confidence": float|null, "source_turns": [int]}
        """
        payload = {"session_id": session_id, "question": question}
        resp = self._post("query_memory", payload)
        return MemoryAnswer(
            task_id="",
            answer=resp.get("answer", ""),
            confidence=resp.get("confidence"),
            source_turns=resp.get("source_turns", []),
        )

    # ------------------------------------------------------------------
    # ContextQualityServiceAdapter 接口
    # ------------------------------------------------------------------

    def compress_context(self, documents: List[Document], budget_tokens: int) -> str:
        """调用上下文压缩端点。

        请求体格式::

            {"documents": [...], "budget_tokens": int}

        期望响应格式::

            {"compressed_context": str}
        """
        payload = {
            "documents": [{"doc_id": d.doc_id, "text": d.text, "title": d.title} for d in documents],
            "budget_tokens": budget_tokens,
        }
        resp = self._post("compress", payload)
        return resp.get("compressed_context", "")

    def answer_with_context(self, context: str, question: str) -> ContextQualityResult:
        """调用上下文问答端点。

        请求体格式::

            {"context": str, "question": str}

        期望响应格式::

            {"answer": str, "tokens_used": int|null, "latency_ms": float|null}
        """
        payload = {"context": context, "question": question}
        resp = self._post("answer", payload)
        return ContextQualityResult(
            task_id="",
            answer=resp.get("answer", ""),
            tokens_used=resp.get("tokens_used"),
            context_used=context,
            latency_ms=resp.get("latency_ms"),
        )
