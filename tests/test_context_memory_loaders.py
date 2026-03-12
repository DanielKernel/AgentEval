"""Tests for context_memory loaders (local fallback mode, zero external deps)."""

import json
import os
import pytest
import tempfile
from pathlib import Path
from agent_eval.context_memory.loaders.base import BenchmarkLoader
from agent_eval.context_memory.loaders.beir import BEIRLoader
from agent_eval.context_memory.loaders.longmemeval import LongMemEvalLoader
from agent_eval.context_memory.loaders.longbench import LongBenchLoader
from agent_eval.context_memory.loaders.locomo import LoCoMoLoader
from agent_eval.context_memory.loaders.ruler import RULERLoader
from agent_eval.context_memory.models import MemoryTaskType


def _write_jsonl(path: Path, records: list):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _write_json(path: Path, data):
    with open(path, "w") as f:
        json.dump(data, f)


class TestBEIRLoaderLocal:
    def test_load_from_local_files(self, tmp_path):
        # Create mock BEIR structure
        corpus_path = tmp_path / "corpus.jsonl"
        queries_path = tmp_path / "queries.jsonl"
        qrels_dir = tmp_path / "qrels"
        qrels_dir.mkdir()
        qrels_path = qrels_dir / "test.tsv"

        _write_jsonl(corpus_path, [
            {"_id": "d1", "title": "Doc 1", "text": "First document text"},
            {"_id": "d2", "title": "Doc 2", "text": "Second document text"},
            {"_id": "d3", "title": "Doc 3", "text": "Third document text"},
        ])
        _write_jsonl(queries_path, [
            {"_id": "q1", "text": "What is first?"},
            {"_id": "q2", "text": "What is second?"},
        ])
        with open(qrels_path, "w") as f:
            f.write("query-id\tcorpus-id\tscore\n")
            f.write("q1\td1\t1\n")
            f.write("q2\td2\t1\n")

        loader = BEIRLoader()
        tasks = loader.load(local_path=str(tmp_path), split="test", max_samples=10)
        assert len(tasks) == 2
        assert tasks[0].task_id is not None
        assert len(tasks[0].corpus) > 0
        assert len(tasks[0].relevant_doc_ids) >= 1

    def test_max_samples_respected(self, tmp_path):
        corpus_path = tmp_path / "corpus.jsonl"
        queries_path = tmp_path / "queries.jsonl"
        qrels_dir = tmp_path / "qrels"
        qrels_dir.mkdir()
        qrels_path = qrels_dir / "test.tsv"

        _write_jsonl(corpus_path, [{"_id": f"d{i}", "text": f"doc {i}", "title": ""} for i in range(10)])
        _write_jsonl(queries_path, [{"_id": f"q{i}", "text": f"query {i}"} for i in range(5)])
        with open(qrels_path, "w") as f:
            f.write("query-id\tcorpus-id\tscore\n")
            for i in range(5):
                f.write(f"q{i}\td{i}\t1\n")

        loader = BEIRLoader()
        tasks = loader.load(local_path=str(tmp_path), split="test", max_samples=2)
        assert len(tasks) <= 2


class TestLongMemEvalLoaderLocal:
    def test_load_from_local_jsonl(self, tmp_path):
        data_path = tmp_path / "test.jsonl"
        _write_jsonl(data_path, [
            {
                "session_id": "s1",
                "history": [
                    {"speaker": "user", "utterance": "My dog's name is Rex"},
                    {"speaker": "assistant", "utterance": "Nice name!"},
                ],
                "question": "What is my dog's name?",
                "answer": "Rex",
                "task_type": "single_session_qa",
            },
            {
                "session_id": "s2",
                "history": [{"speaker": "user", "utterance": "I went to Paris in 2020"}],
                "question": "When did I go to Paris?",
                "answer": "2020",
                "task_type": "temporal_reasoning",
            },
        ])
        loader = LongMemEvalLoader()
        tasks = loader.load(local_path=str(data_path), max_samples=10)
        assert len(tasks) == 2
        assert tasks[0].session_id == "s1"
        assert tasks[0].gold_answer == "Rex"

    def test_task_type_mapping(self, tmp_path):
        data_path = tmp_path / "test.jsonl"
        _write_jsonl(data_path, [
            {
                "session_id": "s1", "history": [],
                "question": "Q?", "answer": "A",
                "task_type": "temporal_reasoning",
            }
        ])
        loader = LongMemEvalLoader()
        tasks = loader.load(local_path=str(data_path))
        assert tasks[0].task_type == MemoryTaskType.TEMPORAL


class TestLongBenchLoaderLocal:
    def test_load_from_local_jsonl(self, tmp_path):
        data_path = tmp_path / "test.jsonl"
        _write_jsonl(data_path, [
            {
                "input": "Long document text about history...",
                "context": "Historical context here",
                "answers": ["The answer is A"],
                "length": 1024,
            },
            {
                "input": "Another long doc",
                "context": "More context",
                "answers": ["Answer B"],
                "length": 512,
            },
        ])
        loader = LongBenchLoader()
        tasks = loader.load(local_path=str(data_path), max_samples=10)
        assert len(tasks) >= 1
        assert tasks[0].gold_answer is not None


class TestLoCoMoLoaderLocal:
    def test_load_from_local_jsonl(self, tmp_path):
        data_path = tmp_path / "test.jsonl"
        _write_jsonl(data_path, [
            {
                "session_id": "s1",
                "conversation": [
                    {"speaker": "user", "utterance": "Hello"},
                    {"speaker": "assistant", "utterance": "Hi"},
                ],
                "question": "What was the greeting?",
                "answer": "Hello",
            }
        ])
        loader = LoCoMoLoader()
        tasks = loader.load(local_path=str(data_path), max_samples=5)
        assert len(tasks) == 1
        assert tasks[0].gold_answer == "Hello"


class TestRULERLoaderLocal:
    def test_load_from_local_jsonl(self, tmp_path):
        data_path = tmp_path / "test.jsonl"
        _write_jsonl(data_path, [
            {
                "context": "A " * 500,
                "question": "What letter repeats?",
                "answer": "A",
                "task": "niah",  # needle in a haystack
                "context_length": 500,
            }
        ])
        loader = RULERLoader()
        tasks = loader.load(local_path=str(data_path), max_samples=5)
        assert len(tasks) == 1
