"""Tests for the trace-vs-gold comparator."""

from mcp_granite.evaluation.comparator import evaluate
from mcp_granite.evaluation.gold_standard import GoldStandard, GoldToolCall
from mcp_granite.harness.trace import ExecutionTrace, ToolCall, ToolResponse


def _make_trace(
    calls: list[tuple[str, dict]],
    final_answer: str = "Booking confirmed for JFK to LHR.",
) -> ExecutionTrace:
    return ExecutionTrace(
        tool_calls=[
            ToolCall(tool_name=name, arguments=args, timestamp=float(i))
            for i, (name, args) in enumerate(calls)
        ],
        final_answer=final_answer,
        total_tokens_in=500,
        total_tokens_out=200,
    )


def _make_gold(
    calls: list[tuple[str, dict]],
    contains: list[str] | None = None,
) -> GoldStandard:
    return GoldStandard(
        calls=[
            GoldToolCall(tool_name=name, arguments=args)
            for name, args in calls
        ],
        expected_contains=contains or ["confirmed", "JFK"],
    )


def test_perfect_match():
    calls = [
        ("search_flights", {"origin": "JFK", "destination": "LHR"}),
        ("book_flight", {"flight_id": "FL001", "passenger_name": "John"}),
    ]
    trace = _make_trace(calls)
    gold = _make_gold(calls)
    result = evaluate(trace, gold)

    assert result.tool_selection_f1 == 1.0
    assert result.argument_accuracy == 1.0
    assert result.sequence_edit_distance == 0.0
    assert result.sequence_kendall_tau == 1.0
    assert result.task_completion == 1.0
    assert result.redundant_call_rate == 0.0


def test_wrong_tools():
    trace = _make_trace([
        ("search_hotels", {"city": "London"}),
    ])
    gold = _make_gold([
        ("search_flights", {"origin": "JFK"}),
    ])
    result = evaluate(trace, gold)

    assert result.tool_selection_f1 == 0.0
    assert result.argument_accuracy == 0.0


def test_extra_calls():
    trace = _make_trace([
        ("search_flights", {"origin": "JFK"}),
        ("search_flights", {"origin": "JFK"}),  # redundant
        ("book_flight", {"flight_id": "FL001"}),
    ])
    gold = _make_gold([
        ("search_flights", {"origin": "JFK"}),
        ("book_flight", {"flight_id": "FL001"}),
    ])
    result = evaluate(trace, gold)

    assert result.tool_selection_f1 == 1.0  # correct tools used
    assert result.redundant_call_rate > 0  # has a duplicate


def test_failed_completion():
    trace = _make_trace(
        [("search_flights", {"origin": "JFK"})],
        final_answer="I could not complete the booking.",
    )
    gold = _make_gold([("search_flights", {"origin": "JFK"})], contains=["confirmed"])
    result = evaluate(trace, gold)

    assert result.task_completion == 0.0
