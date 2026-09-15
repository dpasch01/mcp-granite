# Sample execution

This is one recorded Granite 4 (`granite4:3b`) execution of **Check kitchen
sensors** (`smarthome-004`), repeated once for each of the four tool interfaces.
No faults were injected. Repetition index: 0.

## Prompt

> What are the current sensor readings in the kitchen? Check the light level and temperature.

The mock kitchen contains a light sensor reporting **350 lux** and no temperature
sensor. The scenario and its gold-standard calls are in
[check_kitchen_sensors.yaml](../scenarios/smarthome/check_kitchen_sensors.yaml).

## Recorded results

| Level | Tool calls | F1 | Argument accuracy | Task completion | Time (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| L4 | 1 | 0.667 | 0.500 | 1 | 4.161 |
| L3 | 1 | 1.000 | 1.000 | 1 | 4.195 |
| L2 | 2 | 1.000 | 0.500 | 1 | 5.119 |
| L1 | 0 | 0.000 | 0.000 | 0 | 2.636 |

These are individual recorded outcomes, not averages or evidence of statistical
significance. In this example, task completion checks that the final answer
contains “kitchen” and “lux”; it does not check simulator state.
Token counts are recorded as zero because the trace did not report token usage.

## L3 tool call

```json
{"tool": "get_room_status", "arguments": {"location": "kitchen"}}
```

The tool returned the kitchen light reading and `avg_temp: null`. The model
reported 350 lux and noted that the room status did not include a temperature
reading. The full responses and final answers are preserved in the four
[trace files](sample_run/traces).

## Inspect or rerun

From the repository root:

```bash
# Summarize the recorded execution without a model or API key.
uv run edgetoolbench evaluate --results-dir examples/sample_run

# With Ollama running and granite4:3b pulled, execute the scenario again.
uv run edgetoolbench run --config configs/default.yaml
```

A fresh execution writes to `results/run_YYYYMMDD_HHMMSS/`. Model versions,
hardware, and generation behavior can change outputs and timings.

## Provenance

- Source run: `run_20260324_094111` from the research workspace.
- Recorded on 2026-03-24; exact UTC timestamps and condition seeds remain in
  the results and trace files.
- Selection: model `granite4:3b`, scenario `smarthome-004`, fault rate `0.0`,
  repetition `0`, all four granularities.
- The four records were extracted from the original run; trace files were
  copied unchanged. They were not generated for this repository publication.
- The complete dataset and all other experiment outputs remain separate.
