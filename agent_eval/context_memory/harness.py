"""统一评测 Harness：ContextMemoryEvalHarness。

接受任意实现了 Adapter 协议的对象，自动按任务类型选择评估器套件，
输出含 UC 对齐表的 ContextMemoryReport。

支持三种运行模式：
- ``offline``：完整 benchmark，用于版本对比和能力基线
- ``regression``：小样本抽样，用于常规回归（auto 选 max_samples）
- ``stress``：压力测试（观察退化曲线）
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from agent_eval.context_memory.adapters.base import (
    ContextQualityServiceAdapter,
    MemoryServiceAdapter,
    RetrievalServiceAdapter,
)
from agent_eval.context_memory.graders.context import ContextQualitySuiteGrader
from agent_eval.context_memory.graders.degradation import LengthDegradationGrader
from agent_eval.context_memory.graders.memory import MemorySuiteGrader
from agent_eval.context_memory.graders.retrieval import RetrievalSuiteGrader
from agent_eval.context_memory.models import (
    ContextMemoryEvalResult,
    ContextMemoryReport,
    ContextQualityResult,
    ContextQualityTask,
    MemoryAnswer,
    MemoryTask,
    RetrievalResult,
    RetrievalTask,
)

LLMJudgeFn = Callable[[str, str, str], Dict[str, Any]]


class EvalMode(Enum):
    OFFLINE = "offline"
    REGRESSION = "regression"
    STRESS = "stress"


# UC 对齐表（benchmark -> 支撑的 UC 列表）
_UC_ALIGNMENT: Dict[str, List[str]] = {
    "BEIR": ["UC005", "UC012"],
    "LongMemEval": ["UC004", "UC008", "UC010", "UC013"],
    "LongBench v2": ["UC001", "UC007", "UC009"],
    "LoCoMo": ["UC009", "UC010"],
    "RULER": ["UC003", "UC004", "UC009"],
    "custom": ["UC002", "UC006", "UC011", "UC014"],
}

_REGRESSION_SAMPLE_SIZE = 20


class ContextMemoryEvalHarness:
    """上下文/记忆评测 Harness。

    Parameters
    ----------
    adapter:
        实现了 ``RetrievalServiceAdapter`` / ``MemoryServiceAdapter`` /
        ``ContextQualityServiceAdapter`` 中至少一个协议的服务适配器对象。
    benchmark_name:
        当前评测的 benchmark 名称（影响报告和 UC 对齐表）。
    mode:
        运行模式（offline / regression / stress），默认 offline。
    max_samples:
        最大任务数（None 表示不限制；regression 模式下默认 20）。
    seed:
        随机种子（regression 模式下采样用）。
    ndcg_k:
        nDCG@k 的 k 值（默认 10）。
    passing_threshold:
        全局通过阈值（默认 0.5）。
    judge_fn:
        可选 LLM judge 函数，注入后 grader 会在精确匹配失败时调用 LLM 打分。
    """

    def __init__(
        self,
        adapter: Any,
        benchmark_name: str = "custom",
        mode: Union[EvalMode, str] = EvalMode.OFFLINE,
        max_samples: Optional[int] = None,
        seed: Optional[int] = None,
        ndcg_k: int = 10,
        passing_threshold: float = 0.5,
        judge_fn: Optional[LLMJudgeFn] = None,
    ) -> None:
        self.adapter = adapter
        self.benchmark_name = benchmark_name
        self.mode = EvalMode(mode) if isinstance(mode, str) else mode
        self.seed = seed
        self.ndcg_k = ndcg_k
        self.passing_threshold = passing_threshold
        self.judge_fn = judge_fn

        if self.mode == EvalMode.REGRESSION and max_samples is None:
            self.max_samples = _REGRESSION_SAMPLE_SIZE
        else:
            self.max_samples = max_samples

        self._retrieval_grader = RetrievalSuiteGrader(
            k=ndcg_k,
            ndcg_threshold=passing_threshold,
            recall_threshold=passing_threshold,
            mrr_threshold=passing_threshold,
        )
        self._memory_grader = MemorySuiteGrader(
            passing_threshold=passing_threshold, judge_fn=judge_fn
        )
        self._context_grader = ContextQualitySuiteGrader(
            passing_f1_threshold=passing_threshold, judge_fn=judge_fn
        )
        self._degradation_grader = LengthDegradationGrader()

    def _sample(self, tasks: List[Any]) -> List[Any]:
        if self.max_samples is None or len(tasks) <= self.max_samples:
            return tasks
        rng = random.Random(self.seed)
        return rng.sample(tasks, self.max_samples)

    # ------------------------------------------------------------------
    # 检索评测
    # ------------------------------------------------------------------

    def run_retrieval(
        self, tasks: List[RetrievalTask]
    ) -> ContextMemoryReport:
        """对检索任务列表运行评测。"""
        if not isinstance(self.adapter, RetrievalServiceAdapter):
            raise TypeError(
                f"Adapter {type(self.adapter).__name__} 未实现 RetrievalServiceAdapter 协议。"
            )
        sampled = self._sample(tasks)
        results: List[ContextMemoryEvalResult] = []
        for task in sampled:
            try:
                ranked_docs = self.adapter.retrieve(task.query, task.corpus, top_k=self.ndcg_k)
                retrieval_result = RetrievalResult(task_id=task.task_id, ranked_docs=ranked_docs)
                result = self._retrieval_grader.grade(task, retrieval_result)
            except Exception as e:
                result = ContextMemoryEvalResult(
                    task_id=task.task_id,
                    task_type="retrieval",
                    passed=False,
                    error=str(e),
                )
            results.append(result)
        return ContextMemoryReport(
            benchmark_name=self.benchmark_name,
            results=results,
            metadata={"uc_alignment": _UC_ALIGNMENT.get(self.benchmark_name, [])},
        )

    # ------------------------------------------------------------------
    # 记忆评测
    # ------------------------------------------------------------------

    def run_memory(
        self, tasks: List[MemoryTask]
    ) -> ContextMemoryReport:
        """对记忆任务列表运行评测。"""
        if not isinstance(self.adapter, MemoryServiceAdapter):
            raise TypeError(
                f"Adapter {type(self.adapter).__name__} 未实现 MemoryServiceAdapter 协议。"
            )
        sampled = self._sample(tasks)
        results: List[ContextMemoryEvalResult] = []
        for task in sampled:
            try:
                self.adapter.store_memory(task.session_id, task.history)
                answer = self.adapter.query_memory(task.session_id, task.question)
                answer.task_id = task.task_id
                result = self._memory_grader.grade(task, answer)
            except Exception as e:
                result = ContextMemoryEvalResult(
                    task_id=task.task_id,
                    task_type="memory",
                    passed=False,
                    error=str(e),
                )
            results.append(result)
        return ContextMemoryReport(
            benchmark_name=self.benchmark_name,
            results=results,
            metadata={"uc_alignment": _UC_ALIGNMENT.get(self.benchmark_name, [])},
        )

    # ------------------------------------------------------------------
    # 上下文质量评测
    # ------------------------------------------------------------------

    def run_context_quality(
        self,
        tasks: List[ContextQualityTask],
        compare_raw: bool = False,
    ) -> ContextMemoryReport:
        """对上下文质量任务列表运行评测。

        Parameters
        ----------
        tasks:
            上下文质量任务列表。
        compare_raw:
            若为 True，额外用原始上下文（context_mode=RAW）跑一遍作为对照，
            用于计算压缩保真度。
        """
        if not isinstance(self.adapter, ContextQualityServiceAdapter):
            raise TypeError(
                f"Adapter {type(self.adapter).__name__} 未实现 ContextQualityServiceAdapter 协议。"
            )
        sampled = self._sample(tasks)
        results: List[ContextMemoryEvalResult] = []
        for task in sampled:
            try:
                raw_result: Optional[ContextQualityResult] = None
                if compare_raw and task.documents:
                    raw_context = "\n\n".join(d.text for d in task.documents)
                    raw_result = self.adapter.answer_with_context(raw_context, task.question)
                    raw_result.task_id = task.task_id

                if task.documents and task.budget_tokens:
                    context = self.adapter.compress_context(task.documents, task.budget_tokens)
                elif task.documents:
                    context = "\n\n".join(d.text for d in task.documents)
                else:
                    context = ""

                result_obj = self.adapter.answer_with_context(context, task.question)
                result_obj.task_id = task.task_id
                result = self._context_grader.grade(task, result_obj, raw_result=raw_result)
            except Exception as e:
                result = ContextMemoryEvalResult(
                    task_id=task.task_id,
                    task_type="context_quality",
                    passed=False,
                    error=str(e),
                )
            results.append(result)
        return ContextMemoryReport(
            benchmark_name=self.benchmark_name,
            results=results,
            metadata={"uc_alignment": _UC_ALIGNMENT.get(self.benchmark_name, [])},
        )

    # ------------------------------------------------------------------
    # 退化曲线评测（RULER 场景）
    # ------------------------------------------------------------------

    def run_degradation(
        self, tasks: List[ContextQualityTask]
    ) -> ContextMemoryReport:
        """运行退化曲线评测，记录各 context_length 下的 accuracy。"""
        if not isinstance(self.adapter, ContextQualityServiceAdapter):
            raise TypeError(
                f"Adapter {type(self.adapter).__name__} 未实现 ContextQualityServiceAdapter 协议。"
            )
        sampled = self._sample(tasks)
        point_results: List[ContextMemoryEvalResult] = []
        self._degradation_grader.reset()

        for task in sampled:
            try:
                context_length = int(task.metadata.get("context_length", 0))
                context = "\n\n".join(d.text for d in task.documents) if task.documents else ""
                result_obj = self.adapter.answer_with_context(context, task.question)
                result_obj.task_id = task.task_id
                point_result = self._degradation_grader.record(task, result_obj, context_length)
                point_results.append(point_result)
            except Exception as e:
                point_results.append(
                    ContextMemoryEvalResult(
                        task_id=task.task_id,
                        task_type="context_quality",
                        passed=False,
                        error=str(e),
                    )
                )

        suite_result = self._degradation_grader.grade_suite()
        return ContextMemoryReport(
            benchmark_name=self.benchmark_name,
            results=point_results + [suite_result],
            metadata={
                "uc_alignment": _UC_ALIGNMENT.get(self.benchmark_name, ["UC003", "UC009"]),
                "degradation_analysis": suite_result.metadata.get("analysis", {}),
            },
        )

    # ------------------------------------------------------------------
    # 自动路由（根据任务类型自动选择评测方法）
    # ------------------------------------------------------------------

    def run(self, tasks: List[Any]) -> ContextMemoryReport:
        """自动根据任务类型路由到对应的评测方法。

        支持混合任务列表（RetrievalTask / MemoryTask / ContextQualityTask）。
        """
        retrieval_tasks = [t for t in tasks if isinstance(t, RetrievalTask)]
        memory_tasks = [t for t in tasks if isinstance(t, MemoryTask)]
        context_tasks = [t for t in tasks if isinstance(t, ContextQualityTask)]

        all_results: List[ContextMemoryEvalResult] = []

        if retrieval_tasks:
            report = self.run_retrieval(retrieval_tasks)
            all_results.extend(report.results)
        if memory_tasks:
            report = self.run_memory(memory_tasks)
            all_results.extend(report.results)
        if context_tasks:
            if self.mode == EvalMode.STRESS:
                report = self.run_degradation(context_tasks)
            else:
                report = self.run_context_quality(context_tasks)
            all_results.extend(report.results)

        return ContextMemoryReport(
            benchmark_name=self.benchmark_name,
            results=all_results,
            metadata={"uc_alignment": _UC_ALIGNMENT.get(self.benchmark_name, [])},
        )
