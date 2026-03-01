"""Execution harness for running agent evaluations end-to-end."""

from __future__ import annotations

import inspect
import json
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from agent_eval.evaluator import AgentEvaluator
from agent_eval.models import EvalTask, TaskTrialResult

AgentRunPayload = Any
AgentRunner = Callable[..., AgentRunPayload]
EnvironmentFactory = Callable[..., Any]


class EvaluationHarness:
    """Run tasks against an agent runner and evaluate over multiple trials.

    Parameters
    ----------
    evaluator:
        Configured :class:`~agent_eval.evaluator.AgentEvaluator`.
    agent_runner:
        Callable that executes the agent. It may accept one to three positional
        arguments in order ``(task, environment, seed)`` and may return either:
        - ``str``: agent output text
        - ``dict`` with keys:
          - ``output`` (required string-like)
          - ``transcript`` (optional list of step dicts)
          - ``outcome`` (optional final state dict)
    environment_factory:
        Optional callable that creates an isolated environment per trial. It may
        accept one to three positional arguments in order
        ``(task, trial_index, seed)``.
    default_trials:
        Number of trials used when ``run`` / ``run_task`` do not pass
        ``n_trials`` explicitly.
    """

    def __init__(
        self,
        evaluator: AgentEvaluator,
        agent_runner: AgentRunner,
        environment_factory: Optional[EnvironmentFactory] = None,
        default_trials: int = 1,
    ) -> None:
        if default_trials <= 0:
            raise ValueError(f"default_trials must be positive, got {default_trials!r}")

        self.evaluator = evaluator
        self.agent_runner = agent_runner
        self.environment_factory = environment_factory
        self.default_trials = default_trials

    def run_task(
        self,
        task: EvalTask,
        n_trials: Optional[int] = None,
        base_seed: Optional[int] = None,
    ) -> TaskTrialResult:
        """Run one task across multiple trials and return aggregate results."""
        trial_count = self.default_trials if n_trials is None else n_trials
        if trial_count <= 0:
            raise ValueError(f"n_trials must be positive, got {trial_count!r}")

        outputs: List[str] = []
        seeds: List[Optional[int]] = []
        transcripts: List[List[Dict[str, Any]]] = []
        outcomes: List[Optional[Dict[str, Any]]] = []
        errors: List[str] = []

        for trial_index in range(trial_count):
            seed = None if base_seed is None else base_seed + trial_index
            env = None

            try:
                env = self._create_environment(task, trial_index, seed)
                self._setup_environment(env)
                payload = self._invoke_callable(self.agent_runner, task, env, seed)
                output, transcript, outcome = self._normalise_agent_payload(payload, env)
                error = ""
            except Exception as exc:
                output = ""
                transcript = []
                outcome = self._extract_environment_outcome(env)
                error = f"{type(exc).__name__}: {exc}"
            finally:
                self._teardown_environment(env)

            outputs.append(output)
            seeds.append(seed)
            transcripts.append(transcript)
            outcomes.append(outcome)
            errors.append(error)

        return self.evaluator.evaluate_task_trials(
            task=task,
            agent_outputs=outputs,
            seeds=seeds,
            transcripts=transcripts,
            outcomes=outcomes,
            errors=errors,
        )

    def run(
        self,
        tasks: Sequence[EvalTask],
        n_trials: Optional[int] = None,
        base_seed: Optional[int] = None,
    ) -> List[TaskTrialResult]:
        """Run many tasks and return task-level trial aggregates."""
        return [
            self.run_task(task=task, n_trials=n_trials, base_seed=base_seed)
            for task in tasks
        ]

    def summary(self, task_trial_results: Sequence[TaskTrialResult]) -> Dict[str, Any]:
        """Return summary metrics for harness runs."""
        return self.evaluator.trial_summary(task_trial_results)

    def summary_json(self, task_trial_results: Sequence[TaskTrialResult]) -> str:
        """Return :meth:`summary` serialised as JSON."""
        return json.dumps(self.summary(task_trial_results), indent=2)

    def _create_environment(
        self,
        task: EvalTask,
        trial_index: int,
        seed: Optional[int],
    ) -> Any:
        if self.environment_factory is None:
            return None
        return self._invoke_callable(self.environment_factory, task, trial_index, seed)

    @staticmethod
    def _setup_environment(environment: Any) -> None:
        if environment is None:
            return
        setup = getattr(environment, "setup", None)
        if callable(setup):
            setup()

    @staticmethod
    def _teardown_environment(environment: Any) -> None:
        if environment is None:
            return
        for method_name in ("teardown", "cleanup"):
            fn = getattr(environment, method_name, None)
            if callable(fn):
                fn()
                break

    @staticmethod
    def _extract_environment_outcome(environment: Any) -> Optional[Dict[str, Any]]:
        if environment is None:
            return None

        for method_name in ("get_outcome", "get_final_state"):
            fn = getattr(environment, method_name, None)
            if callable(fn):
                value = fn()
                return value if isinstance(value, dict) else {"value": value}

        if hasattr(environment, "outcome"):
            value = getattr(environment, "outcome")
            return value if isinstance(value, dict) else {"value": value}

        return None

    def _normalise_agent_payload(
        self,
        payload: AgentRunPayload,
        environment: Any,
    ) -> Tuple[str, List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        if isinstance(payload, str):
            return payload, [], self._extract_environment_outcome(environment)

        if not isinstance(payload, dict):
            raise TypeError(
                "agent_runner must return either a string output or a dict payload"
            )

        if "output" not in payload:
            raise ValueError("agent_runner payload dict must include an 'output' field")

        output = str(payload["output"])
        raw_transcript = payload.get("transcript", [])
        if raw_transcript is None:
            raw_transcript = []
        if not isinstance(raw_transcript, list):
            raise TypeError("payload['transcript'] must be a list when provided")

        transcript: List[Dict[str, Any]] = []
        for i, step in enumerate(raw_transcript):
            if isinstance(step, dict):
                transcript.append(step)
            else:
                transcript.append({"step_id": i, "observation": str(step)})

        if "outcome" in payload:
            outcome_value = payload["outcome"]
            outcome = (
                outcome_value
                if isinstance(outcome_value, dict) or outcome_value is None
                else {"value": outcome_value}
            )
        else:
            outcome = self._extract_environment_outcome(environment)

        return output, transcript, outcome

    @staticmethod
    def _invoke_callable(func: Callable[..., Any], *ordered_args: Any) -> Any:
        """Invoke a callable with as many positional args as it can accept."""
        signature = inspect.signature(func)
        params = list(signature.parameters.values())

        has_var_positional = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
        positional_params = [
            p
            for p in params
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]

        if has_var_positional:
            return func(*ordered_args)

        required_count = sum(1 for p in positional_params if p.default is inspect._empty)
        max_count = len(positional_params)

        if required_count > len(ordered_args):
            raise TypeError(
                f"{func.__name__} requires at least {required_count} positional arguments"
            )

        arg_count = min(max_count, len(ordered_args))
        return func(*ordered_args[:arg_count])
