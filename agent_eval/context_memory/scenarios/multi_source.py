"""UC001：多源上下文聚合评测场景。

评测系统从多个异质来源（数据库、文档、工具输出等）聚合上下文的能力。

对齐 UC：
- UC001：多源上下文聚合
- 外部 benchmark：LongBench v2（主）、BEIR（辅）

自建场景补充：外部 benchmark 无法覆盖"多源编排"逻辑，需自建验证：
- 多源文档是否都被利用
- 来源优先级是否正确
- 跨源信息冲突时是否合理处理
"""

from __future__ import annotations

from typing import List

from agent_eval.context_memory.models import ContextQualityTask, Document


def get_multi_source_tasks() -> List[ContextQualityTask]:
    """返回多源聚合场景的示例任务列表。

    每个任务提供来自多个来源的文档，要求系统能够整合所有来源回答问题。
    """
    return [
        ContextQualityTask(
            task_id="ms_001",
            question="根据数据库记录和用户文档，该用户的当前订阅计划是什么，最近有哪些操作？",
            gold_answer="Premium 计划，最近操作包括上传文件和更新个人信息",
            documents=[
                Document(
                    doc_id="db_record_001",
                    text="数据库记录：用户 ID=U001，订阅计划=Premium，到期日=2025-12-31，账户状态=活跃",
                    title="数据库记录",
                    metadata={"source": "database", "priority": 1},
                ),
                Document(
                    doc_id="op_log_001",
                    text="操作日志：2024-03-01 上传文件 report.pdf；2024-03-05 更新个人信息；2024-03-10 查看账单",
                    title="操作日志",
                    metadata={"source": "operation_log", "priority": 2},
                ),
                Document(
                    doc_id="user_doc_001",
                    text="用户上传的文档摘要：月度报告，包含 Q1 业务数据分析",
                    title="用户文档",
                    metadata={"source": "user_document", "priority": 3},
                ),
            ],
            metadata={
                "uc": "UC001",
                "scenario": "multi_source_aggregation",
                "expected_sources_utilized": ["database", "operation_log"],
            },
        ),
        ContextQualityTask(
            task_id="ms_002",
            question="综合工具调用结果和历史对话，当前任务的完成状态是什么？",
            gold_answer="任务已完成 80%，剩余步骤为代码审查和部署",
            documents=[
                Document(
                    doc_id="tool_output_001",
                    text="工具输出（代码检查）：已通过单元测试 45/50，覆盖率 82%，待处理警告 3 个",
                    title="工具调用结果",
                    metadata={"source": "tool_output"},
                ),
                Document(
                    doc_id="history_001",
                    text="历史对话：用户完成了需求分析、设计和编码阶段，尚未进行代码审查和部署",
                    title="历史上下文",
                    metadata={"source": "conversation_history"},
                ),
            ],
            metadata={
                "uc": "UC001",
                "scenario": "tool_context_aggregation",
            },
        ),
        ContextQualityTask(
            task_id="ms_003",
            question="来自多个来源的信息存在冲突：数据库显示用户在北京，但最新工具调用显示 IP 来自上海，请以最新信息为准回答用户当前位置。",
            gold_answer="根据最新信息，用户当前位置为上海",
            documents=[
                Document(
                    doc_id="db_location",
                    text="数据库：用户注册城市=北京，常驻地=北京",
                    title="数据库（旧数据）",
                    metadata={"source": "database", "timestamp": "2023-01-01", "priority": 2},
                ),
                Document(
                    doc_id="tool_location",
                    text="实时工具调用结果：IP 归属地=上海，时间=2024-03-12T18:00:00",
                    title="实时工具结果（新数据）",
                    metadata={"source": "realtime_tool", "timestamp": "2024-03-12", "priority": 1},
                ),
            ],
            metadata={
                "uc": "UC001",
                "scenario": "conflict_resolution",
                "expected_source": "realtime_tool",
            },
        ),
    ]
