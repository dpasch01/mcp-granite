from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to the project root (three levels up from this file:
# src/mcp_granite/config/settings.py -> project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class ExperimentConfig(BaseSettings):
    """Central configuration for an MCP-GRANITE experiment run."""

    model_config = SettingsConfigDict(
        env_prefix="MCP_GRANITE_",
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Experiment matrix ---
    models: list[str] = Field(default=["gpt-4o-mini", "claude-haiku"])
    domains: list[str] = Field(
        default=[
            "travel", "helpdesk", "ecommerce", "smarthome", "industrial", "fleet",
            "agriculture", "energy", "warehouse", "surveillance", "healthcare", "robotics",
        ]
    )
    granularities: list[str] = Field(default=["primitive", "composite_4"])
    fault_rates: list[float] = Field(default=[0.0, 0.1, 0.2, 0.3])
    repetitions: int = 5

    # --- Scenario filtering ---
    scenario_ids: list[str] | None = None  # None = run all
    max_difficulty: str = "hard"

    # --- Execution limits ---
    max_agent_turns: int = 20
    agent_timeout_seconds: float = 120.0

    # --- LLM generation settings ---
    temperature: float = 0.0
    max_tokens: int = 4096

    # --- Prometheus monitoring ---
    prometheus_url: str | None = None
    prometheus_metrics: list[str] | None = None
    prometheus_step: str = "5s"

    # --- Paths ---
    scenarios_dir: Path = Path("scenarios")
    results_dir: Path = Path("results")
    configs_dir: Path = Path("configs")
