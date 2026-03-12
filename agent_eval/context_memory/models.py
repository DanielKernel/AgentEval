"""上下文与记忆评测数据模型。

涵盖三类评测任务：
- RetrievalTask / RetrievalResult：检索评测（BEIR / UC004 / UC005 / UC012）
- MemoryTask / MemoryAnswer：长期记忆评测（LongMemEval / UC008 / UC010 / UC013）
- ContextQualityTask / ContextQualityResult：上下文质量评测（LongBench v2 / UC001 / UC007 / UC009）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 公共类型
# ---------------------------------------------------------------------------


@dataclass
class Document:
    """语料库中的单篇文档。"""

    doc_id: str
    text: str
    title: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RankedDocument:
    """检索排序后的文档条目。"""

    doc_id: str
    score: float
    rank: int = 0
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 检索评测
# ---------------------------------------------------------------------------


@dataclass
class RetrievalTask:
    """检索评测任务：query + 候选语料库 + gold doc IDs。

    用于 BEIR、UC005（混合式召回）、UC012（结构化存储与混合检索）等场景。
    """

    task_id: str
    query: str
    corpus: List[Document] = field(default_factory=list)
    relevant_doc_ids: List[str] = field(default_factory=list)
    """gold 相关文档 ID 列表（用于计算 nDCG@k、Recall@k 等）。"""
    relevance_scores: Dict[str, int] = field(default_factory=dict)
    """doc_id -> relevance grade（可选，支持分级相关性，如 0/1/2）。未提供则默认 relevant_doc_ids 内均为 1。"""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """检索结果：服务返回的排序文档列表。"""

    task_id: str
    ranked_docs: List[RankedDocument] = field(default_factory=list)
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 记忆评测
# ---------------------------------------------------------------------------


class MemoryTaskType(Enum):
    """记忆评测任务类型（对应 LongMemEval 四类子任务）。"""

    QA = "qa"
    """跨会话 QA：从历史对话中检索答案。"""
    TEMPORAL = "temporal"
    """时序推理：涉及时间顺序、先后关系的问题。"""
    UPDATE = "update"
    """知识更新：用户更新某条信息后，系统是否一致返回新值。"""
    ABSTENTION = "abstention"
    """适当拒绝回答：系统记忆中不存在答案时，应返回 "不知道" 而非捏造。"""


@dataclass
class MemoryTurn:
    """单轮对话（用于构建会话历史）。"""

    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryTask:
    """记忆评测任务：历史对话 + 问题 + 期望答案 + 任务类型。

    用于 LongMemEval、UC004/UC008/UC010/UC013 等场景。
    """

    task_id: str
    session_id: str
    history: List[MemoryTurn]
    question: str
    gold_answer: str
    task_type: MemoryTaskType = MemoryTaskType.QA
    should_abstain: bool = False
    """若为 True，期望系统回答 "不知道" 而非给出具体答案（配合 ABSTENTION 类型使用）。"""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryAnswer:
    """记忆服务的返回结果。"""

    task_id: str
    answer: str
    confidence: Optional[float] = None
    source_turns: List[int] = field(default_factory=list)
    """来源轮次索引（可选，用于可解释性评估）。"""
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 上下文质量评测
# ---------------------------------------------------------------------------


class ContextMode(Enum):
    """上下文模式（用于 LongBench v2 对比实验）。"""

    RAW = "raw"
    """原始完整上下文，未经任何处理。"""
    COMPRESSED = "compressed"
    """压缩/摘要后的上下文。"""
    RETRIEVED = "retrieved"
    """检索注入式上下文（retrieve-then-inject）。"""


@dataclass
class ContextQualityTask:
    """上下文质量评测任务：给定上下文 + 问题 + 期望答案。

    用于 LongBench v2、UC001/UC007/UC009 等场景。
    支持多种上下文模式对比（raw vs compressed vs retrieved）。
    """

    task_id: str
    question: str
    gold_answer: str
    documents: List[Document] = field(default_factory=list)
    """原始文档列表（交给被测服务处理后回答问题）。"""
    context_mode: ContextMode = ContextMode.RAW
    budget_tokens: Optional[int] = None
    """压缩目标 token 数（仅 COMPRESSED 模式下有意义）。"""
    domain: str = ""
    """任务领域，如 single_doc_qa / multi_doc_qa / code / dialogue。"""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextQualityResult:
    """上下文质量评测结果：服务返回的答案 + 使用的 token 数。"""

    task_id: str
    answer: str
    tokens_used: Optional[int] = None
    context_used: str = ""
    """实际喂给模型的上下文内容（用于压缩保真度分析）。"""
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 统一评测结果
# ---------------------------------------------------------------------------


@dataclass
class MetricValue:
    """单个指标的评测值。"""

    name: str
    value: float
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextMemoryEvalResult:
    """单个任务的统一评测结果（跨三类任务）。"""

    task_id: str
    task_type: str  # "retrieval" | "memory" | "context_quality"
    passed: bool
    metrics: List[MetricValue] = field(default_factory=list)
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_metric(self, name: str) -> Optional[float]:
        """按名称查找指标值，不存在时返回 None。"""
        for m in self.metrics:
            if m.name == name:
                return m.value
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "passed": self.passed,
            "metrics": {m.name: m.value for m in self.metrics},
            "error": self.error,
        }


@dataclass
class ContextMemoryReport:
    """评测报告：汇总所有任务结果，对齐 UC 映射表。"""

    benchmark_name: str
    results: List[ContextMemoryEvalResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_tasks(self) -> int:
        return len(self.results)

    @property
    def passed_tasks(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def pass_rate(self) -> float:
        return self.passed_tasks / self.total_tasks if self.total_tasks else 0.0

    def aggregate_metric(self, name: str) -> Optional[float]:
        """对所有任务中指定指标取均值，若无则返回 None。"""
        values = [r.get_metric(name) for r in self.results if r.get_metric(name) is not None]
        return sum(values) / len(values) if values else None

    def summary(self) -> Dict[str, Any]:
        metric_names: List[str] = []
        seen = set()
        for r in self.results:
            for m in r.metrics:
                if m.name not in seen:
                    metric_names.append(m.name)
                    seen.add(m.name)

        return {
            "benchmark": self.benchmark_name,
            "total_tasks": self.total_tasks,
            "passed_tasks": self.passed_tasks,
            "pass_rate": round(self.pass_rate, 4),
            "metrics": {name: round(v, 4) for name in metric_names if (v := self.aggregate_metric(name)) is not None},
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark": self.benchmark_name,
            "summary": self.summary(),
            "results": [r.to_dict() for r in self.results],
        }
