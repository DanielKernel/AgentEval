"""UC009：上下文压缩与摘要评测场景。

评测系统对长上下文进行压缩/摘要后，是否保留了关键信息。

对齐 UC：
- UC009：上下文压缩与摘要
- 外部 benchmark：LongBench v2（主）、LoCoMo（辅）
"""

from __future__ import annotations

from typing import List

from agent_eval.context_memory.models import ContextMode, ContextQualityTask, Document


def get_compression_tasks() -> List[ContextQualityTask]:
    """返回上下文压缩/摘要场景的示例任务列表。"""
    return [
        ContextQualityTask(
            task_id="compress_001",
            question="根据本次会议记录，主要讨论了哪三个议题，各自的决策结论是什么？",
            gold_answer="议题一：产品路线图，决定 Q2 发布 v2.0；议题二：人员扩招，批准招聘 5 名工程师；议题三：预算调整，Q2 增加 20% 研发投入",
            documents=[
                Document(
                    doc_id="meeting_001",
                    text=(
                        "会议记录（2024-03-12 14:00-16:00）\n\n"
                        "参会人员：张总、李总监、王经理、陈工、刘工\n\n"
                        "议题一：产品路线图规划\n"
                        "讨论了 v2.0 版本的核心功能，包括 AI 助手集成、多模态支持、性能优化三大方向。"
                        "评估了技术可行性和市场需求。最终决策：Q2（4月底）发布 v2.0，"
                        "重点功能为 AI 助手集成，其他功能延至 v2.1。\n\n"
                        "议题二：Q2 人员扩招计划\n"
                        "HR 汇报了当前团队缺口：后端工程师 3 名、前端工程师 1 名、AI 算法工程师 1 名。"
                        "讨论了招聘渠道和时间线。最终决策：批准招聘 5 名工程师，6 月底前到岗。\n\n"
                        "议题三：Q2 预算调整\n"
                        "财务汇报了 Q1 实际支出与预算偏差。讨论了 Q2 研发投入的必要性。"
                        "最终决策：Q2 研发预算较 Q1 增加 20%，主要用于人力成本和云服务。\n\n"
                        "其他事项：下次会议时间定为 4 月 15 日。"
                    ),
                    title="会议记录",
                )
            ],
            context_mode=ContextMode.COMPRESSED,
            budget_tokens=200,
            domain="meeting_summarization",
            metadata={"uc": "UC009", "scenario": "meeting_compression"},
        ),
        ContextQualityTask(
            task_id="compress_002",
            question="该代码文件的主要功能是什么，包含哪些核心类？",
            gold_answer="实现了用户认证模块，包含 UserAuthenticator、TokenManager、SessionStore 三个核心类",
            documents=[
                Document(
                    doc_id="code_001",
                    text=(
                        "# user_auth.py\n"
                        "# 用户认证模块 - 负责处理用户登录、令牌管理和会话存储\n\n"
                        "import hashlib\nimport jwt\nfrom datetime import datetime, timedelta\n\n"
                        "class UserAuthenticator:\n"
                        "    \"\"\"核心认证类：验证用户凭据\"\"\"\n"
                        "    def authenticate(self, username, password): ...\n"
                        "    def verify_mfa(self, user_id, code): ...\n\n"
                        "class TokenManager:\n"
                        "    \"\"\"JWT 令牌管理：生成和验证令牌\"\"\"\n"
                        "    def generate_token(self, user_id, expires_in=3600): ...\n"
                        "    def validate_token(self, token): ...\n"
                        "    def refresh_token(self, refresh_token): ...\n\n"
                        "class SessionStore:\n"
                        "    \"\"\"会话存储：管理活跃会话\"\"\"\n"
                        "    def create_session(self, user_id): ...\n"
                        "    def get_session(self, session_id): ...\n"
                        "    def invalidate_session(self, session_id): ...\n\n"
                        "# 辅助函数\ndef hash_password(password): ...\n"
                        "def generate_salt(): ...\n"
                    ),
                    title="用户认证模块",
                )
            ],
            context_mode=ContextMode.COMPRESSED,
            budget_tokens=100,
            domain="code_summarization",
            metadata={"uc": "UC009", "scenario": "code_compression"},
        ),
    ]
