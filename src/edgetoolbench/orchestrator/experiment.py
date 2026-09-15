"""Experiment matrix generation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from edgetoolbench.config.settings import ExperimentConfig
from edgetoolbench.scenarios.loader import load_scenarios


@dataclass(frozen=True)
class ExperimentCondition:
    """A single experimental condition (one row of the experiment matrix)."""

    model: str
    domain: str
    granularity: str
    scenario_id: str
    fault_rate: float
    repetition: int
    seed: int

    @property
    def key(self) -> str:
        """Unique string key for this condition (used for result file naming)."""
        safe_model = self.model.replace("/", "--")
        return (
            f"{safe_model}__{self.domain}__{self.granularity}"
            f"__{self.scenario_id}__fr{self.fault_rate}__rep{self.repetition}"
        )


def _derive_seed(condition_key: str) -> int:
    """Derive a deterministic seed from condition parameters."""
    return int(hashlib.sha256(condition_key.encode()).hexdigest()[:8], 16)


def generate_experiment_matrix(config: ExperimentConfig) -> list[ExperimentCondition]:
    """Generate the full Cartesian product of experimental conditions.

    Returns a list of ExperimentCondition objects.
    """
    scenarios = load_scenarios(
        config.scenarios_dir,
        max_difficulty=config.max_difficulty,
    )

    # Optionally filter by scenario IDs
    if config.scenario_ids:
        allowed = set(config.scenario_ids)
        scenarios = [s for s in scenarios if s.id in allowed]

    conditions: list[ExperimentCondition] = []

    for model in config.models:
        for scenario in scenarios:
            if scenario.domain not in config.domains:
                continue
            for granularity in config.granularities:
                if granularity not in scenario.gold_standard:
                    continue
                for fault_rate in config.fault_rates:
                    for rep in range(config.repetitions):
                        key_str = f"{model}__{scenario.id}__{granularity}__fr{fault_rate}__rep{rep}"
                        seed = _derive_seed(key_str)
                        conditions.append(ExperimentCondition(
                            model=model,
                            domain=scenario.domain,
                            granularity=granularity,
                            scenario_id=scenario.id,
                            fault_rate=fault_rate,
                            repetition=rep,
                            seed=seed,
                        ))

    return conditions
