"""UC011：工具上下文治理评测场景（自建）。

评测系统正确管理工具调用上下文的能力：
- 工具输出是否被正确注入上下文
- 工具上下文是否在适当时机清理（不污染后续对话）
- 工具调用失败时上下文的降级处理

对齐 UC：
- UC011：工具上下文治理
- 外部 benchmark 基本无法覆盖，**以自建为主**
"""

from __future__ import annotations

from typing import List

from agent_eval.context_memory.models import MemoryTask, MemoryTaskType, MemoryTurn


def get_tool_context_tasks() -> List[MemoryTask]:
    """返回工具上下文治理场景的示例任务列表。"""
    return [
        MemoryTask(
            task_id="tool_ctx_001",
            session_id="session_tool_001",
            history=[
                MemoryTurn(role="user", content="查询今天上海的天气"),
                MemoryTurn(
                    role="assistant",
                    content="[工具调用: weather_api(city=上海)] 结果：晴，25°C，东南风 3 级",
                    metadata={"tool_call": "weather_api", "tool_result": "晴，25°C，东南风3级"},
                ),
                MemoryTurn(role="assistant", content="今天上海天气晴，气温 25°C，东南风 3 级，适合外出。"),
            ],
            question="根据工具调用结果，今天上海的气温是多少？",
            gold_answer="25°C",
            task_type=MemoryTaskType.QA,
            metadata={
                "uc": "UC011",
                "scenario": "tool_output_injection",
                "tool_name": "weather_api",
            },
        ),
        MemoryTask(
            task_id="tool_ctx_002",
            session_id="session_tool_002",
            history=[
                MemoryTurn(role="user", content="查询 A 股票价格"),
                MemoryTurn(
                    role="assistant",
                    content="[工具调用: stock_api(symbol=A)] 结果：100 元",
                    metadata={"tool_call": "stock_api", "tool_result": "100元"},
                ),
                MemoryTurn(role="assistant", content="A 股票当前价格为 100 元。"),
                MemoryTurn(role="user", content="现在查询 B 股票"),
                MemoryTurn(
                    role="assistant",
                    content="[工具调用: stock_api(symbol=B)] 结果：200 元",
                    metadata={"tool_call": "stock_api", "tool_result": "200元"},
                ),
                MemoryTurn(role="assistant", content="B 股票当前价格为 200 元。"),
            ],
            question="B 股票的价格是多少？不要混淆 A 股票的信息。",
            gold_answer="200 元",
            task_type=MemoryTaskType.QA,
            metadata={
                "uc": "UC011",
                "scenario": "tool_context_isolation",
                "expected_behavior": "返回 B 股票价格，不被 A 股票数据干扰",
            },
        ),
        MemoryTask(
            task_id="tool_ctx_003",
            session_id="session_tool_003",
            history=[
                MemoryTurn(role="user", content="查询订单 ORD-999 的状态"),
                MemoryTurn(
                    role="assistant",
                    content="[工具调用: order_api(order_id=ORD-999)] 结果：ERROR - 订单不存在",
                    metadata={"tool_call": "order_api", "tool_result": "ERROR", "error": "订单不存在"},
                ),
            ],
            question="订单 ORD-999 的状态是什么？",
            gold_answer="",
            task_type=MemoryTaskType.ABSTENTION,
            should_abstain=True,
            metadata={
                "uc": "UC011",
                "scenario": "tool_failure_graceful_degradation",
                "expected_behavior": "告知用户订单不存在，不捏造状态信息",
            },
        ),
        MemoryTask(
            task_id="tool_ctx_004",
            session_id="session_tool_004",
            history=[
                MemoryTurn(role="user", content="帮我查一下会议室占用情况"),
                MemoryTurn(
                    role="assistant",
                    content="[工具调用: calendar_api] 结果：会议室 A 今天 14:00-16:00 占用，其他时段空闲",
                    metadata={"tool_call": "calendar_api"},
                ),
                MemoryTurn(role="assistant", content="会议室 A 今天 14-16 点已占用，其余时段空闲。"),
                MemoryTurn(role="user", content="好的，谢谢。顺便问一下，你喜欢什么颜色？"),
                MemoryTurn(role="assistant", content="作为 AI 助手，我没有颜色偏好。还有什么可以帮您？"),
            ],
            question="会议室 A 今天被占用的时段是？",
            gold_answer="14:00-16:00",
            task_type=MemoryTaskType.QA,
            metadata={
                "uc": "UC011",
                "scenario": "tool_context_persistence",
                "expected_behavior": "工具调用结果在后续对话中仍可正确召回",
            },
        ),
    ]
