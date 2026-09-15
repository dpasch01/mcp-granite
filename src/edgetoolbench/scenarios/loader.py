from __future__ import annotations

from pathlib import Path

import yaml

from edgetoolbench.scenarios.schema import ScenarioDef


def load_scenarios(
    scenarios_dir: Path,
    domain: str | None = None,
    max_difficulty: str = "hard",
) -> list[ScenarioDef]:
    """Load and validate scenario YAML files.

    Args:
        scenarios_dir: Root directory containing domain sub-folders with YAML files.
        domain: If set, only load scenarios for this domain.
        max_difficulty: Maximum difficulty level to include.

    Returns:
        List of validated ScenarioDef objects.
    """
    difficulty_order = {"easy": 0, "medium": 1, "hard": 2}
    max_diff_val = difficulty_order.get(max_difficulty, 2)

    scenarios: list[ScenarioDef] = []
    search_dirs = [scenarios_dir / domain] if domain else sorted(scenarios_dir.iterdir())

    for domain_dir in search_dirs:
        if not domain_dir.is_dir():
            continue
        for yaml_path in sorted(domain_dir.glob("*.yaml")):
            with open(yaml_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            scenario = ScenarioDef(**raw)
            if difficulty_order.get(scenario.difficulty, 0) <= max_diff_val:
                scenarios.append(scenario)

    return scenarios


def load_scenario_by_id(scenarios_dir: Path, scenario_id: str) -> ScenarioDef:
    """Load a single scenario by its ID."""
    all_scenarios = load_scenarios(scenarios_dir)
    for s in all_scenarios:
        if s.id == scenario_id:
            return s
    raise ValueError(f"Scenario '{scenario_id}' not found in {scenarios_dir}")
