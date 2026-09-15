# MCP-GRANITE

A benchmark system for evaluating how Model Context Protocol (MCP) tool-interface
granularity affects LLM-agent performance, robustness, latency, and resource usage.

This repository contains the runnable system, **81 scenarios across nine edge
domains**, and **four recorded executions** of one sample scenario. The complete
experiment outputs will be published separately; their repository link will be
added when available. The CLI command is `mcp-granite`; the Python package is
`mcp_granite`.

## System

The orchestrator combines models, scenarios, interface levels, fault rates, and
repetitions. For each condition it starts a fresh MCP server, connects an agent
through Google ADK and LiteLLM, captures tool calls and responses, evaluates the
trace, and saves results incrementally as JSONL. Optional Prometheus integration
collects resource measurements from an existing monitoring service.

| Level | Configuration value | Interface |
| --- | --- | --- |
| L4 | `primitive` | Fine-grained domain tools |
| L3 | `composite_4` | Four composite tools for each edge domain |
| L2 | `composite_2` | Two tools for each edge domain |
| L1 | `composite_1` | One dispatch tool for each edge domain |

All four levels are implemented for smart home, industrial IoT, fleet,
agriculture, energy, warehouse, surveillance, healthcare, and robotics.
Additional travel, helpdesk, and e-commerce servers support `primitive` and
`composite_4` interfaces; their composite tool counts vary by domain.
Servers use deterministic mock stores and support configurable fault injection.

## Install

Requirements: Linux or macOS, Python 3.12+, and `uv`. On Windows, use WSL
and clone into its Linux filesystem (recorded trace filenames contain `:`).
Run the following commands from the repository root after cloning:

```bash
git clone https://github.com/dpasch01/mcp-granite.git
cd mcp-granite
uv sync --locked --extra dev --extra analysis
uv run mcp-granite --help
uv run mcp-granite list-scenarios
```

The committed `uv.lock` records dependency versions for this release.

## Inspect the sample execution (no model required)

```bash
uv run mcp-granite evaluate --results-dir examples/sample_run
```

The included records come from one historical execution of `granite4:3b` on
`smarthome-004`, with no injected faults and repetition index 0, across all four
levels. See [the sample walkthrough](examples/README.md) for the prompt, recorded
scores, a tool call, and provenance. This small example illustrates the output
format; it is not an aggregate benchmark result.

## Run the example with a local model

Install and start Ollama, then pull the model:

```bash
ollama pull granite4:3b
uv run mcp-granite run --config configs/default.yaml
```

Ollama must be reachable at `http://localhost:11434`. If it is not already
running as a service, run `ollama serve` in another terminal first.
The config runs **four conditions**: one scenario, one model, all four levels,
no faults, and one repetition. New model outputs and timings can differ from
the recorded sample.

The command prints its output directory. Use that path to inspect the new run:

```bash
uv run mcp-granite evaluate --results-dir results/run_YYYYMMDD_HHMMSS
```

Each run contains `results.jsonl` (condition settings, scores, and timing), a
`traces/` directory (tool calls, responses, and final answers), and optionally
`prometheus.csv` when monitoring is configured.

To use another installed local model, pass its Ollama tag with `-m`. API-backed
models can also be selected using the registry or a LiteLLM provider/model ID;
export the appropriate provider credentials in your shell. See `.env.example`
for optional configuration (`MCP_GRANITE_` environment-variable prefix) and
`uv run mcp-granite list-models` for registry
entries. Provider availability depends on your account and installed backend.

## Run the bundled scenario library

The [scenario library](scenarios/README.md) contains 81 scenarios: nine each for
smart home, industrial IoT, fleet, agriculture, energy, warehouse, surveillance,
healthcare, and robotics. Each domain has three easy, three medium, and three
hard scenarios. Every scenario includes gold-standard calls for all four
interface levels.

```bash
uv run mcp-granite list-scenarios
uv run mcp-granite list-scenarios --domain robotics
uv run mcp-granite run --config configs/benchmark.yaml
```

The benchmark config uses the bundled `scenarios/` directory, one model,
all four levels, no faults, and three repetitions: **972 conditions** in total.
Edit the model list, domains, repetitions, and fault rates for your experiment.
The default sample config still runs only `smarthome-004` across four levels.

To use a separate scenario collection, set `scenarios_dir` in your experiment
YAML to a directory containing domain subdirectories with scenario YAML files.
Relative paths are resolved from the working directory. The matrix generator
skips interfaces absent from a scenario's gold standard.

The complete experiment outputs are not included; their separate publication
is planned for a later release.

## Evaluation and analysis

The evaluation module reports:

- Tool-selection precision, recall, and F1 over selected versus expected tool sets.
- Argument accuracy against expected tool-call arguments.
- Sequence edit distance and Kendall's tau for call ordering.
- Task completion: all required `expected_output.contains` strings occur in the
  final answer, case-insensitively. `expected_output.values` is currently
  informational; the evaluator does not validate final simulator state.
- Error recovery after tool errors, token counts when reported by the backend,
  and redundant-call rate.

To generate plots and tables from a completed run:

```bash
uv run python analyze_results.py --run-dir results/run_YYYYMMDD_HHMMSS --no-prometheus
```

Use full benchmark runs for comparative analysis. The four-record sample is
intended for the `evaluate` walkthrough, not statistical inference.

For monitoring, install the optional dependency:

```bash
uv sync --locked --extra dev --extra analysis --extra monitoring
```

Then set `prometheus_url` in the experiment YAML to your Prometheus endpoint.
Monitoring is optional and requires an existing exporter setup.
`uv run mcp-granite fetch-metrics --help` describes post-run collection.

## Development

```bash
uv run pytest -q
uv build
```

Tests use the bundled example and temporary scenario fixtures; they do not
require an LLM service or provider credentials.

## Repository layout

```text
src/mcp_granite/      Runtime, MCP servers, agent harness, evaluator, monitoring
configs/             Small example and full scenario benchmark configuration
scenarios/           81 scenarios across nine edge domains
examples/            Four recorded results, full traces, and walkthrough
tests/               Evaluation, mock-store, loader, and sample tests
analyze_results.py   Analysis of completed benchmark runs
uv.lock              Dependency lockfile
```
