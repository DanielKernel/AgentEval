"""BEIR Benchmark Loader。

BEIR（Benchmarking IR）是检索 / RAG 领域最常见的零样本评测基准，
包含 18 个异质检索数据集（如 nfcorpus、scifact、fiqa、msmarco 等）。

加载优先级：
1. 若已安装 ``beir`` 库，从 BeIR GitHub 自动下载
2. 否则降级为本地 BEIR 格式 JSON/JSONL

参考：https://github.com/beir-cellar/beir
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from agent_eval.context_memory.loaders.base import BenchmarkLoader
from agent_eval.context_memory.models import Document, RetrievalTask


class BEIRLoader(BenchmarkLoader):
    """BEIR dataset loader，输出 ``RetrievalTask`` 列表。

    Parameters
    ----------
    dataset:
        BEIR 数据集名称，如 ``"nfcorpus"``、``"scifact"``、``"fiqa"``、``"msmarco"``。
    data_dir:
        本地缓存 / 降级数据目录（默认 ``~/.cache/agent_eval/beir``）。
    """

    BEIR_DATASETS = [
        "msmarco", "trec-covid", "nfcorpus", "nq", "hotpotqa", "fiqa",
        "arguana", "touche-2020", "dbpedia-entity", "scidocs", "fever",
        "climate-fever", "scifact", "robust04", "signal1m", "news-21",
        "bioasq", "trec-news",
    ]

    def __init__(
        self,
        dataset: str = "nfcorpus",
        data_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.dataset = dataset
        self.data_dir = Path(data_dir) if data_dir else Path.home() / ".cache" / "agent_eval" / "beir"

    def load(
        self,
        split: str = "test",
        max_samples: Optional[int] = None,
        local_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> List[RetrievalTask]:
        """加载 BEIR 数据集，返回 RetrievalTask 列表。"""
        if local_path:
            return self._load_from_local_beir(local_path, split, max_samples)

        if self._check_library("beir"):
            try:
                return self._load_from_beir_lib(split, max_samples)
            except Exception:
                pass

        dataset_dir = self.data_dir / self.dataset
        if dataset_dir.exists():
            return self._load_from_local_beir(dataset_dir, split, max_samples)

        raise RuntimeError(
            f"无法加载 BEIR 数据集 '{self.dataset}'。\n"
            f"请安装 beir 库（pip install beir）或将数据下载到 {dataset_dir}。\n"
            f"本地格式：corpus.jsonl + queries.jsonl + qrels/{split}.tsv"
        )

    def _load_from_beir_lib(
        self, split: str, max_samples: Optional[int]
    ) -> List[RetrievalTask]:
        from beir import util
        from beir.datasets.data_loader import GenericDataLoader

        url = f"https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/{self.dataset}.zip"
        data_path = util.download_and_unzip(url, str(self.data_dir))
        corpus, queries, qrels = GenericDataLoader(data_folder=data_path).load(split=split)
        return self._convert(corpus, queries, qrels, max_samples)

    def _load_from_local_beir(
        self,
        directory: Union[str, Path],
        split: str,
        max_samples: Optional[int],
    ) -> List[RetrievalTask]:
        """从本地 BEIR 格式目录加载（corpus.jsonl + queries.jsonl + qrels/{split}.tsv）。"""
        directory = Path(directory)

        corpus: Dict[str, Dict[str, str]] = {}
        corpus_file = directory / "corpus.jsonl"
        if corpus_file.exists():
            for item in self.load_from_local(corpus_file):
                doc_id = item.get("_id") or item.get("id", "")
                corpus[doc_id] = {"text": item.get("text", ""), "title": item.get("title", "")}

        queries: Dict[str, str] = {}
        queries_file = directory / "queries.jsonl"
        if queries_file.exists():
            for item in self.load_from_local(queries_file):
                qid = item.get("_id") or item.get("id", "")
                queries[qid] = item.get("text", "")

        qrels: Dict[str, Dict[str, int]] = {}
        qrels_file = directory / "qrels" / f"{split}.tsv"
        if qrels_file.exists():
            with open(qrels_file, encoding="utf-8") as f:
                next(f, None)
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) >= 3:
                        qid, doc_id, score = parts[0], parts[1], int(parts[2])
                        qrels.setdefault(qid, {})[doc_id] = score

        return self._convert(corpus, queries, qrels, max_samples)

    @staticmethod
    def _convert(
        corpus: Dict[str, Any],
        queries: Dict[str, str],
        qrels: Dict[str, Dict[str, int]],
        max_samples: Optional[int],
    ) -> List[RetrievalTask]:
        """将 BEIR 格式数据转换为 RetrievalTask 列表。"""
        doc_pool = [
            Document(
                doc_id=doc_id,
                text=info.get("text", "") if isinstance(info, dict) else str(info),
                title=info.get("title", "") if isinstance(info, dict) else "",
            )
            for doc_id, info in corpus.items()
        ]

        tasks: List[RetrievalTask] = []
        for qid, query_text in queries.items():
            if max_samples and len(tasks) >= max_samples:
                break
            rels = qrels.get(qid, {})
            relevant_ids = [doc_id for doc_id, score in rels.items() if score > 0]
            if not relevant_ids:
                continue
            tasks.append(
                RetrievalTask(
                    task_id=qid,
                    query=query_text,
                    corpus=doc_pool,
                    relevant_doc_ids=relevant_ids,
                    relevance_scores=rels,
                )
            )
        return tasks
