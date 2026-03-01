"""对话类 Agent 评测模块的单元测试。"""

from __future__ import annotations

import pytest

from agent_eval.conversation import (
    ConversationEvalHarness,
    ConversationTask,
    KeywordGrader,
    MaxTurnsGrader,
    RegexGrader,
    StringMatchGrader,
    Transcript,
    Turn,
    pass_at_k,
    pass_k,
)
from agent_eval.conversation.sample_agent import EchoAgent, FixedResponseAgent


# ---------------------------------------------------------------------------
# pass@k / pass^k
# ---------------------------------------------------------------------------

def test_pass_at_k_all_success():
    assert pass_at_k(5, 1, [True] * 5) == 1.0
    assert pass_at_k(3, 2, [True, True, True]) == 1.0


def test_pass_at_k_no_success():
    assert pass_at_k(5, 1, [False] * 5) == 0.0


def test_pass_at_k_partial():
    # 3 次中 2 次成功，k=1 -> 1 - C(1,1)/C(3,1) = 2/3
    assert abs(pass_at_k(3, 1, [True, True, False]) - 2/3) < 1e-9


def test_pass_k_consistency():
    assert pass_k(3, 3, [True, True, True]) > 0
    assert pass_k(3, 3, [False, False, False]) == 0.0


# ---------------------------------------------------------------------------
# Transcript
# ---------------------------------------------------------------------------

def test_transcript_last_assistant():
    t = Transcript(
        task_id="x",
        trial_number=0,
        turns=[
            Turn("user", "hi"),
            Turn("assistant", "first"),
            Turn("user", "again"),
            Turn("assistant", "second"),
        ],
    )
    assert t.get_last_assistant_turn() == "second"
    assert t.get_assistant_text() == "first\nsecond"
    assert t.turn_count() == 4


# ---------------------------------------------------------------------------
# Graders
# ---------------------------------------------------------------------------

def test_string_match_grader():
    g = StringMatchGrader(expected_key="expected_outcome")
    task = ConversationTask("t1", "hello", expected_outcome="hello")
    t = Transcript("t1", 0, turns=[Turn("user", "hello"), Turn("assistant", "hello")])
    r = g.grade(t, None, {"task": task})
    assert r.passed is True
    assert r.score == 1.0

    t2 = Transcript("t1", 0, turns=[Turn("assistant", "hi")])
    r2 = g.grade(t2, None, {"task": task})
    assert r2.passed is False


def test_regex_grader():
    g = RegexGrader(pattern=r"\d+")
    t = Transcript("t1", 0, turns=[Turn("assistant", "the answer is 42")])
    r = g.grade(t, None, {})
    assert r.passed is True
    assert r.score == 1.0

    t2 = Transcript("t1", 0, turns=[Turn("assistant", "no numbers")])
    r2 = g.grade(t2, None, {})
    assert r2.passed is False


def test_keyword_grader():
    g = KeywordGrader(keywords=["北京", "天气"], require_all=True)
    t = Transcript("t1", 0, turns=[Turn("assistant", "北京今天天气不错")])
    r = g.grade(t, None, {})
    assert r.passed is True
    assert r.score == 1.0

    g2 = KeywordGrader(keywords=["a", "b"], require_all=False)
    t2 = Transcript("t1", 0, turns=[Turn("assistant", "only a")])
    r2 = g2.grade(t2, None, {})
    assert r2.passed is True
    assert r2.score == 0.5


def test_max_turns_grader():
    g = MaxTurnsGrader(max_turns=5)
    t = Transcript("t1", 0, turns=[Turn("user", "x"), Turn("assistant", "y")])
    r = g.grade(t, None, {})
    assert r.passed is True

    t2 = Transcript("t1", 0, turns=[Turn("user", str(i)) for i in range(12)])
    r2 = g.grade(t2, None, {})
    assert r2.passed is False


# ---------------------------------------------------------------------------
# Harness + EchoAgent
# ---------------------------------------------------------------------------

def test_harness_echo_agent():
    task = ConversationTask(
        task_id="t1",
        initial_user_message="你好",
        expected_outcome="你好",
        max_turns=10,
    )
    graders = [StringMatchGrader(), MaxTurnsGrader(max_turns=10)]
    harness = ConversationEvalHarness(
        agent=EchoAgent(),
        graders=graders,
        n_trials=2,
        seed=42,
    )
    results = harness.run_evaluation([task])
    assert len(results) == 1
    r = results[0]
    assert r.task_id == "t1"
    assert len(r.trials) == 2
    assert r.n_passed == 2
    assert r.pass_at_1 == 1.0
    summary = harness.summary(results)
    assert summary["total_tasks"] == 1
    assert summary["total_trials"] == 2
    assert summary["overall_pass_rate"] == 1.0


def test_harness_fixed_agent_fail():
    task = ConversationTask(
        task_id="t1",
        initial_user_message="你好",
        expected_outcome="你好",
        max_turns=10,
    )
    graders = [StringMatchGrader()]
    harness = ConversationEvalHarness(
        agent=FixedResponseAgent("固定回复"),
        graders=graders,
        n_trials=2,
        seed=42,
    )
    results = harness.run_evaluation([task])
    r = results[0]
    assert r.n_passed == 0
    assert r.pass_at_1 == 0.0
