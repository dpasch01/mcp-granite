#!/usr/bin/env python3
"""MCP-GRANITE analysis script — joins results.jsonl with prometheus.csv,
produces research-paper-quality figures and summary tables.

Usage:
    python analyze_results.py                              # all runs
    python analyze_results.py -r results/run_20260220_174817/  # single run
    python analyze_results.py --output-dir paper_figs/     # custom output
    python analyze_results.py --no-prometheus               # skip resource analysis
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import warnings
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from adjustText import adjust_text
from scipy import stats

# ---------------------------------------------------------------------------
# Project imports (reuse existing helpers)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mcp_granite.models.registry import (
    MODELS,
    _fetch_ollama_model_details,
    resolve_parameter_count,
)
from mcp_granite.monitoring.prometheus import DEFAULT_METRIC_SUFFIXES

# ---------------------------------------------------------------------------
# Global config
# ---------------------------------------------------------------------------
matplotlib.use("Agg")
warnings.filterwarnings("ignore", category=FutureWarning)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# Mapping: friendly column name → (prometheus metric suffix, required dimension or None)
RESOURCE_COLUMNS: dict[str, tuple[str, str | None]] = {
    "gpu_util_pct": ("nvidia_smi_gpu_utilization_percent_average", None),
    "vram_used_B": ("nvidia_smi_gpu_frame_buffer_memory_usage_B_average", "used"),
    "gpu_power_W": ("nvidia_smi_gpu_power_draw_Watts_average", None),
    "gpu_temp_C": ("nvidia_smi_gpu_temperature_Celsius_average", None),
    "cpu_user_pct": ("system_cpu_percentage_average", "user"),
    "ram_used_MiB": ("system_ram_MiB_average", "used"),
    "pdu_power_W": ("snmp_snmp_r4spdu8_power_W_average", None),
    "rapl_power_W": ("cpu_powercap_intel_rapl_zone_Watts_average", None),
}

# Edge device profiles for feasibility analysis
DEVICE_PROFILES: dict[str, dict[str, float]] = {
    "nc16": {"vram_GB": 16, "power_budget_W": 350, "ram_GB": 128},
    "Xavier": {"vram_GB": 8, "power_budget_W": 30, "ram_GB": 8},
    "RPi5": {"vram_GB": 0, "power_budget_W": 15, "ram_GB": 4},
}

# Bytes per parameter for common quantization levels (used to estimate model memory)
QUANT_BYTES_PER_PARAM: dict[str, float] = {
    "Q3_K_M": 0.4375,   # ~3.5 bits
    "Q4_K_M": 0.5625,   # ~4.5 bits
    "Q5_K_M": 0.6875,   # ~5.5 bits
    "Q8_0": 1.0,         # 8 bits
    "FP16": 2.0,          # 16 bits
    "default": 0.5625,    # assume Q4 as typical Ollama default
}

# KV cache overhead multiplier (fraction of model size, conservative estimate)
_KV_CACHE_OVERHEAD = 0.15

# Plot style
PALETTE = sns.color_palette("colorblind")
GRAN_COLORS = {
    "primitive": PALETTE[0],
    "composite_4": PALETTE[1],
    "composite_2": PALETTE[2],
    "composite_1": PALETTE[3],
}
FIG_DPI_PNG = 150
FIG_DPI_PDF = 300


# ═══════════════════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════════════════

def load_results_jsonl(path: Path) -> list[dict]:
    """Load results.jsonl → list of dicts."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def results_to_dataframe(results: list[dict]) -> pd.DataFrame:
    """Flatten results dicts into a DataFrame."""
    rows = []
    for r in results:
        cond = r.get("condition", {})
        metrics = r.get("metrics", {})
        trace = r.get("trace_summary", {})
        row = {**cond, **metrics, **trace, "error": r.get("error")}
        rows.append(row)
    return pd.DataFrame(rows)


def load_all_runs(results_root: Path) -> pd.DataFrame:
    """Load and concatenate results from all run_* directories."""
    frames = []
    for run_dir in sorted(results_root.iterdir()):
        if not run_dir.is_dir() or not run_dir.name.startswith("run_"):
            continue
        jsonl = run_dir / "results.jsonl"
        if jsonl.exists():
            raw = load_results_jsonl(jsonl)
            df = results_to_dataframe(raw)
            df["run_dir"] = run_dir.name
            frames.append(df)
    if not frames:
        log.error("No results.jsonl found under %s", results_root)
        sys.exit(1)
    return pd.concat(frames, ignore_index=True)


def load_single_run(run_dir: Path) -> pd.DataFrame:
    """Load results from a single run directory."""
    jsonl = run_dir / "results.jsonl"
    if not jsonl.exists():
        log.error("No results.jsonl in %s", run_dir)
        sys.exit(1)
    raw = load_results_jsonl(jsonl)
    df = results_to_dataframe(raw)
    df["run_dir"] = run_dir.name
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# Prometheus loading & join
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_dimension(label: str) -> str | None:
    """Extract dimension="..." from a prometheus label string."""
    m = re.search(r'dimension="([^"]+)"', label)
    return m.group(1) if m else None


def _extract_suffix(metric: str) -> str | None:
    """Match a full prometheus metric name against known suffixes."""
    for suffix in DEFAULT_METRIC_SUFFIXES:
        if metric.endswith(suffix):
            return suffix
    return None


def load_prometheus(run_dir: Path) -> pd.DataFrame | None:
    """Load prometheus.csv, parse timestamps, extract suffix & dimension.

    Returns None if file doesn't exist.
    """
    csv_path = run_dir / "prometheus.csv"
    if not csv_path.exists():
        return None

    log.info("Loading prometheus data from %s ...", csv_path)
    df = pd.read_csv(csv_path, dtype={"metric": str, "label": str, "value": str})

    # Parse timestamps
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Extract suffix and dimension
    df["suffix"] = df["metric"].map(_extract_suffix)
    df["dimension"] = df["label"].map(_extract_dimension)

    # Drop rows with unrecognised suffixes
    df = df.dropna(subset=["suffix"]).copy()
    df.sort_values("timestamp", inplace=True)

    return df


def join_prometheus_to_conditions(
    results_df: pd.DataFrame,
    prom_df: pd.DataFrame,
) -> pd.DataFrame:
    """For each condition row, slice the prometheus window [started_at, ended_at]
    and compute mean resource metrics.  Returns results_df with extra columns."""

    # Pre-sort prometheus timestamps for searchsorted
    prom_ts = prom_df["timestamp"].values  # already sorted

    # Build per-(suffix, dimension) arrays for fast lookup
    resource_values: dict[str, pd.Series] = {}
    for col_name, (suffix, dim) in RESOURCE_COLUMNS.items():
        mask = prom_df["suffix"] == suffix
        if dim is not None:
            mask = mask & (prom_df["dimension"] == dim)
        resource_values[col_name] = prom_df.loc[mask].copy()

    # Parse condition timestamps
    started = pd.to_datetime(results_df["started_at"], utc=True)
    ended = pd.to_datetime(results_df["ended_at"], utc=True)

    # Pre-compute per resource column
    for col_name in RESOURCE_COLUMNS:
        results_df[f"{col_name}_mean"] = np.nan
        results_df[f"{col_name}_max"] = np.nan

    for idx in results_df.index:
        s, e = started[idx], ended[idx]
        if pd.isna(s) or pd.isna(e):
            continue

        for col_name, sub_df in resource_values.items():
            if sub_df.empty:
                continue
            sub_ts = sub_df["timestamp"].values
            lo = np.searchsorted(sub_ts, s.to_numpy(), side="left")
            hi = np.searchsorted(sub_ts, e.to_numpy(), side="right")
            if hi > lo:
                vals = sub_df["value"].values[lo:hi]
                results_df.at[idx, f"{col_name}_mean"] = np.nanmean(vals)
                results_df.at[idx, f"{col_name}_max"] = np.nanmax(vals)

    return results_df


def load_and_join(
    run_dirs: list[Path],
    use_prometheus: bool,
) -> tuple[pd.DataFrame, bool]:
    """Load results (and optionally prometheus) from one or more run dirs.

    Returns (df, has_prometheus).
    """
    frames = []
    for run_dir in run_dirs:
        jsonl = run_dir / "results.jsonl"
        if not jsonl.exists():
            continue
        raw = load_results_jsonl(jsonl)
        df = results_to_dataframe(raw)
        df["run_dir"] = run_dir.name

        if use_prometheus:
            prom = load_prometheus(run_dir)
            if prom is not None and not prom.empty:
                df = join_prometheus_to_conditions(df, prom)
                log.info(
                    "Joined %d prometheus rows to %d conditions for %s",
                    len(prom), len(df), run_dir.name,
                )

        frames.append(df)

    if not frames:
        log.error("No results found.")
        sys.exit(1)

    combined = pd.concat(frames, ignore_index=True)

    # Check if we actually got any resource data
    resource_cols = [f"{c}_mean" for c in RESOURCE_COLUMNS]
    has_prom = any(c in combined.columns and combined[c].notna().any() for c in resource_cols)

    return combined, has_prom


# ═══════════════════════════════════════════════════════════════════════════════
# Parameter count helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_param_billions(s: str) -> float | None:
    """Parse '7B' → 7.0, '1.5B' → 1.5, '268.10M' → 0.268, '?' → None."""
    if not s or s == "?":
        return None
    s = s.strip()
    m = re.match(r"^([\d.]+)[Bb]$", s)
    if m:
        return float(m.group(1))
    m = re.match(r"^([\d.]+)[Mm]$", s)
    if m:
        return float(m.group(1)) / 1000.0
    return None


def add_parameter_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Add param_count (str like '7B') and param_B (float) columns."""
    ollama_details = _fetch_ollama_model_details()
    models = df["model"].unique()
    mapping = {}
    for model in models:
        mapping[model] = resolve_parameter_count(model, ollama_details)
    df["param_count"] = df["model"].map(mapping)
    df["param_B"] = df["param_count"].map(_parse_param_billions)
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# Output helpers
# ═══════════════════════════════════════════════════════════════════════════════

def ensure_dirs(output_dir: Path) -> tuple[Path, Path]:
    """Create and return (figures_dir, tables_dir)."""
    fig_dir = output_dir / "figures"
    tbl_dir = output_dir / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tbl_dir.mkdir(parents=True, exist_ok=True)
    return fig_dir, tbl_dir


def save_fig(fig: plt.Figure, fig_dir: Path, name: str) -> None:
    """Save a figure as both PNG and PDF."""
    fig.savefig(fig_dir / f"{name}.png", dpi=FIG_DPI_PNG, bbox_inches="tight")
    fig.savefig(fig_dir / f"{name}.pdf", dpi=FIG_DPI_PDF, bbox_inches="tight")
    plt.close(fig)
    log.info("  Saved %s.png / .pdf", name)


def save_table(df: pd.DataFrame, tbl_dir: Path, name: str) -> None:
    """Save a DataFrame as CSV."""
    df.to_csv(tbl_dir / f"{name}.csv", index=False)
    log.info("  Saved %s.csv", name)


def _model_sort_key(df: pd.DataFrame) -> list[str]:
    """Return model names sorted by param_B (NaN last), then name."""
    tmp = df.drop_duplicates("model")[["model", "param_B"]].copy()
    tmp["sort_val"] = tmp["param_B"].fillna(1e9)
    tmp = tmp.sort_values(["sort_val", "model"])
    return tmp["model"].tolist()


def _short_name(model: str) -> str:
    """Abbreviate long model names for plot tick labels.

    Examples:
        'robbiemu/Salesforce_Llama-xLAM-2:8b-fc-r-q3_K_M' → 'xLAM-2:8b'
        'functiongemma:latest' → 'functiongemma'
        'mistral-nemo:12b' → 'mistral-nemo:12b'
    """
    # Strip user/org prefix
    if "/" in model:
        model = model.rsplit("/", 1)[-1]
    # Strip '_Llama-' style prefixes from HF-namespaced models
    if "_" in model and "-" in model:
        # e.g. 'Salesforce_Llama-xLAM-2:8b-fc-r-q3_K_M' → keep from last known model token
        parts = model.split("_", 1)
        if len(parts[0]) > 8:
            model = parts[1]
    # Strip ':latest' suffix (adds no info)
    if model.endswith(":latest"):
        model = model[: -len(":latest")]
    # Truncate quant suffixes after size tag  e.g. ':8b-fc-r-q3_K_M' → ':8b'
    m = re.match(r"^(.+?:\d+(?:\.\d+)?[bBmM])(?:[-_].+)?$", model)
    if m:
        model = m.group(1)
    return model


def _short_names(models: list[str]) -> dict[str, str]:
    """Build a {full_name: short_name} mapping, deduplicating if needed."""
    mapping = {m: _short_name(m) for m in models}
    # Handle collisions by falling back to full name
    seen: dict[str, list[str]] = {}
    for full, short in mapping.items():
        seen.setdefault(short, []).append(full)
    for short, fulls in seen.items():
        if len(fulls) > 1:
            for f in fulls:
                mapping[f] = f  # revert to full name
    return mapping


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1: Dataset Overview
# ═══════════════════════════════════════════════════════════════════════════════

def section_01_overview(df: pd.DataFrame, fig_dir: Path, tbl_dir: Path) -> None:
    log.info("Section 1: Dataset Overview")

    models = _model_sort_key(df)
    rows = []
    for model in models:
        sub = df[df["model"] == model]
        param = sub["param_count"].iloc[0] if "param_count" in sub.columns else "?"
        n_conditions = len(sub)
        domains = sub["domain"].nunique()
        granularities = sorted(sub["granularity"].unique())
        n_errors = sub["error"].notna().sum()
        n_timeouts = (sub["timed_out"] == True).sum()  # noqa: E712
        mean_completion = sub["task_completion"].mean()
        mean_f1 = sub["tool_selection_f1"].mean()
        rows.append({
            "model": model,
            "params": param,
            "conditions": n_conditions,
            "domains": domains,
            "granularities": ", ".join(granularities),
            "errors": n_errors,
            "error_rate": f"{n_errors / n_conditions:.1%}" if n_conditions else "N/A",
            "timeouts": n_timeouts,
            "timeout_rate": f"{n_timeouts / n_conditions:.1%}" if n_conditions else "N/A",
            "mean_task_completion": f"{mean_completion:.3f}",
            "mean_f1": f"{mean_f1:.3f}",
        })

    overview = pd.DataFrame(rows)
    save_table(overview, tbl_dir, "01_dataset_overview")

    # Also print to console
    print("\n" + "=" * 80)
    print("DATASET OVERVIEW")
    print("=" * 80)
    print(overview.to_string(index=False))
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2: Per-Condition Resource Attribution (heatmaps)
# ═══════════════════════════════════════════════════════════════════════════════

def section_02_resource_heatmap(df: pd.DataFrame, fig_dir: Path, tbl_dir: Path) -> None:
    log.info("Section 2: Per-Condition Resource Heatmap")

    models = _model_sort_key(df)
    resource_metrics = [
        ("gpu_util_pct_mean", "GPU Util (%)"),
        ("vram_used_B_mean", "VRAM Used (GB)"),
        ("gpu_power_W_mean", "GPU Power (W)"),
        ("cpu_user_pct_mean", "CPU User (%)"),
        ("ram_used_MiB_mean", "RAM Used (MiB)"),
        ("rapl_power_W_mean", "RAPL Power (W)"),
        ("pdu_power_W_mean", "PDU Power (W)"),
    ]

    # Filter to metrics that have data
    resource_metrics = [(c, l) for c, l in resource_metrics if c in df.columns and df[c].notna().any()]

    if not resource_metrics:
        log.warning("  No resource metrics available — skipping section 2.")
        return

    n_metrics = len(resource_metrics)
    snames = _short_names(models)
    fig, axes = plt.subplots(1, n_metrics, figsize=(3.5 * n_metrics + 1.5, max(5, 0.4 * len(models))))

    if n_metrics == 1:
        axes = [axes]

    for i, (ax, (col, label)) in enumerate(zip(axes, resource_metrics)):
        pivot = df.pivot_table(
            values=col, index="model", columns="granularity", aggfunc="mean",
        )
        # Convert VRAM from bytes to GB for readability
        if "vram" in col.lower() and "B" in col:
            pivot = pivot / 1e9

        # Reorder rows and use short names
        ordered = [m for m in models if m in pivot.index]
        pivot = pivot.reindex(ordered)
        pivot.index = [snames.get(m, m) for m in pivot.index]

        sns.heatmap(pivot, annot=True, fmt=".1f", cmap="YlOrRd", ax=ax, cbar_kws={"shrink": 0.6})
        ax.set_title(label, fontsize=10)
        ax.set_xlabel("")
        # Only show y-tick labels on the leftmost subplot
        if i == 0:
            ax.set_ylabel("")
        else:
            ax.set_ylabel("")
            ax.set_yticks([])

    fig.suptitle("Mean Resource Usage per Model × Granularity", fontsize=13, y=1.02)
    fig.tight_layout()
    save_fig(fig, fig_dir, "02_resource_heatmap")

    # Save underlying table
    tbl_rows = []
    for model in models:
        for gran in GRAN_COLORS:
            sub = df[(df["model"] == model) & (df["granularity"] == gran)]
            if sub.empty:
                continue
            row = {"model": model, "granularity": gran}
            for col, label in resource_metrics:
                row[label] = sub[col].mean()
            tbl_rows.append(row)
    save_table(pd.DataFrame(tbl_rows), tbl_dir, "02_resource_attribution")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3: Model Size vs Performance (scaling laws)
# ═══════════════════════════════════════════════════════════════════════════════

def _scaling_plot(
    df: pd.DataFrame,
    y_col: str,
    y_label: str,
    fig_dir: Path,
    fig_name: str,
) -> None:
    """Generic scatter + error bar for param_B (log) vs a performance metric."""
    sub = df.dropna(subset=["param_B", y_col]).copy()
    if sub.empty:
        log.warning("  No data for %s — skipping.", y_col)
        return

    snames = _short_names(sub["model"].unique().tolist())
    fig, ax = plt.subplots(figsize=(8, 5))

    # Collect per-model midpoints for annotation (label once, not per granularity)
    model_points: dict[str, tuple[float, float]] = {}  # model → (x, y_mid)

    for gran, color in GRAN_COLORS.items():
        g = sub[sub["granularity"] == gran]
        if g.empty:
            continue
        grouped = g.groupby("model").agg(
            x=("param_B", "first"),
            y_mean=(y_col, "mean"),
            y_std=(y_col, "std"),
        ).reset_index()

        ax.errorbar(
            grouped["x"], grouped["y_mean"], yerr=grouped["y_std"],
            fmt="o", color=color, label=gran, capsize=3, markersize=6,
        )

        for _, row in grouped.iterrows():
            if row["model"] in model_points:
                prev_x, prev_y = model_points[row["model"]]
                model_points[row["model"]] = (prev_x, (prev_y + row["y_mean"]) / 2)
            else:
                model_points[row["model"]] = (row["x"], row["y_mean"])

    # Annotate once per model using adjustText for repulsion
    texts = []
    for model, (mx, my) in model_points.items():
        texts.append(ax.text(mx, my, snames.get(model, model), fontsize=7, alpha=0.8))

    ax.set_xscale("log")
    ax.set_xlabel("Parameter Count (Billions)")
    ax.set_ylabel(y_label)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Spearman correlation (pooled)
    rho, pval = stats.spearmanr(sub["param_B"], sub[y_col])
    ax.set_title(f"{y_label} vs Model Size  (Spearman ρ={rho:.3f}, p={pval:.3g})")

    adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle="-", color="gray", alpha=0.5))

    fig.tight_layout()
    save_fig(fig, fig_dir, fig_name)


def section_03_scaling_performance(df: pd.DataFrame, fig_dir: Path, tbl_dir: Path) -> None:
    log.info("Section 3: Model Size vs Performance")

    _scaling_plot(df, "task_completion", "Task Completion", fig_dir, "03a_scaling_task_completion")
    _scaling_plot(df, "tool_selection_f1", "Tool Selection F1", fig_dir, "03b_scaling_f1")
    _scaling_plot(df, "argument_accuracy", "Argument Accuracy", fig_dir, "03c_scaling_argument_accuracy")

    # Summary table
    sub = df.dropna(subset=["param_B"]).copy()
    if sub.empty:
        return
    summary = sub.groupby(["model", "granularity", "param_B"]).agg(
        task_completion_mean=("task_completion", "mean"),
        task_completion_std=("task_completion", "std"),
        f1_mean=("tool_selection_f1", "mean"),
        f1_std=("tool_selection_f1", "std"),
        arg_acc_mean=("argument_accuracy", "mean"),
        arg_acc_std=("argument_accuracy", "std"),
    ).reset_index()
    save_table(summary, tbl_dir, "03_scaling_performance")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4: Model Size vs Resource Cost
# ═══════════════════════════════════════════════════════════════════════════════

def section_04_scaling_resources(df: pd.DataFrame, fig_dir: Path, tbl_dir: Path) -> None:
    log.info("Section 4: Model Size vs Resource Cost")

    _scaling_plot(df, "wall_time_seconds", "Wall Time (s)", fig_dir, "04a_scaling_walltime")

    if "gpu_power_W_mean" in df.columns and df["gpu_power_W_mean"].notna().any():
        _scaling_plot(df, "gpu_power_W_mean", "GPU Power (W)", fig_dir, "04b_scaling_gpu_power")

    if "vram_used_B_mean" in df.columns and df["vram_used_B_mean"].notna().any():
        df_tmp = df.copy()
        df_tmp["vram_used_GB_mean"] = df_tmp["vram_used_B_mean"] / 1e9
        _scaling_plot(df_tmp, "vram_used_GB_mean", "VRAM Used (GB)", fig_dir, "04c_scaling_vram")

    # Summary table
    resource_cols = ["wall_time_seconds"]
    for c in ["gpu_power_W_mean", "vram_used_B_mean", "cpu_user_pct_mean", "rapl_power_W_mean"]:
        if c in df.columns and df[c].notna().any():
            resource_cols.append(c)

    sub = df.dropna(subset=["param_B"]).copy()
    if sub.empty:
        return
    agg_dict = {c: ["mean", "std"] for c in resource_cols if c in sub.columns}
    if not agg_dict:
        return
    summary = sub.groupby(["model", "granularity", "param_B"]).agg(agg_dict).reset_index()
    summary.columns = ["_".join(c).rstrip("_") for c in summary.columns]
    save_table(summary, tbl_dir, "04_scaling_resources")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5: Granularity Impact (primitive vs composite)
# ═══════════════════════════════════════════════════════════════════════════════

def section_05_granularity(
    df: pd.DataFrame, fig_dir: Path, tbl_dir: Path, has_prometheus: bool,
) -> None:
    log.info("Section 5: Granularity Impact")

    models = _model_sort_key(df)
    snames = _short_names(models)
    perf_cols = ["task_completion", "tool_selection_f1", "argument_accuracy"]

    # --- 5a: Performance ---
    fig, axes = plt.subplots(1, len(perf_cols), figsize=(5 * len(perf_cols), 5))
    granularities_present = sorted(df["granularity"].unique())
    for ax, col in zip(axes, perf_cols):
        plot_data = []
        for model in models:
            for gran in granularities_present:
                sub = df[(df["model"] == model) & (df["granularity"] == gran)]
                if sub.empty:
                    continue
                plot_data.append({
                    "model": snames.get(model, model),
                    "granularity": gran,
                    "value": sub[col].mean(),
                })
        pdata = pd.DataFrame(plot_data)
        if pdata.empty:
            continue
        sns.barplot(data=pdata, x="model", y="value", hue="granularity",
                    palette=GRAN_COLORS, ax=ax,
                    order=[snames.get(m, m) for m in models])
        ax.set_title(col.replace("_", " ").title())
        ax.tick_params(axis="x", rotation=45)
        for lbl in ax.get_xticklabels():
            lbl.set_ha("right")
            lbl.set_fontsize(8)
        ax.set_ylabel("")
        ax.legend(fontsize=8)

    # Wilcoxon signed-rank test per metric (primitive vs each composite level)
    stats_rows = []
    for col in perf_cols:
        for comp_gran in [g for g in granularities_present if g != "primitive"]:
            prim_vals, comp_vals = [], []
            for model in models:
                p = df[(df["model"] == model) & (df["granularity"] == "primitive")][col].mean()
                c = df[(df["model"] == model) & (df["granularity"] == comp_gran)][col].mean()
                if not np.isnan(p) and not np.isnan(c):
                    prim_vals.append(p)
                    comp_vals.append(c)
            if len(prim_vals) >= 5:
                stat, pval = stats.wilcoxon(prim_vals, comp_vals)
                stats_rows.append({"metric": col, "comparison": f"primitive_vs_{comp_gran}",
                                   "wilcoxon_stat": stat, "p_value": pval,
                                   "n_models": len(prim_vals)})

    fig.suptitle("Granularity Impact on Performance", fontsize=13, y=1.02)
    fig.tight_layout()
    save_fig(fig, fig_dir, "05a_granularity_performance")

    if stats_rows:
        save_table(pd.DataFrame(stats_rows), tbl_dir, "05_granularity_wilcoxon")

    # --- 5b: Resources ---
    if not has_prometheus:
        log.warning("  Skipping 5b (resource comparison) — no prometheus data.")
        return

    res_cols = [
        ("gpu_util_pct_mean", "GPU Util (%)"),
        ("gpu_power_W_mean", "GPU Power (W)"),
        ("cpu_user_pct_mean", "CPU User (%)"),
        ("rapl_power_W_mean", "RAPL Power (W)"),
    ]
    res_cols = [(c, l) for c, l in res_cols if c in df.columns and df[c].notna().any()]
    if not res_cols:
        return

    fig, axes = plt.subplots(1, len(res_cols), figsize=(5 * len(res_cols), 5))
    if len(res_cols) == 1:
        axes = [axes]

    for ax, (col, label) in zip(axes, res_cols):
        plot_data = []
        for model in models:
            for gran in granularities_present:
                sub = df[(df["model"] == model) & (df["granularity"] == gran)]
                if sub.empty:
                    continue
                plot_data.append({
                    "model": snames.get(model, model),
                    "granularity": gran,
                    "value": sub[col].mean(),
                })
        pdata = pd.DataFrame(plot_data)
        if pdata.empty:
            continue
        sns.barplot(data=pdata, x="model", y="value", hue="granularity",
                    palette=GRAN_COLORS, ax=ax,
                    order=[snames.get(m, m) for m in models])
        ax.set_title(label)
        ax.tick_params(axis="x", rotation=45)
        for lbl in ax.get_xticklabels():
            lbl.set_ha("right")
            lbl.set_fontsize(8)
        ax.set_ylabel("")
        ax.legend(fontsize=8)

    fig.suptitle("Granularity Impact on Resource Usage", fontsize=13, y=1.02)
    fig.tight_layout()
    save_fig(fig, fig_dir, "05b_granularity_resources")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 6: Efficiency Frontiers
# ═══════════════════════════════════════════════════════════════════════════════

def _pareto_front(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Return boolean mask of Pareto-optimal points (maximize both)."""
    n = len(xs)
    mask = np.ones(n, dtype=bool)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if xs[j] >= xs[i] and ys[j] >= ys[i] and (xs[j] > xs[i] or ys[j] > ys[i]):
                mask[i] = False
                break
    return mask


def section_06_efficiency(df: pd.DataFrame, fig_dir: Path, tbl_dir: Path) -> None:
    log.info("Section 6: Efficiency Frontiers")

    models = _model_sort_key(df)

    # Derived: F1/watt, completion/second
    has_power = "gpu_power_W_mean" in df.columns and df["gpu_power_W_mean"].notna().any()
    has_rapl = "rapl_power_W_mean" in df.columns and df["rapl_power_W_mean"].notna().any()

    # Compute per-model means
    eff_rows = []
    for model in models:
        for gran in sorted(df["granularity"].unique()):
            sub = df[(df["model"] == model) & (df["granularity"] == gran)]
            if sub.empty:
                continue
            row = {
                "model": model,
                "granularity": gran,
                "f1": sub["tool_selection_f1"].mean(),
                "completion": sub["task_completion"].mean(),
                "wall_time": sub["wall_time_seconds"].mean(),
            }
            if has_power:
                row["gpu_power_W"] = sub["gpu_power_W_mean"].mean()
            if has_rapl:
                row["rapl_power_W"] = sub["rapl_power_W_mean"].mean()

            # Energy = power × time (joules)
            power = row.get("gpu_power_W") or row.get("rapl_power_W")
            if power and not np.isnan(power) and row["wall_time"] > 0:
                row["energy_J"] = power * row["wall_time"]
                row["f1_per_watt"] = row["f1"] / power if power > 0 else np.nan
            row["completion_per_sec"] = row["completion"] / row["wall_time"] if row["wall_time"] > 0 else 0

            eff_rows.append(row)

    eff = pd.DataFrame(eff_rows)
    if eff.empty:
        log.warning("  No efficiency data — skipping.")
        return

    save_table(eff, tbl_dir, "06_efficiency_metrics")

    # --- 6a: Pareto — F1 vs power ---
    power_col = "gpu_power_W" if "gpu_power_W" in eff.columns and eff["gpu_power_W"].notna().any() else (
        "rapl_power_W" if "rapl_power_W" in eff.columns and eff["rapl_power_W"].notna().any() else None
    )

    snames = _short_names(models)
    from matplotlib.lines import Line2D
    _pareto_legend = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=GRAN_COLORS["primitive"],
               markersize=8, label="primitive"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=GRAN_COLORS["composite_4"],
               markersize=8, label="composite_4"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="gray",
               markersize=12, label="Pareto optimal"),
    ]

    if power_col and "f1_per_watt" in eff.columns:
        sub_eff = eff.dropna(subset=[power_col, "f1"])
        if not sub_eff.empty:
            fig, ax = plt.subplots(figsize=(8, 6))
            xs = sub_eff["f1"].values
            ys = -sub_eff[power_col].values
            front = _pareto_front(xs, ys)

            texts = []
            for i, (_, row) in enumerate(sub_eff.iterrows()):
                color = GRAN_COLORS.get(row["granularity"], "gray")
                marker = "*" if front[i] else "o"
                size = 150 if front[i] else 60
                ax.scatter(row[power_col], row["f1"], c=[color], marker=marker,
                           s=size, edgecolors="black" if front[i] else "none", linewidths=1)
                texts.append(ax.text(
                    row[power_col], row["f1"],
                    snames.get(row["model"], row["model"]), fontsize=7, alpha=0.8,
                ))

            front_pts = sub_eff[front].sort_values(power_col)
            if len(front_pts) > 1:
                ax.plot(front_pts[power_col], front_pts["f1"], "k--", alpha=0.4, label="Pareto frontier")

            ax.set_xlabel(f"Power ({power_col.replace('_', ' ')})")
            ax.set_ylabel("Tool Selection F1")
            ax.set_title("Efficiency Frontier: F1 vs Power")
            ax.legend(handles=_pareto_legend, fontsize=8)
            ax.grid(True, alpha=0.3)
            adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle="-", color="gray", alpha=0.5))
            fig.tight_layout()
            save_fig(fig, fig_dir, "06a_pareto_f1_power")

    # --- 6b: Pareto — completion vs wall time ---
    sub_eff = eff.dropna(subset=["wall_time", "completion"])
    if not sub_eff.empty:
        fig, ax = plt.subplots(figsize=(8, 6))
        xs = sub_eff["completion"].values
        ys = -sub_eff["wall_time"].values
        front = _pareto_front(xs, ys)

        texts = []
        for i, (_, row) in enumerate(sub_eff.iterrows()):
            color = GRAN_COLORS.get(row["granularity"], "gray")
            marker = "*" if front[i] else "o"
            size = 150 if front[i] else 60
            ax.scatter(row["wall_time"], row["completion"], c=[color], marker=marker,
                       s=size, edgecolors="black" if front[i] else "none", linewidths=1)
            texts.append(ax.text(
                row["wall_time"], row["completion"],
                snames.get(row["model"], row["model"]), fontsize=7, alpha=0.8,
            ))

        front_pts = sub_eff[front].sort_values("wall_time")
        if len(front_pts) > 1:
            ax.plot(front_pts["wall_time"], front_pts["completion"], "k--", alpha=0.4,
                    label="Pareto frontier")

        ax.set_xlabel("Wall Time (s)")
        ax.set_ylabel("Task Completion")
        ax.set_title("Efficiency Frontier: Completion vs Time")
        handles = _pareto_legend
        ax.legend(handles=handles, fontsize=8)
        ax.grid(True, alpha=0.3)
        adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle="-", color="gray", alpha=0.5))
        fig.tight_layout()
        save_fig(fig, fig_dir, "06b_pareto_completion_time")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 7: Edge Feasibility Projections
# ═══════════════════════════════════════════════════════════════════════════════

def _estimate_model_memory_gb(param_B: float, model_name: str) -> float:
    """Estimate total model memory (weights + KV cache overhead) in GB.

    Uses quantization level detected from the model name, falling back to Q4
    (the typical Ollama default).  Adds a conservative KV-cache overhead.
    """
    # Try to detect quantization from the model name
    name_upper = model_name.upper()
    bpp = QUANT_BYTES_PER_PARAM["default"]
    for quant_tag, bytes_pp in QUANT_BYTES_PER_PARAM.items():
        if quant_tag != "default" and quant_tag.upper() in name_upper:
            bpp = bytes_pp
            break

    weight_bytes = param_B * 1e9 * bpp
    total_bytes = weight_bytes * (1 + _KV_CACHE_OVERHEAD)
    return total_bytes / (1024 ** 3)


def section_07_feasibility(df: pd.DataFrame, fig_dir: Path, tbl_dir: Path) -> None:
    log.info("Section 7: Edge Feasibility Projections")

    models = _model_sort_key(df)

    # Estimate per-model memory from parameter counts instead of system-wide
    # Prometheus metrics (which reflect total host usage, not the model alone).
    model_resources: dict[str, dict[str, float]] = {}
    for model in models:
        sub = df[df["model"] == model]
        param_B = sub["param_B"].dropna().iloc[0] if "param_B" in sub.columns else None
        res: dict[str, float] = {}
        if param_B is not None and not np.isnan(param_B):
            mem_gb = _estimate_model_memory_gb(param_B, model)
            res["model_mem_GB"] = mem_gb
        # GPU power: use measured per-model mean (not system-wide RAPL)
        if "gpu_power_W_mean" in sub.columns:
            vals = sub["gpu_power_W_mean"].dropna()
            if len(vals):
                res["gpu_power_mean_W"] = vals.mean()
        model_resources[model] = res

    # Build feasibility matrix
    # NOTE: Power feasibility is only checked against nc16 (the measurement host).
    # Cross-device power projections are not valid because GPU idle power and
    # thermal characteristics differ fundamentally across hardware platforms.
    # For Xavier / RPi5 we check memory fit only.
    fit_labels = {2: "fit", 1: "tight", 0: "no-fit"}
    rows = []
    matrix = {}

    MEASUREMENT_HOST = "nc16"  # device where Prometheus data was collected

    for model in models:
        res = model_resources.get(model, {})
        mem_gb = res.get("model_mem_GB")
        gpu_power = res.get("gpu_power_mean_W")
        matrix[model] = {}
        for dev_name, profile in DEVICE_PROFILES.items():
            issues = []

            # Memory check: model must fit in VRAM (GPU devices) or RAM (CPU-only)
            if mem_gb is not None:
                if profile["vram_GB"] > 0:
                    # GPU device — model loaded into VRAM
                    if mem_gb > profile["vram_GB"]:
                        issues.append(f"VRAM: {mem_gb:.1f}>{profile['vram_GB']}GB")
                    elif mem_gb > 0.9 * profile["vram_GB"]:
                        issues.append(f"VRAM tight ({mem_gb:.1f}/{profile['vram_GB']}GB)")
                else:
                    # CPU-only device — model loaded into system RAM
                    if mem_gb > profile["ram_GB"]:
                        issues.append(f"RAM: {mem_gb:.1f}>{profile['ram_GB']}GB")
                    elif mem_gb > 0.9 * profile["ram_GB"]:
                        issues.append(f"RAM tight ({mem_gb:.1f}/{profile['ram_GB']}GB)")

            # Power check: only valid for the measurement host (nc16)
            if dev_name == MEASUREMENT_HOST:
                if gpu_power is not None and not np.isnan(gpu_power):
                    if gpu_power > profile["power_budget_W"]:
                        issues.append(f"power: {gpu_power:.0f}>{profile['power_budget_W']}W")

            if any(">" in i for i in issues):
                fit = 0
            elif issues:
                fit = 1
            else:
                fit = 2

            matrix[model][dev_name] = fit
            rows.append({
                "model": model, "device": dev_name, "fit": fit_labels[fit],
                "issues": "; ".join(issues) if issues else "OK",
            })

    feasibility_df = pd.DataFrame(rows)
    save_table(feasibility_df, tbl_dir, "07_edge_feasibility")

    # Heatmap
    snames = _short_names(models)
    devices = list(DEVICE_PROFILES.keys())
    heat_data = pd.DataFrame(
        [[matrix.get(m, {}).get(d, np.nan) for d in devices] for m in models],
        index=[snames.get(m, m) for m in models], columns=devices,
    )

    fig, ax = plt.subplots(figsize=(6, max(4, 0.4 * len(models))))
    cmap = matplotlib.colors.ListedColormap(["#ff6b6b", "#ffd93d", "#6bcf7f"])
    bounds = [-0.5, 0.5, 1.5, 2.5]
    norm = matplotlib.colors.BoundaryNorm(bounds, cmap.N)

    sns.heatmap(
        heat_data, annot=heat_data.replace({0: "NO", 1: "TIGHT", 2: "FIT"}),
        fmt="", cmap=cmap, norm=norm, ax=ax, linewidths=0.5,
        cbar=False,
    )
    ax.set_title("Edge Feasibility Matrix")
    ax.set_ylabel("")

    fig.tight_layout()
    save_fig(fig, fig_dir, "07_edge_feasibility_matrix")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 8: Domain Analysis
# ═══════════════════════════════════════════════════════════════════════════════

def section_08_domain(
    df: pd.DataFrame, fig_dir: Path, tbl_dir: Path, has_prometheus: bool,
) -> None:
    log.info("Section 8: Domain Analysis")

    domains = sorted(df["domain"].unique())
    models = _model_sort_key(df)

    # --- 8a: Performance by domain ---
    perf_cols = ["task_completion", "tool_selection_f1", "argument_accuracy"]
    fig, axes = plt.subplots(1, len(perf_cols), figsize=(5 * len(perf_cols), 5))
    for ax, col in zip(axes, perf_cols):
        domain_data = df.groupby("domain")[col].agg(["mean", "std"]).reindex(domains)
        ax.bar(domains, domain_data["mean"], yerr=domain_data["std"],
               capsize=3, color=PALETTE[2], alpha=0.8)
        ax.set_title(col.replace("_", " ").title())
        ax.tick_params(axis="x", rotation=45)
        for lbl in ax.get_xticklabels():
            lbl.set_ha("right")
        ax.set_ylim(0, 1.05)

    fig.suptitle("Performance by Domain (all models pooled)", fontsize=13, y=1.02)
    fig.tight_layout()
    save_fig(fig, fig_dir, "08a_domain_performance")

    # Domain summary table
    domain_summary = df.groupby("domain").agg(
        n_conditions=("model", "count"),
        task_completion_mean=("task_completion", "mean"),
        task_completion_std=("task_completion", "std"),
        f1_mean=("tool_selection_f1", "mean"),
        arg_acc_mean=("argument_accuracy", "mean"),
        wall_time_mean=("wall_time_seconds", "mean"),
    ).reset_index()
    save_table(domain_summary, tbl_dir, "08_domain_summary")

    # --- 8b: Model × Domain heatmap ---
    snames = _short_names(models)
    pivot = df.pivot_table(values="task_completion", index="model", columns="domain", aggfunc="mean")
    ordered = [m for m in models if m in pivot.index]
    pivot = pivot.reindex(ordered)
    pivot.index = [snames.get(m, m) for m in pivot.index]

    fig, ax = plt.subplots(figsize=(max(6, len(domains) * 1.2), max(4, 0.4 * len(ordered))))
    sns.heatmap(pivot, annot=True, fmt=".2f", cmap="RdYlGn", vmin=0, vmax=1,
                ax=ax, linewidths=0.5)
    ax.set_title("Task Completion: Model × Domain")
    ax.set_ylabel("")
    fig.tight_layout()
    save_fig(fig, fig_dir, "08b_domain_model_heatmap")


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="MCP-GRANITE analysis — produces research figures and tables.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-r", "--run-dir",
        type=Path,
        default=None,
        help="Single run directory to analyse (default: all runs under results-root).",
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=None,
        help="Top-level directory containing run_* subdirs (default: results/).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis_output"),
        help="Output directory for figures and tables (default: analysis_output/).",
    )
    parser.add_argument(
        "--no-prometheus",
        action="store_true",
        help="Skip prometheus data loading and resource analysis sections.",
    )
    args = parser.parse_args()

    # Resolve run directories
    if args.run_dir:
        run_dir = args.run_dir.resolve()
        if not run_dir.is_dir():
            log.error("Run directory does not exist: %s", run_dir)
            sys.exit(1)
        run_dirs = [run_dir]
    else:
        results_root = (args.results_root or Path("results")).resolve()
        if not results_root.is_dir():
            log.error("No results directory found: %s", results_root)
            sys.exit(1)
        run_dirs = sorted(
            [d for d in results_root.iterdir() if d.is_dir() and d.name.startswith("run_")]
        )
        if not run_dirs:
            log.error("No run_* directories found under %s.", results_root)
            sys.exit(1)

    use_prometheus = not args.no_prometheus

    # Load and join
    log.info("Loading data from %d run(s)...", len(run_dirs))
    df, has_prometheus = load_and_join(run_dirs, use_prometheus)
    log.info("Loaded %d condition results.", len(df))

    # Add parameter counts
    df = add_parameter_counts(df)
    log.info(
        "Models: %s", ", ".join(f"{m} ({df[df['model']==m]['param_count'].iloc[0]})"
                                for m in _model_sort_key(df))
    )

    if has_prometheus:
        log.info("Prometheus resource data: AVAILABLE")
    else:
        log.info("Prometheus resource data: NOT AVAILABLE")

    # Output dirs
    fig_dir, tbl_dir = ensure_dirs(args.output_dir)

    # Run sections
    print("\n" + "=" * 80)
    print("  MCP-GRANITE Analysis")
    print("=" * 80)

    # Section 1: always runs
    section_01_overview(df, fig_dir, tbl_dir)

    # Section 2: requires prometheus
    if has_prometheus:
        section_02_resource_heatmap(df, fig_dir, tbl_dir)
    else:
        log.warning("Skipping section 2 (resource heatmap) — no prometheus data.")

    # Section 3: always runs (but needs param_B for scaling)
    section_03_scaling_performance(df, fig_dir, tbl_dir)

    # Section 4: requires prometheus for resource plots (walltime always available)
    if has_prometheus:
        section_04_scaling_resources(df, fig_dir, tbl_dir)
    else:
        log.warning("Skipping section 4 (scaling resources) — no prometheus data.")

    # Section 5: 5a always, 5b requires prometheus
    section_05_granularity(df, fig_dir, tbl_dir, has_prometheus)

    # Section 6: requires prometheus for power-based efficiency
    if has_prometheus:
        section_06_efficiency(df, fig_dir, tbl_dir)
    else:
        log.warning("Skipping section 6 (efficiency frontiers) — no prometheus data.")

    # Section 7: requires prometheus
    if has_prometheus:
        section_07_feasibility(df, fig_dir, tbl_dir)
    else:
        log.warning("Skipping section 7 (edge feasibility) — no prometheus data.")

    # Section 8: always runs
    section_08_domain(df, fig_dir, tbl_dir, has_prometheus)

    print("\n" + "=" * 80)
    print(f"  Analysis complete. Output in: {args.output_dir}/")
    print(f"  Figures: {fig_dir}/")
    print(f"  Tables:  {tbl_dir}/")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
