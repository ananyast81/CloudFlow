# Data Understanding agent

Profiles CSV data, resolves target/task using explicit input or optional JSON reasoning, conservatively cleans data, and reserves the holdout. `agent.py` is a backward-compatible standalone dispatcher; it never executes generated code.

The integrated entry point is `main.py`, called by `orchestrator/graph.py`. Cross-agent state is defined in `shared/contracts.py`. Agents run in the shared isolated worker; use the root `compose.yaml` for deployment.

See `docs/ARCHITECTURE.md`, `docs/API.md` and the root README for execution, endpoints and validation.
