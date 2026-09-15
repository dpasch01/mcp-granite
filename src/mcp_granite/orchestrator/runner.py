"""Experiment runner: executes all conditions sequentially with incremental save."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from mcp_granite.config.settings import ExperimentConfig
from mcp_granite.evaluation.comparator import evaluate
from mcp_granite.evaluation.gold_standard import load_gold_standard
from mcp_granite.harness.agent_factory import create_agent_and_toolset
from mcp_granite.harness.runner import build_runner, run_scenario
from mcp_granite.mcp_servers._base import FaultConfig
from mcp_granite.orchestrator.experiment import (
    ExperimentCondition,
    generate_experiment_matrix,
)
from mcp_granite.orchestrator.results import (
    ConditionResult,
    load_completed_keys,
    save_result,
    save_trace,
)
from mcp_granite.scenarios.loader import load_scenario_by_id

logger = logging.getLogger(__name__)


async def run_experiment(config: ExperimentConfig) -> Path:
    """Run the full experiment matrix.

    Returns the output directory path containing results.
    """
    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = config.results_dir / f"run_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    conditions = generate_experiment_matrix(config)
    completed = load_completed_keys(output_dir)

    logger.info(
        "Experiment matrix: %d conditions (%d already completed)",
        len(conditions),
        len(completed),
    )

    for i, condition in enumerate(conditions):
        if condition.key in completed:
            logger.info(
                "[%d/%d] Skipping (already done): %s", i + 1, len(conditions), condition.key
            )
            continue

        logger.info("[%d/%d] Running: %s", i + 1, len(conditions), condition.key)

        result = await _run_single_condition(condition, config)
        save_result(result, output_dir)
        save_trace(result, output_dir)

        if result.error:
            logger.warning("  -> Error: %s", result.error)
        else:
            logger.info(
                "  -> F1=%.2f, completion=%.1f, time=%.1fs",
                result.metrics.tool_selection_f1,
                result.metrics.task_completion,
                result.trace.wall_time_seconds,
            )

    logger.info("Experiment complete. Results in: %s", output_dir)

    # Fetch Prometheus metrics for the entire run window
    if config.prometheus_url:
        try:
            from mcp_granite.monitoring.prometheus import (
                PrometheusClient,
                get_run_time_window,
                save_prometheus_csv,
            )
            from mcp_granite.orchestrator.results import load_results

            all_results = load_results(output_dir)
            window = get_run_time_window(all_results)
            if window:
                started_at, ended_at = window
                client = PrometheusClient(
                    url=config.prometheus_url, step=config.prometheus_step
                )
                logger.info(
                    "Fetching Prometheus metrics for %s .. %s", started_at, ended_at
                )
                rows = client.fetch_run_timeseries(
                    started_at=started_at,
                    ended_at=ended_at,
                    metrics=config.prometheus_metrics,
                )
                csv_path = save_prometheus_csv(rows, output_dir)
                logger.info("Prometheus CSV saved: %s (%d rows)", csv_path, len(rows))
            else:
                logger.warning("No valid timestamps in results, skipping Prometheus fetch.")
        except Exception:
            logger.warning(
                "Prometheus fetch failed, continuing without.", exc_info=True
            )
    return output_dir


async def _run_single_condition(
    condition: ExperimentCondition,
    config: ExperimentConfig,
) -> ConditionResult:
    """Run a single experimental condition."""
    fault_config = FaultConfig(
        rate=condition.fault_rate,
        seed=condition.seed,
    )

    try:
        # Load scenario
        scenario = load_scenario_by_id(config.scenarios_dir, condition.scenario_id)

        # Create agent + MCP toolset
        agent, toolset = create_agent_and_toolset(
            model_name=condition.model,
            domain=condition.domain,
            granularity=condition.granularity,
            fault_config=fault_config,
        )

        try:
            # Build runner and execute
            adk_runner = build_runner(agent)
            trace = await run_scenario(
                runner=adk_runner,
                scenario=scenario,
                timeout_seconds=config.agent_timeout_seconds,
                max_turns=config.max_agent_turns,
            )
        finally:
            await toolset.close()

        # Evaluate against gold standard
        gold = load_gold_standard(scenario, condition.granularity)
        metrics = evaluate(trace, gold)

        return ConditionResult(
            condition=condition,
            trace=trace,
            metrics=metrics,
            error=trace.error,
        )

    except Exception as exc:
        logger.exception("Condition failed: %s", condition.key)
        # Return a result with error info and zeroed metrics
        from mcp_granite.evaluation.metrics import ScenarioResult
        from mcp_granite.harness.trace import ExecutionTrace

        return ConditionResult(
            condition=condition,
            trace=ExecutionTrace(error=str(exc)),
            metrics=ScenarioResult(
                tool_selection_precision=0,
                tool_selection_recall=0,
                tool_selection_f1=0,
                argument_accuracy=0,
                sequence_edit_distance=1.0,
                sequence_kendall_tau=0,
                task_completion=0,
                error_recovery_rate=None,
                token_efficiency=0,
                redundant_call_rate=0,
            ),
            error=str(exc),
        )


def run_experiment_sync(config: ExperimentConfig) -> Path:
    """Synchronous wrapper for run_experiment."""
    return asyncio.run(run_experiment(config))
