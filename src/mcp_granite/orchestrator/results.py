"""Result collection, serialization, and aggregation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from mcp_granite.evaluation.metrics import ScenarioResult
from mcp_granite.harness.trace import ExecutionTrace
from mcp_granite.orchestrator.experiment import ExperimentCondition


@dataclass
class ConditionResult:
    """Result of a single experimental condition run."""

    condition: ExperimentCondition
    trace: ExecutionTrace
    metrics: ScenarioResult
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": {
                "model": self.condition.model,
                "domain": self.condition.domain,
                "granularity": self.condition.granularity,
                "scenario_id": self.condition.scenario_id,
                "fault_rate": self.condition.fault_rate,
                "repetition": self.condition.repetition,
                "seed": self.condition.seed,
            },
            "metrics": self.metrics.to_dict(),
            "trace_summary": {
                "num_tool_calls": len(self.trace.tool_calls),
                "num_llm_turns": self.trace.num_llm_turns,
                "wall_time_seconds": self.trace.wall_time_seconds,
                "timed_out": self.trace.timed_out,
                "total_tokens": self.trace.total_tokens(),
                "started_at": self.trace.started_at,
                "ended_at": self.trace.ended_at,
            },
            "error": self.error,
        }


def save_result(result: ConditionResult, output_dir: Path) -> None:
    """Append a single result to the JSONL file (crash-resilient incremental save)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "results.jsonl"
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(result.to_dict(), default=str) + "\n")


def save_trace(result: ConditionResult, output_dir: Path) -> None:
    """Save the full trace for a condition (for post-hoc re-evaluation)."""
    traces_dir = output_dir / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    trace_path = traces_dir / f"{result.condition.key}.json"
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(result.trace.to_dict(), f, indent=2, default=str)


def load_results(output_dir: Path) -> list[dict[str, Any]]:
    """Load all results from a JSONL file."""
    jsonl_path = output_dir / "results.jsonl"
    if not jsonl_path.exists():
        return []
    results = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def load_completed_keys(output_dir: Path) -> set[str]:
    """Load the set of condition keys that have already been completed (for resume)."""
    results = load_results(output_dir)
    keys = set()
    for r in results:
        cond = r.get("condition", {})
        safe_model = cond.get("model", "").replace("/", "--")
        key = (
            f"{safe_model}__{cond.get('domain')}__{cond.get('granularity')}"
            f"__{cond.get('scenario_id')}__fr{cond.get('fault_rate')}__rep{cond.get('repetition')}"
        )
        keys.add(key)
    return keys


@dataclass
class ModelRunSummary:
    """Aggregated summary of experiment runs for a single model."""

    model: str
    experiment_count: int
    latest_run_dir: str
    last_finished: str


def scan_all_runs(results_dir: Path) -> list[ModelRunSummary]:
    """Scan all run_* subdirectories, aggregate results by model.

    Returns a list of ModelRunSummary sorted by model name.
    """
    if not results_dir.is_dir():
        return []

    # Collect per-model stats across all run directories
    model_stats: dict[str, dict[str, Any]] = {}

    for run_dir in sorted(results_dir.iterdir()):
        if not run_dir.is_dir() or not run_dir.name.startswith("run_"):
            continue

        results = load_results(run_dir)
        for r in results:
            model = r.get("condition", {}).get("model", "unknown")
            ended_at = r.get("trace_summary", {}).get("ended_at", "")

            if model not in model_stats:
                model_stats[model] = {
                    "experiment_count": 0,
                    "latest_run_dir": run_dir.name,
                    "last_finished": ended_at or "",
                }

            stats = model_stats[model]
            stats["experiment_count"] += 1

            # Track the latest run directory and timestamp
            if run_dir.name > stats["latest_run_dir"]:
                stats["latest_run_dir"] = run_dir.name
            if ended_at and ended_at > stats["last_finished"]:
                stats["last_finished"] = ended_at

    summaries = [
        ModelRunSummary(
            model=model,
            experiment_count=stats["experiment_count"],
            latest_run_dir=stats["latest_run_dir"],
            last_finished=stats["last_finished"],
        )
        for model, stats in model_stats.items()
    ]
    summaries.sort(key=lambda s: s.model)
    return summaries


def results_to_dataframe(output_dir: Path) -> pd.DataFrame:
    """Load results and flatten into a pandas DataFrame for analysis."""
    results = load_results(output_dir)
    rows = []
    for r in results:
        cond = r.get("condition", {})
        metrics = r.get("metrics", {})
        trace_summary = r.get("trace_summary", {})
        row = {**cond, **metrics, **trace_summary, "error": r.get("error")}
        rows.append(row)
    return pd.DataFrame(rows)
