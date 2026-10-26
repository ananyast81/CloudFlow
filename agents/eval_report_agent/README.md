# Reporting agent

Computes SHAP explanations with a visible fallback when necessary, exports transformed data, creates JSON/Markdown/HTML reports, Plotly figures and reproducibility artifacts. Optional Gemini/Groq interpretation is labeled separately from measured evidence.

The integrated entry point is `main.py`, called by `orchestrator/graph.py`. Cross-agent state is defined in `shared/contracts.py`. Agents run in the shared isolated worker; use the root `compose.yaml` for deployment.

See `docs/ARCHITECTURE.md`, `docs/API.md` and the root README for execution, endpoints and validation.
