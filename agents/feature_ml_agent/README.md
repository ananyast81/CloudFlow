# Modeling agent

Trains baseline and approved model families, fits preprocessing within CV folds, runs bounded parameter grids, persists all candidate models and tracks results in MLflow.

The integrated entry point is `main.py`, called by `orchestrator/graph.py`. Cross-agent state is defined in `shared/contracts.py`. Agents run in the shared isolated worker; use the root `compose.yaml` for deployment.

See `docs/ARCHITECTURE.md`, `docs/API.md` and the root README for execution, endpoints and validation.
