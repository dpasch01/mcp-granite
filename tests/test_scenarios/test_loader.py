"""Scenario loader tests using temporary fixtures, independent of the full dataset."""

from pathlib import Path

import pytest
import yaml

from mcp_granite.scenarios.loader import load_scenario_by_id, load_scenarios

SAMPLE_ROOT = Path(__file__).resolve().parents[2] / "scenarios"


@pytest.fixture
def scenarios_dir(tmp_path):
    sample = yaml.safe_load(
        (SAMPLE_ROOT / "smarthome/check_kitchen_sensors.yaml").read_text()
    )
    for domain, difficulty in [("smarthome", "easy"), ("industrial", "medium"), ("fleet", "hard")]:
        record = {**sample, "id": f"{domain}-test", "domain": domain, "difficulty": difficulty}
        directory = tmp_path / domain
        directory.mkdir()
        (directory / "sample.yaml").write_text(yaml.safe_dump(record))
    return tmp_path


def test_load_all_scenarios(scenarios_dir):
    scenarios = load_scenarios(scenarios_dir)
    assert len(scenarios) == 3
    assert {s.domain for s in scenarios} == {"smarthome", "industrial", "fleet"}


def test_load_by_domain(scenarios_dir):
    scenarios = load_scenarios(scenarios_dir, domain="smarthome")
    assert [s.id for s in scenarios] == ["smarthome-test"]


@pytest.mark.parametrize("difficulty,count", [("easy", 1), ("medium", 2), ("hard", 3)])
def test_load_by_difficulty(scenarios_dir, difficulty, count):
    assert len(load_scenarios(scenarios_dir, max_difficulty=difficulty)) == count


def test_load_by_id(scenarios_dir):
    scenario = load_scenario_by_id(scenarios_dir, "industrial-test")
    assert scenario.domain == "industrial"
    assert scenario.difficulty == "medium"


def test_unknown_id(scenarios_dir):
    with pytest.raises(ValueError, match="not found"):
        load_scenario_by_id(scenarios_dir, "missing")


def test_sample_has_all_granularities():
    scenario = load_scenario_by_id(SAMPLE_ROOT, "smarthome-004")
    assert set(scenario.gold_standard) == {"primitive", "composite_4", "composite_2", "composite_1"}
    assert all(scenario.gold_standard.values())
    assert scenario.expected_output.contains == ["kitchen", "lux"]
