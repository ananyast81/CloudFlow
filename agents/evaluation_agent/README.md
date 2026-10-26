# Evaluation & Diagnostics agent

Uses training CV to decide bounded retries. After selection is final, evaluates the winner and a baseline on the same untouched holdout and exports metrics, error examples and a Plotly diagnostic chart.

The integrated entry point is `main.py`, called by `orchestrator/graph.py`. Cross-agent state is defined in `shared/contracts.py`. Agents run in the shared isolated worker; use the root `compose.yaml` for deployment.

See `docs/ARCHITECTURE.md`, `docs/API.md` and the root README for execution, endpoints and validation.
