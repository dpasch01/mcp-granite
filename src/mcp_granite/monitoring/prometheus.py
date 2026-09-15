"""Prometheus metrics collection for MCP-GRANITE experiment runs."""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

PROMETHEUS_CSV = "prometheus.csv"

CSV_COLUMNS = [
    "timestamp",
    "metric",
    "label",
    "value",
]

# Curated metric suffixes relevant to LLM inference benchmarking on edge devices.
# These are matched against the tail of each Prometheus metric name (after the hostname
# segment), so they work across hosts (nc16, xavier, etc.) without modification.
DEFAULT_METRIC_SUFFIXES: list[str] = [
    # --- GPU compute & memory ---
    "nvidia_smi_gpu_utilization_percent_average",
    "nvidia_smi_gpu_memory_utilization_percent_average",
    "nvidia_smi_gpu_frame_buffer_memory_usage_B_average",
    "nvidia_smi_gpu_bar1_memory_usage_B_average",
    "nvidia_smi_gpu_clock_freq_MHz_average",
    "nvidia_smi_gpu_performance_state_state_average",
    # --- GPU power & thermal ---
    "nvidia_smi_gpu_power_draw_Watts_average",
    "nvidia_smi_gpu_temperature_Celsius_average",
    # --- GPU I/O ---
    "nvidia_smi_gpu_pcie_bandwidth_usage_B_persec_average",
    "nvidia_smi_gpu_pcie_bandwidth_utilization_percentage_average",
    # --- System CPU ---
    "system_cpu_percentage_average",
    "system_load_load_average",
    "system_cpu_some_pressure_percentage_average",
    # --- System memory ---
    "system_ram_MiB_average",
    "mem_available_MiB_average",
    "mem_committed_MiB_average",
    "mem_swap_MiB_average",
    "mem_swapio_KiB_persec_average",
    "mem_pgfaults_faults_persec_average",
    "mem_reclaiming_MiB_average",
    "system_memory_some_pressure_percentage_average",
    "system_memory_full_pressure_percentage_average",
    "system_pgpgio_KiB_persec_average",
    # --- System power ---
    "cpu_powercap_intel_rapl_zone_Watts_average",
    "cpu_powercap_intel_rapl_subzones_Watts_average",
    "snmp_snmp_r4spdu8_power_W_average",
    "snmp_snmp_r4spdu8_energy_kWh_average",
    "snmp_snmp_r4spdu8_current_A_average",
    # --- System I/O & network ---
    "system_io_KiB_persec_average",
    "system_net_kilobits_persec_average",
    # --- System thermal ---
    "system_hw_sensor_temperature_input_degrees_Celsius_average",
    # --- Container memory (cadvisor) ---
    "prometheus_cadvisor_container_cpu_usage_seconds_total_seconds_average",
    "prometheus_cadvisor_container_memory_usage_bytes_bytes_average",
    "prometheus_cadvisor_container_memory_working_set_bytes_bytes_average",
    "prometheus_cadvisor_container_memory_rss_rss_average",
    "prometheus_cadvisor_container_memory_cache_cache_average",
    "prometheus_cadvisor_container_memory_swap_swap_average",
    "prometheus_cadvisor_container_memory_mapped_file_file_average",
    "prometheus_cadvisor_container_memory_max_usage_bytes_bytes_average",
    "prometheus_cadvisor_container_memory_failcnt_failcnt_persec_average",
    "prometheus_cadvisor_container_memory_failures_total_failures_persec_average",
]


class PrometheusClient:
    """Thin wrapper around prometheus_pandas for fetching range metrics."""

    def __init__(self, url: str, step: str = "5s") -> None:
        from prometheus_pandas import query

        self._prom = query.Prometheus(url)
        self._step = step

    def discover_metrics(self) -> list[str]:
        """Return all metric names from the Prometheus instance."""
        import requests

        resp = requests.get(f"{self._prom.api_url}/api/v1/label/__name__/values")
        resp.raise_for_status()
        body = resp.json()
        return sorted(body.get("data", []))

    def discover_curated_metrics(self, hostname: str | None = None) -> list[str]:
        """Return only the curated metrics relevant to LLM benchmarking.

        Filters all discovered metrics by hostname (default: ``socket.gethostname()``)
        and the suffixes in ``DEFAULT_METRIC_SUFFIXES``.
        """
        import socket

        hostname = hostname or socket.gethostname()
        host_pattern = f"_{hostname}_"
        suffix_set = set(DEFAULT_METRIC_SUFFIXES)

        all_metrics = self.discover_metrics()
        curated = []
        for m in all_metrics:
            if host_pattern not in m:
                continue
            _, _, suffix = m.partition(host_pattern)
            if suffix in suffix_set:
                curated.append(m)
        return sorted(curated)

    def fetch_run_timeseries(
        self,
        started_at: str,
        ended_at: str,
        metrics: list[str] | None = None,
        max_chunk_seconds: int = 7200,
    ) -> list[dict[str, str]]:
        """Fetch raw time-series data for the entire run window.

        Returns a list of row dicts ready for CSV writing, with columns:
        ``timestamp``, ``metric``, ``label``, ``value``.

        If *metrics* is ``None``, the curated metric list is used.

        For long time ranges, the query is automatically split into chunks of
        *max_chunk_seconds* (default 2 hours) to avoid Prometheus query limits.
        Results from all chunks are aggregated into a single list.
        """
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at)

        if metrics is None:
            metrics = self.discover_curated_metrics()

        # Build time-range chunks
        total_seconds = (end - start).total_seconds()
        chunk_delta = timedelta(seconds=max_chunk_seconds)
        chunks: list[tuple[datetime, datetime]] = []
        chunk_start = start
        while chunk_start < end:
            chunk_end = min(chunk_start + chunk_delta, end)
            chunks.append((chunk_start, chunk_end))
            chunk_start = chunk_end

        if len(chunks) > 1:
            logger.info(
                "Time range %.1fh exceeds chunk limit (%ds), splitting into %d chunks.",
                total_seconds / 3600,
                max_chunk_seconds,
                len(chunks),
            )

        rows: list[dict[str, str]] = []
        for metric in metrics:
            for chunk_idx, (c_start, c_end) in enumerate(chunks):
                try:
                    df = self._prom.query_range(metric, c_start, c_end, self._step)
                    if df.empty:
                        continue

                    for col in df.columns:
                        label_key = str(col) if col != metric else "{}"
                        for ts, val in df[col].items():
                            rows.append(
                                {
                                    "timestamp": str(ts),
                                    "metric": metric,
                                    "label": label_key,
                                    "value": str(val),
                                }
                            )
                except Exception:
                    logger.warning(
                        "Failed to fetch metric %r chunk %d/%d, skipping.",
                        metric,
                        chunk_idx + 1,
                        len(chunks),
                        exc_info=True,
                    )

        return rows


def save_prometheus_csv(
    rows: list[dict[str, str]],
    output_dir: Path,
) -> Path:
    """Write time-series rows to ``prometheus.csv`` in *output_dir*.

    Overwrites any existing file (this is a full-run fetch, not incremental).
    Returns the path to the written CSV.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / PROMETHEUS_CSV

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return csv_path


def get_run_time_window(results: list[dict]) -> tuple[str, str] | None:
    """Extract the earliest started_at and latest ended_at from results.

    Returns ``(started_at, ended_at)`` or ``None`` if no valid timestamps found.
    """
    started = []
    ended = []
    for r in results:
        ts = r.get("trace_summary", {})
        if ts.get("started_at"):
            started.append(ts["started_at"])
        if ts.get("ended_at"):
            ended.append(ts["ended_at"])

    if not started or not ended:
        return None

    return min(started), max(ended)
