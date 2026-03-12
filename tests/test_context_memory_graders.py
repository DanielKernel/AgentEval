"""Tests for context_memory graders (zero external deps)."""

import pytest
from agent_eval.context_memory.graders.retrieval import (
    MRRGrader,
    NDCGGrader,
    RecallAtKGrader,
    RetrievalSuiteGrader,
    ndcg_at_k,
    recall_at_k,
    mrr,
)
from agent_eval.context_memory.graders.memory import (
    AbstentionGrader,
    KnowledgeUpdateGrader,
    MemorySuiteGrader,
    QAAccuracyGrader,
    TemporalReasoningGrader,
)
from agent_eval.context_memory.graders.context import (
    CompressionFidelityGrader,
    ContextQualitySuiteGrader,
    MultiDocUtilizationGrader,
    TokenEfficiencyGrader,
)
from agent_eval.context_memory.graders.degradation import (
    LengthDegradationGrader,
    LengthDegradationPoint,
)
from agent_eval.context_memory.models import (
    ContextQualityResult,
    ContextQualityTask,
    ContextMode,
    MemoryAnswer,
    MemoryTask,
    MemoryTaskType,
    MemoryTurn,
    RankedDocument,
    RetrievalResult,
    RetrievalTask,
    Document,
)


# ── Retrieval grader helpers ────────────────────────────────────────────────

def _make_task(relevant_ids):
    corpus = [Document(doc_id=f"d{i}", text=f"t{i}") for i in range(5)]
    return RetrievalTask(
        task_id="t1", query="q", corpus=corpus, relevant_doc_ids=list(relevant_ids),
        relevance_scores={d: 1 for d in relevant_ids},
    )


def _make_ranked(doc_ids):
    return [RankedDocument(doc_id=d, score=1.0 - i * 0.1, rank=i + 1) for i, d in enumerate(doc_ids)]


class TestNDCGAtK:
    def test_perfect_ranking(self):
        task = _make_task(["d1", "d2", "d3"])
        ranked = _make_ranked(["d1", "d2", "d3"])
        score = ndcg_at_k(task, ranked, k=3)
        assert score == pytest.approx(1.0, abs=1e-4)

    def test_no_relevant(self):
        task = _make_task(["d0"])
        ranked = _make_ranked(["d1", "d2"])
        score = ndcg_at_k(task, ranked, k=2)
        assert score == pytest.approx(0.0)

    def test_partial_ranking(self):
        task = _make_task(["d1"])
        ranked = _make_ranked(["d2", "d1"])
        score = ndcg_at_k(task, ranked, k=2)
        assert 0 < score < 1.0

    def test_empty_ranked(self):
        task = _make_task(["d1"])
        assert ndcg_at_k(task, [], k=10) == pytest.approx(0.0)


class TestRecallAtK:
    def test_full_recall(self):
        task = _make_task(["d1", "d2"])
        ranked = _make_ranked(["d1", "d2", "d3"])
        assert recall_at_k(task, ranked, k=3) == pytest.approx(1.0)

    def test_zero_recall(self):
        task = _make_task(["d1", "d2"])
        ranked = _make_ranked(["d3", "d4"])
        assert recall_at_k(task, ranked, k=2) == pytest.approx(0.0)

    def test_partial_recall(self):
        task = _make_task(["d1", "d2"])
        ranked = _make_ranked(["d1", "d4"])
        assert recall_at_k(task, ranked, k=2) == pytest.approx(0.5)

    def test_empty_relevant(self):
        task = _make_task([])
        ranked = _make_ranked(["d1"])
        assert recall_at_k(task, ranked, k=10) == pytest.approx(0.0)


class TestMRR:
    def test_first_hit(self):
        task = _make_task(["d1"])
        ranked = _make_ranked(["d1", "d2"])
        assert mrr(task, ranked) == pytest.approx(1.0)

    def test_second_hit(self):
        task = _make_task(["d1"])
        ranked = _make_ranked(["d2", "d1"])
        assert mrr(task, ranked) == pytest.approx(0.5)

    def test_no_hit(self):
        task = _make_task(["d1"])
        ranked = _make_ranked(["d3", "d4"])
        assert mrr(task, ranked) == pytest.approx(0.0)


class TestRetrievalSuiteGrader:
    def _make_task_result(self, ranked_ids, relevant_ids):
        corpus = [Document(doc_id=d, text="x") for d in {"d1", "d2", "d3", "d4", "d5"}]
        task = RetrievalTask(
            task_id="t1", query="q", corpus=corpus, relevant_doc_ids=relevant_ids
        )
        ranked = [RankedDocument(doc_id=d, score=1.0 - i * 0.1, rank=i + 1) for i, d in enumerate(ranked_ids)]
        result = RetrievalResult(task_id="t1", ranked_docs=ranked)
        return task, result

    def test_perfect_score(self):
        task, result = self._make_task_result(["d1", "d2"], ["d1", "d2"])
        grader = RetrievalSuiteGrader(k=2, ndcg_threshold=0.5, recall_threshold=0.5, mrr_threshold=0.5)
        eval_result = grader.grade(task, result)
        assert eval_result.passed is True

    def test_zero_score(self):
        task, result = self._make_task_result(["d3", "d4"], ["d1", "d2"])
        grader = RetrievalSuiteGrader(k=2, ndcg_threshold=0.5, recall_threshold=0.5, mrr_threshold=0.5)
        eval_result = grader.grade(task, result)
        assert eval_result.passed is False


# ── Memory graders ───────────────────────────────────────────────────────────

class TestQAAccuracyGrader:
    def _make_task_answer(self, gold, predicted, task_type=MemoryTaskType.QA):
        task = MemoryTask(
            task_id="m1", session_id="s1", history=[],
            question="Q?", gold_answer=gold, task_type=task_type,
        )
        answer = MemoryAnswer(task_id="m1", answer=predicted)
        return task, answer

    def test_exact_match(self):
        task, answer = self._make_task_answer("Paris", "Paris")
        grader = QAAccuracyGrader()
        result = grader.grade(task, answer)
        assert result.passed is True
        assert result.get_metric("token_f1") == pytest.approx(1.0)

    def test_case_insensitive(self):
        task, answer = self._make_task_answer("Paris", "paris")
        grader = QAAccuracyGrader()
        result = grader.grade(task, answer)
        assert result.passed is True

    def test_partial_f1(self):
        task, answer = self._make_task_answer("the quick brown fox", "the fox")
        grader = QAAccuracyGrader(passing_threshold=0.3)
        result = grader.grade(task, answer)
        f1 = result.get_metric("token_f1")
        assert f1 is not None and 0 < f1 < 1.0

    def test_wrong_answer(self):
        task, answer = self._make_task_answer("Paris", "London")
        grader = QAAccuracyGrader()
        result = grader.grade(task, answer)
        assert result.get_metric("token_f1") == pytest.approx(0.0)


class TestAbstentionGrader:
    def _make_task_answer(self, should_abstain, predicted):
        task = MemoryTask(
            task_id="a1", session_id="s1", history=[],
            question="Q?", gold_answer="", task_type=MemoryTaskType.ABSTENTION,
            should_abstain=should_abstain,
        )
        answer = MemoryAnswer(task_id="a1", answer=predicted)
        return task, answer

    def test_correct_abstention(self):
        task, answer = self._make_task_answer(True, "I don't know the answer to that.")
        grader = AbstentionGrader()
        result = grader.grade(task, answer)
        assert result.passed is True

    def test_wrong_abstention(self):
        task, answer = self._make_task_answer(True, "The answer is definitely Paris.")
        grader = AbstentionGrader()
        result = grader.grade(task, answer)
        assert result.passed is False

    def test_should_answer(self):
        task, answer = self._make_task_answer(False, "The answer is Paris.")
        grader = AbstentionGrader()
        result = grader.grade(task, answer)
        assert result.passed is True


class TestMemorySuiteGrader:
    def test_dispatches_by_task_type(self):
        task = MemoryTask(
            task_id="m1", session_id="s1", history=[],
            question="Q?", gold_answer="Paris", task_type=MemoryTaskType.QA,
        )
        answer = MemoryAnswer(task_id="m1", answer="Paris")
        grader = MemorySuiteGrader()
        result = grader.grade(task, answer)
        assert result.get_metric("token_f1") == pytest.approx(1.0)


# ── Context quality graders ──────────────────────────────────────────────────

class TestCompressionFidelityGrader:
    def _make_task(self, gold_answer):
        return ContextQualityTask(
            task_id="c1", documents=["doc text"],
            question="Q?", gold_answer=gold_answer,
            budget_tokens=100, context_mode=ContextMode.COMPRESSED,
        )

    def _make_result(self, answer, context="ctx", tokens=None):
        return ContextQualityResult(task_id="c1", answer=answer, context_used=context, tokens_used=tokens)

    def test_high_fidelity(self):
        task = self._make_task("Paris is the capital")
        raw = self._make_result("Paris is the capital")
        compressed = self._make_result("Paris is the capital")
        grader = CompressionFidelityGrader(passing_threshold=0.2)
        eval_result = grader.grade(task, raw, compressed)
        assert eval_result.passed is True

    def test_low_fidelity(self):
        task = self._make_task("Paris is the capital")
        raw = self._make_result("Paris is the capital")
        compressed = self._make_result("London is great")
        grader = CompressionFidelityGrader(passing_threshold=0.1)
        eval_result = grader.grade(task, raw, compressed)
        assert eval_result.passed is False


class TestTokenEfficiencyGrader:
    def test_compression_ratio(self):
        task = ContextQualityTask(
            task_id="c2", documents=["a " * 100],
            question="Q?", gold_answer="answer",
            budget_tokens=50, context_mode=ContextMode.COMPRESSED,
        )
        compressed = ContextQualityResult(task_id="c2", answer="answer", context_used="a " * 50, tokens_used=100)
        grader = TokenEfficiencyGrader(baseline_tokens=200, target_token_budget=150)
        eval_result = grader.grade(task, compressed)
        metrics = {m.name: m.value for m in eval_result.metrics}
        assert "tokens_used" in metrics
        assert "token_savings_ratio" in metrics


# ── Degradation grader ───────────────────────────────────────────────────────

def _make_cq_task_result(task_id, gold_answer, predicted_answer, context_len):
    task = ContextQualityTask(
        task_id=task_id, documents=["x " * context_len],
        question="Q?", gold_answer=gold_answer,
        budget_tokens=context_len, context_mode=ContextMode.COMPRESSED,
    )
    result = ContextQualityResult(task_id=task_id, answer=predicted_answer)
    return task, result


class TestLengthDegradationGrader:
    def test_no_degradation(self):
        grader = LengthDegradationGrader()
        for i, (length, answer) in enumerate([(100, "Paris"), (500, "Paris"), (1000, "Paris")]):
            task, result = _make_cq_task_result(f"t{i}", "Paris", answer, length)
            grader.record(task, result, length)
        analysis = grader.analyze()
        assert "degradation_slope" in analysis
        assert "mean_accuracy" in analysis

    def test_strong_degradation(self):
        grader = LengthDegradationGrader(passing_accuracy_threshold=0.5)
        answers = [("Paris", 100), ("Paris", 500), ("London", 1000), ("Berlin", 2000)]
        for i, (ans, length) in enumerate(answers):
            task, result = _make_cq_task_result(f"t{i}", "Paris", ans, length)
            grader.record(task, result, length)
        analysis = grader.analyze()
        slope = analysis.get("degradation_slope")
        assert slope is not None
        assert slope < 0  # accuracy drops as length increases

    def test_reset(self):
        grader = LengthDegradationGrader()
        task, result = _make_cq_task_result("t1", "Paris", "Paris", 100)
        grader.record(task, result, 100)
        grader.reset()
        assert len(grader._data_points) == 0

    def test_insufficient_data(self):
        grader = LengthDegradationGrader()
        analysis = grader.analyze()
        assert analysis["degradation_slope"] is None
