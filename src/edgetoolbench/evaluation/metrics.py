"""All seven benchmark metrics for EdgeToolBench."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from scipy.stats import kendalltau


@dataclass
class ScenarioResult:
    """Computed metrics for a single scenario run."""

    tool_selection_precision: float
    tool_selection_recall: float
    tool_selection_f1: float
    argument_accuracy: float
    sequence_edit_distance: float  # normalised (0 = perfect, 1 = worst)
    sequence_kendall_tau: float  # -1 to 1 (1 = perfect)
    task_completion: float  # 0.0 or 1.0
    error_recovery_rate: float | None  # None if no faults injected
    token_efficiency: int  # total tokens consumed
    redundant_call_rate: float  # 0 to 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_selection_precision": self.tool_selection_precision,
            "tool_selection_recall": self.tool_selection_recall,
            "tool_selection_f1": self.tool_selection_f1,
            "argument_accuracy": self.argument_accuracy,
            "sequence_edit_distance": self.sequence_edit_distance,
            "sequence_kendall_tau": self.sequence_kendall_tau,
            "task_completion": self.task_completion,
            "error_recovery_rate": self.error_recovery_rate,
            "token_efficiency": self.token_efficiency,
            "redundant_call_rate": self.redundant_call_rate,
        }


# ── Tool Selection F1 ───────────────────────────────────────────────────────

def compute_tool_selection_f1(
    actual_tools: set[str], gold_tools: set[str]
) -> tuple[float, float, float]:
    """Compute precision, recall, F1 over tool sets."""
    if not actual_tools and not gold_tools:
        return 1.0, 1.0, 1.0
    if not actual_tools:
        return 0.0, 0.0, 0.0
    if not gold_tools:
        return 0.0, 0.0, 0.0

    tp = len(actual_tools & gold_tools)
    precision = tp / len(actual_tools) if actual_tools else 0.0
    recall = tp / len(gold_tools) if gold_tools else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


# ── Argument Accuracy ────────────────────────────────────────────────────────

def compute_argument_accuracy(
    actual_calls: list[dict[str, Any]],
    gold_calls: list[dict[str, Any]],
) -> float:
    """Compute average argument match rate across matched tool calls.

    Each call is a dict with 'tool_name' and 'arguments'.
    Matches actual calls to gold calls by tool name (greedy, first match).
    """
    if not gold_calls:
        return 1.0

    # Build a pool of gold calls to match against
    gold_remaining = list(gold_calls)
    scores: list[float] = []

    for actual in actual_calls:
        best_idx = None
        best_score = -1.0
        for i, gold in enumerate(gold_remaining):
            if actual["tool_name"] == gold["tool_name"]:
                score = _arg_similarity(actual.get("arguments", {}), gold.get("arguments", {}))
                if score > best_score:
                    best_score = score
                    best_idx = i
        if best_idx is not None:
            scores.append(best_score)
            gold_remaining.pop(best_idx)

    return sum(scores) / len(gold_calls) if gold_calls else 0.0


def _arg_similarity(actual: dict, gold: dict) -> float:
    """Jaccard-like similarity of argument key-value pairs."""
    if not gold:
        return 1.0 if not actual else 0.0

    matches = 0
    for key, gval in gold.items():
        if key in actual:
            if _values_match(actual[key], gval):
                matches += 1
    return matches / len(gold)


def _values_match(actual: Any, gold: Any) -> bool:
    """Flexible value comparison."""
    if isinstance(gold, str) and isinstance(actual, str):
        return gold.lower().strip() == actual.lower().strip()
    if isinstance(gold, dict) and isinstance(actual, dict):
        # Recursive check — all gold keys must match
        return all(
            k in actual and _values_match(actual[k], v) for k, v in gold.items()
        )
    return actual == gold


# ── Sequence Fidelity ────────────────────────────────────────────────────────

def compute_sequence_edit_distance(actual_seq: list[str], gold_seq: list[str]) -> float:
    """Normalised Levenshtein edit distance between tool-call sequences."""
    if not gold_seq and not actual_seq:
        return 0.0
    if not gold_seq or not actual_seq:
        return 1.0

    n, m = len(actual_seq), len(gold_seq)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if actual_seq[i - 1] == gold_seq[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)

    max_len = max(n, m)
    return dp[n][m] / max_len if max_len > 0 else 0.0


def compute_sequence_kendall_tau(actual_seq: list[str], gold_seq: list[str]) -> float:
    """Kendall's tau rank correlation for tool ordering.

    Maps tool names to their positions in the gold sequence, then computes
    correlation based on which gold tools appear in actual and their order.
    Returns 0.0 if fewer than 2 matching tools.
    """
    # Build position map for gold
    gold_positions = {}
    for i, name in enumerate(gold_seq):
        if name not in gold_positions:
            gold_positions[name] = i

    # Find matching tools and their positions
    actual_ranks = []
    gold_ranks = []
    used_positions: set[int] = set()

    for name in actual_seq:
        if name in gold_positions:
            gpos = gold_positions[name]
            if gpos not in used_positions:
                actual_ranks.append(len(actual_ranks))
                gold_ranks.append(gpos)
                used_positions.add(gpos)

    if len(actual_ranks) < 2:
        return 0.0

    tau, _ = kendalltau(actual_ranks, gold_ranks)
    return float(tau) if not (tau != tau) else 0.0  # handle NaN


# ── Task Completion ──────────────────────────────────────────────────────────

def compute_task_completion(
    final_answer: str | None,
    expected_contains: list[str],
    expected_values: dict[str, Any],
) -> float:
    """Check if the agent's final answer meets expected criteria.

    Returns 1.0 if all checks pass, 0.0 otherwise.
    """
    if not final_answer:
        return 0.0

    answer_lower = final_answer.lower()

    # Check all required substrings
    for substr in expected_contains:
        if substr.lower() not in answer_lower:
            return 0.0

    # expected_values is informational for now — hard to check from text
    return 1.0


# ── Error Recovery ───────────────────────────────────────────────────────────

def compute_error_recovery_rate(
    tool_responses: list[dict],
    tool_calls: list[dict],
) -> float | None:
    """Compute fraction of errors that were followed by a retry or alternative.

    Returns None if no errors occurred.
    """
    error_indices = [
        i for i, tr in enumerate(tool_responses)
        if tr.get("is_error", False)
    ]
    if not error_indices:
        return None

    recovered = 0
    for idx in error_indices:
        error_tool = tool_responses[idx].get("tool_name", "")
        # Check if there's a subsequent call to the same tool (retry)
        # or any subsequent call (alternative strategy)
        subsequent_calls = tool_calls[idx + 1:] if idx + 1 < len(tool_calls) else []
        if subsequent_calls:
            recovered += 1

    return recovered / len(error_indices) if error_indices else 0.0


# ── Redundant Call Rate ──────────────────────────────────────────────────────

def compute_redundant_call_rate(tool_calls: list[dict]) -> float:
    """Fraction of tool calls that are exact duplicates (same name + args)."""
    if not tool_calls:
        return 0.0

    seen: Counter[str] = Counter()
    for tc in tool_calls:
        key = f"{tc['tool_name']}:{_stable_hash(tc.get('arguments', {}))}"
        seen[key] += 1

    redundant = sum(count - 1 for count in seen.values() if count > 1)
    return redundant / len(tool_calls)


def _stable_hash(d: dict) -> str:
    """Create a stable string representation for hashing."""
    return str(sorted(d.items()))
