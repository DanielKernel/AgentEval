"""LongBench v2 Benchmark Loader。

LongBench v2 评测长上下文理解与压缩后的保真能力，覆盖：
- single_doc_qa：单文档 QA
- multi_doc_qa：多文档 QA
- few_shot_learning：长对话历史理解
- long_in_context_learning：长结构化数据理解
- code_repo：代码仓库理解

加载优先级：
1. 若已安装 ``datasets`` 库，从 HuggingFace 加载
2. 否则降级为本地 JSON/JSONL

参考：https://huggingface.co/datasets/THUDM/LongBench
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from agent_eval.context_memory.loaders.base import BenchmarkLoader
from agent_eval.context_memory.models import (
    ContextMode,
    ContextQualityTask,
    Document,
)

_LONGBENCH_DOMAINS = [
    "single_doc_qa",
    "multi_doc_qa",
    "few_shot_learning",
    "long_in_context_learning",
    "code_repo",
]


class LongBenchLoader(BenchmarkLoader):
    """LongBench v2 dataset loader，输出 ``ContextQualityTask`` 列表。

    Parameters
    ----------
    hf_dataset_name:
        HuggingFace dataset 名称（默认 ``"THUDM/LongBench"``）。
    domains:
        过滤指定任务领域（默认加载全部）。
    context_mode:
        评测上下文模式（RAW / COMPRESSED / RETRIEVED），影响 task 的 context_mode 字段。
    data_dir:
        本地缓存目录。
    """

    def __init__(
        self,
        hf_dataset_name: str = "THUDM/LongBench",
        domains: Optional[List[str]] = None,
        context_mode: ContextMode = ContextMode.RAW,
        data_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.hf_dataset_name = hf_dataset_name
        self.domains = set(domains) if domains else None
        self.context_mode = context_mode
        self.data_dir = Path(data_dir) if data_dir else Path.home() / ".cache" / "agent_eval" / "longbench"

    def load(
        self,
        split: str = "test",
        max_samples: Optional[int] = None,
        local_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> List[ContextQualityTask]:
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
            f"无法加载 LongBench v2 数据集。\n"
            f"请安装 datasets 库（pip install datasets）或将数据下载到 {local_file}。\n"
            f"本地格式（JSONL）：每行包含 _id, input, answers, context, type 字段。"
        )

    def _load_from_hf(self, split: str, max_samples: Optional[int]) -> List[ContextQualityTask]:
        from datasets import load_dataset

        all_tasks: List[ContextQualityTask] = []
        subsets = list(self.domains) if self.domains else _LONGBENCH_DOMAINS
        for domain in subsets:
            try:
                dataset = load_dataset(self.hf_dataset_name, domain, split=split)
                tasks = self._convert(list(dataset), domain=domain)
                all_tasks.extend(tasks)
                if max_samples and len(all_tasks) >= max_samples:
                    break
            except Exception:
                continue
        return self._apply_limit(all_tasks, max_samples)

    def _convert(
        self,
        raw: List[Dict[str, Any]],
        domain: str = "",
    ) -> List[ContextQualityTask]:
        tasks: List[ContextQualityTask] = []
        for item in raw:
            if self.domains and domain and domain not in self.domains:
                continue

            context_text = item.get("context", "") or item.get("input", "")
            question = item.get("input", "") or item.get("question", "")
            if not question and context_text:
                parts = context_text.split("\n\n", 1)
                question = parts[0] if len(parts) == 1 else parts[-1][:200]

            answers = item.get("answers", []) or item.get("answer", [])
            if isinstance(answers, str):
                answers = [answers]
            gold_answer = answers[0] if answers else ""

            doc = Document(
                doc_id=str(item.get("_id", f"lb_{len(tasks)}")),
                text=context_text,
            )
            item_domain = item.get("type", domain or "unknown")

            tasks.append(
                ContextQualityTask(
                    task_id=str(item.get("_id", f"lb_{len(tasks)}")),
                    question=question,
                    gold_answer=gold_answer,
                    documents=[doc],
                    context_mode=self.context_mode,
                    domain=item_domain,
                    metadata={"all_answers": answers},
                )
            )
        return tasks
