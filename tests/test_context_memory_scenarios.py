"""Tests for self-built scenario tasks."""

import pytest
from agent_eval.context_memory.scenarios import (
    get_all_self_built_tasks,
    get_compression_tasks,
    get_context_exposure_tasks,
    get_memory_tier_tasks,
    get_multi_source_tasks,
    get_sub_agent_tasks,
    get_tool_context_tasks,
    get_working_memory_tasks,
)
from agent_eval.context_memory.models import (
    ContextQualityTask,
    MemoryTask,
    MemoryTaskType,
)


class TestMultiSourceScenario:
    def test_returns_tasks(self):
        tasks = get_multi_source_tasks()
        assert len(tasks) > 0

    def test_tasks_have_uc_metadata(self):
        tasks = get_multi_source_tasks()
        for task in tasks:
            assert "uc" in task.metadata
            assert task.metadata["uc"].startswith("UC001")

    def test_task_ids_unique(self):
        tasks = get_multi_source_tasks()
        ids = [t.task_id for t in tasks]
        assert len(ids) == len(set(ids))


class TestMemoryTierScenario:
    def test_returns_tasks(self):
        tasks = get_memory_tier_tasks()
        assert len(tasks) > 0

    def test_tasks_have_uc_metadata(self):
        tasks = get_memory_tier_tasks()
        for task in tasks:
            assert "uc" in task.metadata
            assert "UC002" in task.metadata["uc"]

    def test_memory_tasks_have_history(self):
        tasks = get_memory_tier_tasks()
        for task in tasks:
            assert isinstance(task, MemoryTask)
            assert len(task.history) > 0


class TestContextExposureScenario:
    def test_returns_tasks(self):
        tasks = get_context_exposure_tasks()
        assert len(tasks) > 0

    def test_all_should_abstain(self):
        tasks = get_context_exposure_tasks()
        for task in tasks:
            assert task.should_abstain is True, f"Task {task.task_id} should have should_abstain=True"

    def test_tasks_are_memory_type(self):
        tasks = get_context_exposure_tasks()
        for task in tasks:
            assert isinstance(task, MemoryTask)
            assert task.task_type == MemoryTaskType.ABSTENTION


class TestCompressionScenario:
    def test_returns_tasks(self):
        tasks = get_compression_tasks()
        assert len(tasks) > 0

    def test_tasks_are_context_quality_type(self):
        tasks = get_compression_tasks()
        for task in tasks:
            assert isinstance(task, ContextQualityTask)

    def test_budget_tokens_set(self):
        tasks = get_compression_tasks()
        for task in tasks:
            assert task.budget_tokens > 0


class TestWorkingMemoryScenario:
    def test_returns_tasks(self):
        tasks = get_working_memory_tasks()
        assert len(tasks) > 0

    def test_tasks_have_uc_metadata(self):
        tasks = get_working_memory_tasks()
        for task in tasks:
            assert "uc" in task.metadata
            assert "UC010" in task.metadata["uc"]


class TestToolContextScenario:
    def test_returns_tasks(self):
        tasks = get_tool_context_tasks()
        assert len(tasks) > 0

    def test_tasks_have_uc_metadata(self):
        tasks = get_tool_context_tasks()
        for task in tasks:
            assert "uc" in task.metadata
            assert "UC011" in task.metadata["uc"]


class TestSubAgentScenario:
    def test_returns_tasks(self):
        tasks = get_sub_agent_tasks()
        assert len(tasks) > 0

    def test_tasks_have_uc_metadata(self):
        tasks = get_sub_agent_tasks()
        for task in tasks:
            assert "uc" in task.metadata
            assert "UC014" in task.metadata["uc"]


class TestGetAllSelfBuiltTasks:
    def test_returns_all_tasks(self):
        tasks = get_all_self_built_tasks()
        assert len(tasks) >= 20  # at least 20 tasks across 7 scenarios

    def test_all_task_ids_unique(self):
        tasks = get_all_self_built_tasks()
        ids = [t.task_id for t in tasks]
        assert len(ids) == len(set(ids)), "Duplicate task IDs found!"

    def test_all_tasks_have_metadata(self):
        tasks = get_all_self_built_tasks()
        for task in tasks:
            assert hasattr(task, "metadata")
            assert "uc" in task.metadata

    def test_covers_multiple_uc_codes(self):
        tasks = get_all_self_built_tasks()
        uc_codes = set()
        for task in tasks:
            uc = task.metadata.get("uc", "")
            # Extract UC code (e.g., "UC001", "UC002")
            for part in uc.split(","):
                code = part.strip()
                if code.startswith("UC"):
                    uc_codes.add(code[:5])  # UC001 → UC001
        assert len(uc_codes) >= 5, f"Expected at least 5 UC codes, got: {uc_codes}"
