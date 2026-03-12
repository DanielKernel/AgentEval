"""LoCoMo Benchmark Loader。

LoCoMo（Long-Context Conversation Memory）是专注于长对话记忆的 benchmark，
覆盖：
- 长对话 QA（跨多轮会话的记忆召回）
- 事件级摘要评估
- 会话型 QA

LoCoMo 是 LongMemEval 的补充件，强化 UC009（压缩/摘要）和 UC010（工作记忆）评测。

加载优先级：
1. 若已安装 ``datasets`` 库，从 HuggingFace 加载
2. 否则降级为本地 JSON/JSONL

参考：https://huggingface.co/datasets/snap-research/locomo
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from agent_eval.context_memory.loaders.base import BenchmarkLoader
from agent_eval.context_memory.models import MemoryTask, MemoryTaskType, MemoryTurn


class LoCoMoLoader(BenchmarkLoader):
    """LoCoMo dataset loader，输出 ``MemoryTask`` 列表。

    Parameters
    ----------
    hf_dataset_name:
        HuggingFace dataset 名称（默认 ``"snap-research/locomo"``）。
    data_dir:
        本地缓存目录。
    """

    def __init__(
        self,
        hf_dataset_name: str = "snap-research/locomo",
        data_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.hf_dataset_name = hf_dataset_name
        self.data_dir = Path(data_dir) if data_dir else Path.home() / ".cache" / "agent_eval" / "locomo"

    def load(
        self,
        split: str = "test",
        max_samples: Optional[int] = None,
        local_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> List[MemoryTask]:
        if local_path:
            raw = self.load_from_local(local_path, max_samples)
            return self._apply_limit(self._convert(raw), max_samples)

        if self._check_library("datasets"):
            try:
                return self._load_from_hf(split, max_samples)
            except Exception:
                pass

        local_file = self.data_dir / f"{split}.jsonl"
        if local_file.exists():
            raw = self.load_from_local(local_file, max_samples)
            return self._apply_limit(self._convert(raw), max_samples)

        raise RuntimeError(
            f"无法加载 LoCoMo 数据集。\n"
            f"请安装 datasets 库（pip install datasets）或将数据下载到 {local_file}。\n"
            f"本地格式（JSONL）：每行包含 id, question, answer, conversation 字段。"
        )

    def _load_from_hf(self, split: str, max_samples: Optional[int]) -> List[MemoryTask]:
        from datasets import load_dataset

        dataset = load_dataset(self.hf_dataset_name, split=split)
        return self._apply_limit(self._convert(list(dataset)), max_samples)

    def _convert(self, raw: List[Dict[str, Any]]) -> List[MemoryTask]:
        tasks: List[MemoryTask] = []
        for item in raw:
            conversation = item.get("conversation", []) or item.get("dialogue", [])
            history = self._parse_conversation(conversation)

            qa_list = item.get("qa", [])
            if isinstance(qa_list, list) and qa_list:
                for qa_item in qa_list:
                    q = qa_item.get("question", "")
                    a = qa_item.get("answer", "")
                    if not q:
                        continue
                    tasks.append(
                        MemoryTask(
                            task_id=str(item.get("id", f"locomo_{len(tasks)}")) + f"_{len(tasks)}",
                            session_id=str(item.get("id", f"session_{len(tasks)}")),
                            history=history,
                            question=q,
                            gold_answer=a,
                            task_type=MemoryTaskType.QA,
                            metadata={"source": "locomo"},
                        )
                    )
            else:
                question = item.get("question", "")
                if not question:
                    continue
                tasks.append(
                    MemoryTask(
                        task_id=str(item.get("id", f"locomo_{len(tasks)}")),
                        session_id=str(item.get("id", f"session_{len(tasks)}")),
                        history=history,
                        question=question,
                        gold_answer=item.get("answer", ""),
                        task_type=MemoryTaskType.QA,
                        metadata={"source": "locomo"},
                    )
                )
        return tasks

    @staticmethod
    def _parse_conversation(conversation: Any) -> List[MemoryTurn]:
        if not conversation:
            return []
        turns = []
        for item in conversation:
            if isinstance(item, dict):
                role = item.get("role", item.get("speaker", "user"))
                content = item.get("content", item.get("text", item.get("utterance", "")))
                turns.append(MemoryTurn(role=role, content=content))
            elif isinstance(item, str):
                turns.append(MemoryTurn(role="user", content=item))
        return turns
