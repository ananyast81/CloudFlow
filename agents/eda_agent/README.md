# Analysis & Features agent

Reuses the original schema-validated statistical tools and chart planner on training rows only. Proposes feature exclusions and preprocessing. Matplotlib PNG paths are registered for REST delivery.

The integrated entry point is `main.py`, called by `orchestrator/graph.py`. Cross-agent state is defined in `shared/contracts.py`. Agents run in the shared isolated worker; use the root `compose.yaml` for deployment.

See `docs/ARCHITECTURE.md`, `docs/API.md` and the root README for execution, endpoints and validation.
