"""对话 Agent 协议：任意对话类 Agent 需实现的接口。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from agent_eval.conversation.models import ConversationTask, Transcript, Turn


@runtime_checkable
class DialogueAgent(Protocol):
    """对话类 Agent 协议。

    实现此接口的 Agent 可被评测框架驱动：给定任务，在 max_turns 内多轮对话，
    返回完整转录记录（Transcript）。
    """

    def run(self, task: ConversationTask) -> Transcript:
        """执行任务并返回完整转录记录。

        Parameters
        ----------
        task : ConversationTask
            评测任务（含初始用户消息与 max_turns 等）。

        Returns
        -------
        Transcript
            多轮对话的完整记录，至少包含 initial_user_message 对应的 user 轮与助手的回复。
        """
        ...


def run_agent_simple(
    agent: DialogueAgent,
    task: ConversationTask,
) -> Transcript:
    """调用任意实现 DialogueAgent 协议的对象执行任务。"""
    return agent.run(task)
