"""Tests for context_memory data models."""

import pytest
from agent_eval.context_memory.models import (
    ContextMemoryEvalResult,
    ContextMemoryReport,
    ContextMode,
    ContextQualityResult,
    ContextQualityTask,
    Document,
    MemoryAnswer,
    MemoryTask,
    MemoryTaskType,
    MemoryTurn,
    MetricValue,
    RankedDocument,
    RetrievalResult,
    RetrievalTask,
)


class TestDocument:
    def test_basic_creation(self):
        doc = Document(doc_id="d1", text="hello world")
        assert doc.doc_id == "d1"
        assert doc.text == "hello world"
        assert doc.title == ""
        assert doc.metadata == {}

    def test_with_metadata(self):
        doc = Document(doc_id="d2", text="foo", title="Foo Title", metadata={"src": "wiki"})
        assert doc.title == "Foo Title"
        assert doc.metadata["src"] == "wiki"


class TestRankedDocument:
    def test_creation(self):
        rd = RankedDocument(doc_id="d1", score=0.9, rank=1)
        assert rd.rank == 1
        assert rd.score == pytest.approx(0.9)


class TestRetrievalTask:
    def test_creation(self):
        docs = [Document(doc_id=f"d{i}", text=f"text {i}") for i in range(3)]
        task = RetrievalTask(
            task_id="rt1",
            query="What is AI?",
            corpus=docs,
            relevant_doc_ids=["d0", "d2"],
        )
        assert task.task_id == "rt1"
        assert len(task.corpus) == 3
        assert "d0" in task.relevant_doc_ids


class TestMemoryTask:
    def test_creation(self):
        turns = [
            MemoryTurn(role="user", content="Hi"),
            MemoryTurn(role="assistant", content="Hello"),
        ]
        task = MemoryTask(
            task_id="mt1",
            session_id="s1",
            history=turns,
            question="What did the user say?",
            gold_answer="Hi",
            task_type=MemoryTaskType.QA,
        )
        assert task.task_id == "mt1"
        assert task.task_type == MemoryTaskType.QA
        assert task.should_abstain is False  # default

    def test_abstention_task(self):
        task = MemoryTask(
            task_id="mt2",
            session_id="s2",
            history=[],
            question="What is the secret?",
            gold_answer="",
            task_type=MemoryTaskType.ABSTENTION,
            should_abstain=True,
        )
        assert task.should_abstain is True


class TestContextQualityTask:
    def test_creation(self):
        task = ContextQualityTask(
            task_id="cq1",
            documents=["long doc 1", "long doc 2"],
            question="Summarize",
            gold_answer="Summary",
            budget_tokens=200,
            context_mode=ContextMode.COMPRESSED,
        )
        assert task.budget_tokens == 200
        assert task.context_mode == ContextMode.COMPRESSED


class TestMetricValue:
    def test_creation(self):
        mv = MetricValue(name="ndcg@10", value=0.75)
        assert mv.value == pytest.approx(0.75)


class TestContextMemoryEvalResult:
    def test_creation(self):
        metrics = [MetricValue(name="recall@10", value=0.8)]
        result = ContextMemoryEvalResult(
            task_id="t1",
            task_type="retrieval",
            passed=True,
            metrics=metrics,
        )
        assert result.passed is True
        assert result.task_type == "retrieval"

    def test_get_metric(self):
        metrics = [MetricValue(name="ndcg@10", value=0.75)]
        result = ContextMemoryEvalResult(task_id="t1", task_type="retrieval", passed=True, metrics=metrics)
        assert result.get_metric("ndcg@10") == pytest.approx(0.75)
        assert result.get_metric("missing") is None


class TestContextMemoryReport:
    def _make_results(self):
        return [
            ContextMemoryEvalResult(
                task_id=f"t{i}",
                task_type="memory",
                passed=i % 2 == 0,
                metrics=[MetricValue(name="qa_f1", value=float(i) / 4)],
            )
            for i in range(6)
        ]

    def test_summary_returns_dict(self):
        report = ContextMemoryReport(benchmark_name="test", results=self._make_results())
        summary = report.summary()
        assert isinstance(summary, dict)
        assert "benchmark" in summary or "total_tasks" in summary

    def test_to_dict(self):
        report = ContextMemoryReport(benchmark_name="beir", results=self._make_results())
        d = report.to_dict()
        assert "results" in d

    def test_pass_rate(self):
        results = self._make_results()
        report = ContextMemoryReport(benchmark_name="beir", results=results)
        # i=0,2,4 → 3 passed out of 6
        assert report.pass_rate == pytest.approx(0.5)

    def test_aggregate_metric(self):
        results = self._make_results()
        report = ContextMemoryReport(benchmark_name="beir", results=results)
        avg = report.aggregate_metric("qa_f1")
        assert avg is not None
        assert 0 <= avg <= 1.0
