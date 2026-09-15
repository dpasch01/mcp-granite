"""Verify the published sample can be generated and evaluated without the full dataset."""

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from mcp_granite.cli import main
from mcp_granite.config.settings import ExperimentConfig
from mcp_granite.evaluation.comparator import evaluate
from mcp_granite.evaluation.gold_standard import load_gold_standard
from mcp_granite.harness.trace import ExecutionTrace, ToolCall, ToolResponse
from mcp_granite.orchestrator.experiment import generate_experiment_matrix
from mcp_granite.orchestrator.results import load_results
from mcp_granite.scenarios.loader import load_scenario_by_id

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples/sample_run"


def test_example_matrix_matches_recorded_conditions():
    config = ExperimentConfig(**yaml.safe_load((ROOT / "configs/default.yaml").read_text()))
    config.scenarios_dir = ROOT / "scenarios"
    conditions = generate_experiment_matrix(config)
    assert len(conditions) == 4
    assert {c.key for c in conditions} == {p.stem for p in (SAMPLE / "traces").glob("*.json")}


def test_recorded_metrics_match_evaluation():
    scenario = load_scenario_by_id(ROOT / "scenarios", "smarthome-004")
    results = load_results(SAMPLE)
    assert len(results) == 4
    for result in results:
        c = result["condition"]
        filename = (
            f"{c['model']}__{c['domain']}__{c['granularity']}__{c['scenario_id']}"
            f"__fr{c['fault_rate']}__rep{c['repetition']}.json"
        )
        raw = json.loads((SAMPLE / "traces" / filename).read_text())
        raw["tool_calls"] = [ToolCall(**call) for call in raw["tool_calls"]]
        raw["tool_responses"] = [ToolResponse(**response) for response in raw["tool_responses"]]
        trace = ExecutionTrace(**raw)
        actual = evaluate(trace, load_gold_standard(scenario, c["granularity"])).to_dict()
        for key, expected in result["metrics"].items():
            if expected is None:
                assert actual[key] is None
            else:
                assert actual[key] == pytest.approx(expected)


def test_evaluate_sample_cli():
    result = CliRunner().invoke(main, ["evaluate", "--results-dir", str(SAMPLE)])
    assert result.exit_code == 0, result.output
    assert "Loaded 4 results." in result.output
    assert "granite4:3b" in result.output
