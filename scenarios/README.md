# Scenario library

The library contains **81 scenarios across nine domains**. Each domain has
three easy, three medium, and three hard scenarios, with gold-standard tool
calls for `primitive`, `composite_4`, `composite_2`, and `composite_1` interfaces.

| Domain | Directory | Scenarios |
| --- | --- | ---: |
| Agriculture | [agriculture](agriculture) | 9 |
| Energy | [energy](energy) | 9 |
| Fleet | [fleet](fleet) | 9 |
| Healthcare | [healthcare](healthcare) | 9 |
| Industrial IoT | [industrial](industrial) | 9 |
| Robotics | [robotics](robotics) | 9 |
| Smart home | [smarthome](smarthome) | 9 |
| Surveillance | [surveillance](surveillance) | 9 |
| Warehouse | [warehouse](warehouse) | 9 |

Each YAML file defines its ID, domain, difficulty, user prompt, expected tool
calls per interface, and expected answer criteria. The runtime validates these
files through `mcp_granite.scenarios.schema.ScenarioDef`.

From the repository root:

```bash
uv run mcp-granite list-scenarios
uv run mcp-granite run --config configs/default.yaml
uv run mcp-granite run --config configs/benchmark.yaml
```

The default config selects one scenario and four interfaces (4 conditions).
The benchmark config selects all 81 scenarios, four interfaces, and three
repetitions (972 conditions). Both use one model and no injected faults.

These definitions were copied unchanged from the current research workspace.
Recorded results remain limited to the four executions in
[the sample walkthrough](../examples/README.md).
