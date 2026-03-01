"""数据模型：对话类 Agent 评测（基于 Anthropic Demystifying evals 文档）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Turn:
    """单轮对话：用户或助手的一条消息。"""

    role: str  # "user" | "assistant" | "system"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transcript:
    """试验的完整转录记录（Transcript）：所有轮次的输入输出与可选元数据。"""

    task_id: str
    trial_number: int
    turns: List[Turn] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_assistant_text(self) -> str:
        """拼接所有助手回复文本，用于基于输出的评估器。"""
        return "\n".join(
            t.content for t in self.turns if t.role == "assistant"
        ).strip()

    def get_last_assistant_turn(self) -> Optional[str]:
        """最后一条助手回复。"""
        for t in reversed(self.turns):
            if t.role == "assistant":
                return t.content
        return None

    def turn_count(self) -> int:
        return len(self.turns)


@dataclass
class ConversationTask:
    """单个对话评测任务（Task）：输入与成功标准。"""

    task_id: str
    initial_user_message: str
    expected_outcome: Optional[str] = None
    success_criteria: Optional[Dict[str, Any]] = None
    max_turns: int = 20
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Assertion:
    """评估器的一条断言。"""

    description: str
    passed: bool
    evidence: str = ""


@dataclass
class GradingResult:
    """单个评估器（Grader）的评分结果。"""

    grader_name: str
    passed: bool
    score: float
    assertions: List[Assertion] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrialResult:
    """单次试验（Trial）的结果：转录 + 各评估器评分 + 是否通过。"""

    task_id: str
    trial_number: int
    transcript: Transcript
    grades: Dict[str, GradingResult] = field(default_factory=dict)
    passed: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "trial_number": self.trial_number,
            "passed": self.passed,
            "error": self.error,
            "grades": {
                name: {
                    "passed": g.passed,
                    "score": g.score,
                    "assertions": [
                        {"description": a.description, "passed": a.passed, "evidence": a.evidence}
                        for a in g.assertions
                    ],
                }
                for name, g in self.grades.items()
            },
            "transcript_turn_count": self.transcript.turn_count(),
        }
