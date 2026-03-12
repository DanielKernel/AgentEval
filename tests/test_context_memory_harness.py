"""Tests for the ContextMemoryEvalHarness (zero external deps, uses MockAdapter)."""

import pytest
from agent_eval.context_memory.adapters.mock import MockAdapter
from agent_eval.context_memory.harness import ContextMemoryEvalHarness, EvalMode
from agent_eval.context_memory.models import (
    ContextQualityTask,
    ContextMode,
    Document,
    MemoryAnswer,
    MemoryTask,
    MemoryTaskType,
    MemoryTurn,
    RankedDocument,
    RetrievalTask,
)


def make_retrieval_task(task_id="rt1"):
    corpus = [Document(doc_id=f"d{i}", text=f"text {i}") for i in range(5)]
    return RetrievalTask(
        task_id=task_id,
        query="What is AI?",
        corpus=corpus,
        relevant_doc_ids=["d0", "d2"],
    )


def make_memory_task(task_id="mt1"):
    return MemoryTask(
        task_id=task_id,
        session_id="s1",
        history=[MemoryTurn(role="user", content="My name is Alice")],
        question="What is my name?",
        gold_answer="Alice",
        task_type=MemoryTaskType.QA,
    )


def make_context_quality_task(task_id="cq1"):
    return ContextQualityTask(
        task_id=task_id,
        documents=["Long document about AI. " * 20],
        question="What is AI?",
        gold_answer="Artificial Intelligence",
        budget_tokens=100,
        context_mode=ContextMode.COMPRESSED,
    )


class TestEvalMode:
    def test_enum_values(self):
        assert EvalMode.OFFLINE.value == "offline"
        assert EvalMode.REGRESSION.value == "regression"
        assert EvalMode.STRESS.value == "stress"


class TestContextMemoryEvalHarness:
    def test_run_retrieval(self):
        adapter = MockAdapter(
            ranked_docs=[
                RankedDocument(doc_id="d0", score=0.9, rank=1),
                RankedDocument(doc_id="d1", score=0.8, rank=2),
                RankedDocument(doc_id="d2", score=0.7, rank=3),
            ]
        )
        harness = ContextMemoryEvalHarness(adapter=adapter)
        tasks = [make_retrieval_task("rt1"), make_retrieval_task("rt2")]
        report = harness.run_retrieval(tasks)
        assert len(report.results) == 2
        assert all(r.task_type == "retrieval" for r in report.results)

    def test_run_memory(self):
        adapter = MockAdapter(
            memory_answer="Alice"
        )
        harness = ContextMemoryEvalHarness(adapter=adapter)
        tasks = [make_memory_task("mt1")]
        report = harness.run_memory(tasks)
        assert len(report.results) == 1
        assert report.results[0].get_metric("token_f1") == pytest.approx(1.0)

    def test_run_context_quality(self):
        adapter = MockAdapter(
            compressed_context="Artificial Intelligence is...",
            qa_answer="Artificial Intelligence",
        )
        harness = ContextMemoryEvalHarness(adapter=adapter)
        tasks = [make_context_quality_task("cq1")]
        report = harness.run_context_quality(tasks)
        assert len(report.results) == 1

    def test_run_auto_router_retrieval(self):
        adapter = MockAdapter(
            ranked_docs=[RankedDocument(doc_id="d0", score=0.9, rank=1)]
        )
        harness = ContextMemoryEvalHarness(adapter=adapter)
        tasks = [make_retrieval_task()]
        report = harness.run(tasks)
        assert len(report.results) >= 1

    def test_run_auto_router_memory(self):
        adapter = MockAdapter(
            memory_answer="Alice"
        )
        harness = ContextMemoryEvalHarness(adapter=adapter)
        tasks = [make_memory_task()]
        report = harness.run(tasks)
        assert len(report.results) >= 1

    def test_run_mixed_tasks(self):
        adapter = MockAdapter(
            ranked_docs=[RankedDocument(doc_id="d0", score=0.9, rank=1)],
            memory_answer="Alice",
        )
        harness = ContextMemoryEvalHarness(adapter=adapter)
        tasks = [make_retrieval_task(), make_memory_task()]
        report = harness.run(tasks)
        assert len(report.results) == 2

    def test_regression_mode_limits_samples(self):
        adapter = MockAdapter(
            memory_answer="Alice"
        )
        harness = ContextMemoryEvalHarness(adapter=adapter, mode=EvalMode.REGRESSION)
        tasks = [make_memory_task(f"mt{i}") for i in range(50)]
        report = harness.run(tasks)
        # REGRESSION mode caps at max_samples (default 20)
        assert len(report.results) <= 20

    def test_report_summary_not_empty(self):
        adapter = MockAdapter(
            memory_answer="Alice"
        )
        harness = ContextMemoryEvalHarness(adapter=adapter)
        tasks = [make_memory_task()]
        report = harness.run(tasks)
        summary = report.summary()
        assert isinstance(summary, dict)
        assert len(summary) > 0

    def test_report_to_dict(self):
        adapter = MockAdapter(
            memory_answer="Alice"
        )
        harness = ContextMemoryEvalHarness(adapter=adapter)
        report = harness.run([make_memory_task()])
        d = report.to_dict()
        assert "results" in d
