"""CLI entry point for EdgeToolBench."""

from __future__ import annotations

import logging
from pathlib import Path

import click
import yaml

from edgetoolbench.config.settings import ExperimentConfig


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def main(verbose: bool) -> None:
    """EdgeToolBench: Benchmark for tool granularity effects on LLM agents."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@main.command()
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="YAML config file (default: configs/default.yaml).",
)
@click.option("--models", "-m", multiple=True, help="Override model list.")
@click.option("--domains", "-d", multiple=True, help="Override domain list.")
@click.option("--fault-rates", multiple=True, type=float, help="Override fault rates.")
@click.option("--repetitions", "-k", type=int, default=None, help="Override repetitions.")
@click.option(
    "--timeout", "-t", type=float, default=None, help="Agent timeout in seconds (default: 120)."
)
def run(
    config_path: Path | None,
    models: tuple[str, ...],
    domains: tuple[str, ...],
    fault_rates: tuple[float, ...],
    repetitions: int | None,
    timeout: float | None,
) -> None:
    """Run the experiment matrix."""
    config = _load_config(config_path)

    # Apply CLI overrides
    if models:
        config.models = list(models)
    if domains:
        config.domains = list(domains)
    if fault_rates:
        config.fault_rates = list(fault_rates)
    if repetitions is not None:
        config.repetitions = repetitions
    if timeout is not None:
        config.agent_timeout_seconds = timeout

    # Preflight: verify all Ollama models are available locally
    from edgetoolbench.models.registry import preflight_check_models

    preflight_check_models(config.models)

    click.echo(
        f"Running experiment: {len(config.models)} models x "
        f"{len(config.domains)} domains x "
        f"{len(config.granularities)} granularities x "
        f"{len(config.fault_rates)} fault rates x "
        f"{config.repetitions} reps"
    )

    from edgetoolbench.orchestrator.runner import run_experiment_sync

    output_dir = run_experiment_sync(config)
    click.echo(f"Results saved to: {output_dir}")


@main.command()
@click.option(
    "--results-dir",
    "-r",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Directory containing results.jsonl.",
)
def evaluate(results_dir: Path) -> None:
    """Load and display summary statistics from a completed run."""
    from edgetoolbench.orchestrator.results import results_to_dataframe

    df = results_to_dataframe(results_dir)
    if df.empty:
        click.echo("No results found.")
        return

    click.echo(f"Loaded {len(df)} results.\n")

    # Summary by model × granularity
    summary = (
        df.groupby(["model", "granularity"])
        .agg(
            {
                "tool_selection_f1": "mean",
                "argument_accuracy": "mean",
                "sequence_edit_distance": "mean",
                "task_completion": "mean",
                "wall_time_seconds": "mean",
            }
        )
        .round(3)
    )
    click.echo("=== Summary by Model × Granularity ===")
    click.echo(summary.to_string())
    click.echo()

    # Summary by domain
    domain_summary = (
        df.groupby("domain")
        .agg(
            {
                "tool_selection_f1": "mean",
                "task_completion": "mean",
            }
        )
        .round(3)
    )
    click.echo("=== Summary by Domain ===")
    click.echo(domain_summary.to_string())


@main.command("list-scenarios")
@click.option("--domain", "-d", default=None, help="Filter by domain.")
def list_scenarios(domain: str | None) -> None:
    """List all available scenarios."""
    from edgetoolbench.scenarios.loader import load_scenarios

    config = _load_config(None)
    scenarios = load_scenarios(config.scenarios_dir, domain=domain)

    if not scenarios:
        click.echo("No scenarios found.")
        return

    click.echo(f"{'ID':<20} {'Domain':<12} {'Difficulty':<10} {'Name'}")
    click.echo("-" * 70)
    for s in scenarios:
        click.echo(f"{s.id:<20} {s.domain:<12} {s.difficulty:<10} {s.name}")


@main.command("list-models")
def list_models() -> None:
    """List all registered models."""
    from edgetoolbench.models.registry import MODELS

    click.echo(f"{'Name':<20} {'Size':<10} {'Local':<6} {'ID'}")
    click.echo("-" * 70)
    for name, spec in MODELS.items():
        model_id = spec.google_model or spec.litellm_id or "?"
        click.echo(f"{name:<20} {spec.size_class:<10} {str(spec.local):<6} {model_id}")


@main.command("list-run-models")
@click.option(
    "--results-dir",
    "-r",
    type=click.Path(exists=True, path_type=Path),
    default="results",
    help="Top-level results directory (default: results/).",
)
def list_run_models(results_dir: Path) -> None:
    """List which model was used in each run directory."""
    from edgetoolbench.orchestrator.results import load_results

    run_dirs = sorted(
        p for p in results_dir.iterdir() if p.is_dir() and p.name.startswith("run_")
    )
    if not run_dirs:
        click.echo(f"No run directories found under {results_dir}/.")
        return

    # Determine column widths
    run_w = max(len(d.name) for d in run_dirs)
    run_w = max(run_w, len("Run"))

    rows: list[tuple[str, str, int]] = []
    for run_dir in run_dirs:
        results = load_results(run_dir)
        if not results:
            rows.append((run_dir.name, "(no results)", 0))
            continue
        model = results[0].get("condition", {}).get("model", "unknown")
        rows.append((run_dir.name, model, len(results)))

    model_w = max(len(r[1]) for r in rows)
    model_w = max(model_w, len("Model"))
    exp_w = max(len(str(r[2])) for r in rows)
    exp_w = max(exp_w, len("Exps"))

    header = f"{'Run':<{run_w}}  {'Model':<{model_w}}  {'Exps':>{exp_w}}"
    sep = "-" * len(header)
    click.echo(header)
    click.echo(sep)
    for run_name, model, count in rows:
        click.echo(f"{run_name:<{run_w}}  {model:<{model_w}}  {count:>{exp_w}}")
    click.echo(sep)
    click.echo(f"{'TOTAL':<{run_w}}  {'':<{model_w}}  {sum(r[2] for r in rows):>{exp_w}}")


@main.command("list-runs")
@click.option(
    "--results-dir",
    "-r",
    type=click.Path(exists=True, path_type=Path),
    default="results",
    help="Top-level results directory (default: results/).",
)
def list_runs(results_dir: Path) -> None:
    """List all completed experiment runs grouped by model."""
    from edgetoolbench.models.registry import (
        _fetch_ollama_model_details,
        resolve_parameter_count,
    )
    from edgetoolbench.orchestrator.results import scan_all_runs

    summaries = scan_all_runs(results_dir)
    if not summaries:
        click.echo("No runs found.")
        return

    # Fetch Ollama details once for parameter resolution
    ollama_details = _fetch_ollama_model_details()

    # Dynamic column width for model name
    model_width = max(len(s.model) for s in summaries)
    model_width = max(model_width, len("Model"))
    # Fixed widths for other columns
    params_w, exps_w, run_w, ts_w = 10, 6, 26, 20

    header = (
        f"{'Model':<{model_width}}  "
        f"{'Params':>{params_w}}  "
        f"{'Exps':>{exps_w}}  "
        f"{'Latest Run':<{run_w}}  "
        f"{'Last Finished':<{ts_w}}"
    )
    sep = "-" * len(header)

    click.echo(header)
    click.echo(sep)

    total_exps = 0
    for s in summaries:
        params = resolve_parameter_count(s.model, ollama_details)
        # Truncate timestamp to seconds (remove fractional / tz)
        last_ts = s.last_finished[:19] if s.last_finished else ""
        click.echo(
            f"{s.model:<{model_width}}  "
            f"{params:>{params_w}}  "
            f"{s.experiment_count:>{exps_w}}  "
            f"{s.latest_run_dir:<{run_w}}  "
            f"{last_ts:<{ts_w}}"
        )
        total_exps += s.experiment_count

    click.echo(sep)
    # TOTAL row: model column shows "TOTAL", params blank, exps total, rest blank
    click.echo(f"{'TOTAL':<{model_width}}  {'':>{params_w}}  {total_exps:>{exps_w}}")


@main.command("fetch-metrics")
@click.option(
    "--results-dir",
    "-r",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to a single run_XXXXXX directory.",
)
@click.option("--all", "fetch_all", is_flag=True, help="Fetch metrics for all runs under results/.")
@click.option(
    "--prometheus-url",
    type=str,
    default=None,
    help="Prometheus URL (overrides ETB_PROMETHEUS_URL env var).",
)
@click.option("--metrics", multiple=True, help="Specific metric names to fetch (default: curated list).")
@click.option("--step", type=str, default="5s", help="Range query step resolution (default: 5s).")
@click.option("--force", is_flag=True, help="Re-fetch even if prometheus.csv already exists.")
@click.option(
    "--max-chunk",
    type=int,
    default=7200,
    help="Max seconds per Prometheus query chunk (default: 7200 = 2h).",
)
def fetch_metrics(
    results_dir: Path | None,
    fetch_all: bool,
    prometheus_url: str | None,
    metrics: tuple[str, ...],
    step: str,
    force: bool,
    max_chunk: int,
) -> None:
    """Fetch Prometheus time-series for experiment runs."""
    from edgetoolbench.monitoring.prometheus import PrometheusClient

    if not results_dir and not fetch_all:
        raise click.ClickException("Provide --results-dir/-r for a single run, or --all for every run.")

    # Resolve Prometheus URL
    config = _load_config(None)
    if prometheus_url is None:
        prometheus_url = config.prometheus_url
    if not prometheus_url:
        import os

        prometheus_url = os.environ.get("ETB_PROMETHEUS_URL")
    if not prometheus_url:
        raise click.ClickException(
            "No Prometheus URL provided. Use --prometheus-url, config, or ETB_PROMETHEUS_URL env var."
        )

    metrics_list = list(metrics) if metrics else None
    client = PrometheusClient(url=prometheus_url, step=step)

    # Collect run directories to process
    if fetch_all:
        base = config.results_dir
        run_dirs = sorted(p for p in base.iterdir() if p.is_dir() and p.name.startswith("run_"))
        if not run_dirs:
            click.echo(f"No run directories found under {base}/.")
            return
        click.echo(f"Found {len(run_dirs)} runs under {base}/.\n")
    else:
        run_dirs = [results_dir]

    skip_existing = fetch_all and not force
    for run_dir in run_dirs:
        _fetch_metrics_for_run(
            run_dir, client, metrics_list,
            skip_existing=skip_existing,
            max_chunk_seconds=max_chunk,
        )


def _fetch_metrics_for_run(
    run_dir: Path,
    client: "PrometheusClient",  # noqa: F821
    metrics: list[str] | None,
    *,
    skip_existing: bool = False,
    max_chunk_seconds: int = 7200,
) -> None:
    """Fetch and save Prometheus time-series for a single run directory."""
    from edgetoolbench.monitoring.prometheus import (
        PROMETHEUS_CSV,
        get_run_time_window,
        save_prometheus_csv,
    )
    from edgetoolbench.orchestrator.results import load_results

    label = run_dir.name

    # Skip only if the file exists AND has actual data (more than just a header)
    csv_file = run_dir / PROMETHEUS_CSV
    if skip_existing and csv_file.exists():
        file_size = csv_file.stat().st_size
        # A header-only CSV (e.g. "timestamp,metric,label,value\n") is ~31 bytes
        if file_size > 100:
            click.echo(f"[{label}] Already has {PROMETHEUS_CSV} ({file_size} bytes), skipping.")
            return
        else:
            click.echo(
                f"[{label}] Existing {PROMETHEUS_CSV} is empty/header-only "
                f"({file_size} bytes), re-fetching."
            )

    results = load_results(run_dir)
    if not results:
        click.echo(f"[{label}] No results found, skipping.")
        return

    window = get_run_time_window(results)
    if not window:
        click.echo(f"[{label}] No valid timestamps, skipping.")
        return

    started_at, ended_at = window
    from datetime import datetime

    duration_h = (
        datetime.fromisoformat(ended_at) - datetime.fromisoformat(started_at)
    ).total_seconds() / 3600
    click.echo(f"[{label}] {started_at} .. {ended_at} ({duration_h:.1f}h) — fetching...")

    rows = client.fetch_run_timeseries(
        started_at=started_at,
        ended_at=ended_at,
        metrics=metrics,
        max_chunk_seconds=max_chunk_seconds,
    )

    if not rows:
        click.echo(f"[{label}] No data returned from Prometheus.")
        return

    csv_path = save_prometheus_csv(rows, run_dir)
    click.echo(f"[{label}] Saved {len(rows)} rows to {csv_path}")


@main.command("list-metrics")
@click.option(
    "--prometheus-url",
    type=str,
    default=None,
    help="Prometheus URL (overrides ETB_PROMETHEUS_URL env var).",
)
@click.option(
    "--host-filter",
    type=str,
    default=None,
    help="Filter metrics containing _<host>_ (default: local hostname).",
)
@click.option("--all", "show_all", is_flag=True, help="Show all metrics, skip hostname filter.")
@click.option(
    "--curated", is_flag=True, help="Show only the curated metrics used by fetch-metrics."
)
def list_metrics(
    prometheus_url: str | None,
    host_filter: str | None,
    show_all: bool,
    curated: bool,
) -> None:
    """List available Prometheus metrics (filtered by hostname by default)."""
    import os
    import socket

    from edgetoolbench.monitoring.prometheus import PrometheusClient

    # Resolve Prometheus URL
    if prometheus_url is None:
        config = _load_config(None)
        prometheus_url = config.prometheus_url
    if not prometheus_url:
        prometheus_url = os.environ.get("ETB_PROMETHEUS_URL")
    if not prometheus_url:
        raise click.ClickException(
            "No Prometheus URL provided. Use --prometheus-url, config, or ETB_PROMETHEUS_URL env var."
        )

    client = PrometheusClient(url=prometheus_url)
    hostname = host_filter or socket.gethostname()

    if curated:
        filtered = client.discover_curated_metrics(hostname=hostname)
        label = f"curated for '{hostname}'"
    elif show_all:
        filtered = client.discover_metrics()
        label = "all"
    else:
        pattern = f"_{hostname}_"
        filtered = [m for m in client.discover_metrics() if pattern in m]
        label = f"matching '_{hostname}_'"

    if not filtered:
        click.echo(f"No metrics found ({label}).")
        return

    click.echo(f"Found {len(filtered)} metrics ({label}):\n")
    for m in filtered:
        click.echo(f"  {m}")


@main.command("serve-mcp")
@click.option(
    "--domain",
    "-d",
    required=True,
    type=click.Choice(["travel", "helpdesk", "ecommerce", "smarthome", "industrial", "fleet"]),
)
@click.option(
    "--granularity",
    "-g",
    required=True,
    type=click.Choice(["primitive", "composite_4", "composite_2", "composite_1"]),
)
@click.option("--fault-rate", type=float, default=0.0, help="Fault injection rate.")
@click.option("--seed", type=int, default=42, help="Random seed for fault injection.")
def serve_mcp(domain: str, granularity: str, fault_rate: float, seed: int) -> None:
    """Run a standalone MCP server (for debugging/testing)."""
    import importlib
    import json
    import os
    import subprocess
    import sys

    module = f"edgetoolbench.mcp_servers.{domain}.{granularity}_server"
    try:
        importlib.import_module(module)
    except ModuleNotFoundError:
        raise click.ClickException(
            f"No server module for domain='{domain}', granularity='{granularity}'. "
            f"Expected module: {module}"
        )

    env = {
        **os.environ,
        "FAULT_CONFIG": json.dumps({"rate": fault_rate, "seed": seed}),
    }

    click.echo(f"Starting MCP server: {module} (fault_rate={fault_rate}, seed={seed})")
    click.echo("Press Ctrl+C to stop.")
    subprocess.run([sys.executable, "-m", module], env=env)


def _load_config(config_path: Path | None) -> ExperimentConfig:
    """Load experiment config from YAML or use defaults."""
    if config_path and config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return ExperimentConfig(**data)
    # Try default config
    default_path = Path("configs/default.yaml")
    if default_path.exists():
        with open(default_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return ExperimentConfig(**data)
    return ExperimentConfig()


if __name__ == "__main__":
    main()
