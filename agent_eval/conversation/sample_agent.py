"""示例：实现 DialogueAgent 的简单 Agent，用于本地测试与演示。"""

from __future__ import annotations

from agent_eval.conversation.models import ConversationTask, Transcript, Turn


class EchoAgent:
    """简单回显 Agent：将用户首条消息原样作为助手回复（单轮）。"""

    def run(self, task: ConversationTask) -> Transcript:
        turns = [
            Turn(role="user", content=task.initial_user_message),
            Turn(role="assistant", content=task.initial_user_message),
        ]
        return Transcript(
            task_id=task.task_id,
            trial_number=0,
            turns=turns,
        )


class FixedResponseAgent:
    """固定回复 Agent：对每条任务返回固定内容（可用于测试评估器）。"""

    def __init__(self, response: str = "这是固定回复。"):
        self.response = response

    def run(self, task: ConversationTask) -> Transcript:
        turns = [
            Turn(role="user", content=task.initial_user_message),
            Turn(role="assistant", content=self.response),
        ]
        return Transcript(
            task_id=task.task_id,
            trial_number=0,
            turns=turns,
        )


class CallableAgent:
    """通过可调用对象实现的 Agent：便于接入任意后端（如 OpenAI/Anthropic）。"""

    def __init__(self, fn):
        """
        Parameters
        ----------
        fn : callable
            签名 (task: ConversationTask) -> Transcript
        """
        self.fn = fn

    def run(self, task: ConversationTask) -> Transcript:
        return self.fn(task)
