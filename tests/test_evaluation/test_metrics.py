"""Tests for evaluation metrics."""

from mcp_granite.evaluation.metrics import (
    compute_argument_accuracy,
    compute_redundant_call_rate,
    compute_sequence_edit_distance,
    compute_sequence_kendall_tau,
    compute_task_completion,
    compute_tool_selection_f1,
)


# ── Tool Selection F1 ────────────────────────────────────────────────────────

def test_f1_perfect():
    p, r, f = compute_tool_selection_f1({"a", "b"}, {"a", "b"})
    assert p == 1.0 and r == 1.0 and f == 1.0


def test_f1_partial():
    p, r, f = compute_tool_selection_f1({"a", "b", "c"}, {"a", "b"})
    assert r == 1.0
    assert p == pytest.approx(2 / 3)


def test_f1_empty_actual():
    p, r, f = compute_tool_selection_f1(set(), {"a"})
    assert f == 0.0


def test_f1_both_empty():
    p, r, f = compute_tool_selection_f1(set(), set())
    assert f == 1.0


# ── Argument Accuracy ────────────────────────────────────────────────────────

def test_arg_accuracy_perfect():
    actual = [{"tool_name": "t1", "arguments": {"a": "1", "b": "2"}}]
    gold = [{"tool_name": "t1", "arguments": {"a": "1", "b": "2"}}]
    assert compute_argument_accuracy(actual, gold) == 1.0


def test_arg_accuracy_partial():
    actual = [{"tool_name": "t1", "arguments": {"a": "1", "b": "WRONG"}}]
    gold = [{"tool_name": "t1", "arguments": {"a": "1", "b": "2"}}]
    assert compute_argument_accuracy(actual, gold) == 0.5


def test_arg_accuracy_missing_tool():
    actual = [{"tool_name": "t2", "arguments": {}}]
    gold = [{"tool_name": "t1", "arguments": {"a": "1"}}]
    assert compute_argument_accuracy(actual, gold) == 0.0


# ── Sequence Fidelity ────────────────────────────────────────────────────────

def test_edit_distance_perfect():
    assert compute_sequence_edit_distance(["a", "b", "c"], ["a", "b", "c"]) == 0.0


def test_edit_distance_swap():
    dist = compute_sequence_edit_distance(["b", "a", "c"], ["a", "b", "c"])
    assert 0 < dist < 1


def test_edit_distance_empty():
    assert compute_sequence_edit_distance([], []) == 0.0
    assert compute_sequence_edit_distance([], ["a"]) == 1.0


def test_kendall_tau_perfect():
    tau = compute_sequence_kendall_tau(["a", "b", "c"], ["a", "b", "c"])
    assert tau == 1.0


def test_kendall_tau_reversed():
    tau = compute_sequence_kendall_tau(["c", "b", "a"], ["a", "b", "c"])
    assert tau < 0


def test_kendall_tau_too_few():
    tau = compute_sequence_kendall_tau(["a"], ["a", "b", "c"])
    assert tau == 0.0


# ── Task Completion ──────────────────────────────────────────────────────────

def test_task_completion_pass():
    assert compute_task_completion("Booking confirmed for JFK", ["confirmed", "JFK"], {}) == 1.0


def test_task_completion_fail():
    assert compute_task_completion("Something went wrong", ["confirmed"], {}) == 0.0


def test_task_completion_none():
    assert compute_task_completion(None, ["confirmed"], {}) == 0.0


# ── Redundant Call Rate ──────────────────────────────────────────────────────

def test_no_redundancy():
    calls = [
        {"tool_name": "a", "arguments": {"x": 1}},
        {"tool_name": "b", "arguments": {"x": 2}},
    ]
    assert compute_redundant_call_rate(calls) == 0.0


def test_full_redundancy():
    calls = [
        {"tool_name": "a", "arguments": {"x": 1}},
        {"tool_name": "a", "arguments": {"x": 1}},
    ]
    assert compute_redundant_call_rate(calls) == 0.5


def test_empty_calls():
    assert compute_redundant_call_rate([]) == 0.0


# Need pytest for approx
import pytest
