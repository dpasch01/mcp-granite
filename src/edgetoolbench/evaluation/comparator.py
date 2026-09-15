"""Compare execution traces against gold standards to produce metrics."""

from __future__ import annotations

from edgetoolbench.evaluation.gold_standard import GoldStandard
from edgetoolbench.evaluation.metrics import (
    ScenarioResult,
    compute_argument_accuracy,
    compute_error_recovery_rate,
    compute_redundant_call_rate,
    compute_sequence_edit_distance,
    compute_sequence_kendall_tau,
    compute_task_completion,
    compute_tool_selection_f1,
)
from edgetoolbench.harness.trace import ExecutionTrace


def evaluate(trace: ExecutionTrace, gold: GoldStandard) -> ScenarioResult:
    """Evaluate an execution trace against a gold standard.

    Returns a ScenarioResult with all computed metrics.
    """
    # Prepare data in dict form for metric functions
    actual_tools = trace.tool_call_set()
    gold_tools = set(gold.required_tool_names)

    actual_calls_dicts = [
        {"tool_name": tc.tool_name, "arguments": tc.arguments}
        for tc in trace.tool_calls
    ]
    gold_calls_dicts = [
        {"tool_name": gc.tool_name, "arguments": gc.arguments}
        for gc in gold.required_calls
    ]

    actual_seq = trace.tool_call_names()
    gold_seq = gold.required_tool_names

    # 1. Tool Selection F1
    precision, recall, f1 = compute_tool_selection_f1(actual_tools, gold_tools)

    # 2. Argument Accuracy
    arg_acc = compute_argument_accuracy(actual_calls_dicts, gold_calls_dicts)

    # 3. Sequence Fidelity
    edit_dist = compute_sequence_edit_distance(actual_seq, gold_seq)
    kendall = compute_sequence_kendall_tau(actual_seq, gold_seq)

    # 4. Task Completion
    completion = compute_task_completion(
        trace.final_answer, gold.expected_contains, gold.expected_values,
    )

    # 5. Error Recovery
    tr_dicts = [
        {"tool_name": tr.tool_name, "response": tr.response, "is_error": tr.is_error}
        for tr in trace.tool_responses
    ]
    tc_dicts = [
        {"tool_name": tc.tool_name, "arguments": tc.arguments}
        for tc in trace.tool_calls
    ]
    error_recovery = compute_error_recovery_rate(tr_dicts, tc_dicts)

    # 6. Token Efficiency
    tokens = trace.total_tokens()

    # 7. Redundant Call Rate
    redundant = compute_redundant_call_rate(tc_dicts)

    return ScenarioResult(
        tool_selection_precision=precision,
        tool_selection_recall=recall,
        tool_selection_f1=f1,
        argument_accuracy=arg_acc,
        sequence_edit_distance=edit_dist,
        sequence_kendall_tau=kendall,
        task_completion=completion,
        error_recovery_rate=error_recovery,
        token_efficiency=tokens,
        redundant_call_rate=redundant,
    )
