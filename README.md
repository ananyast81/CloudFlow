# CloudFlow

A five-agent data science workspace that turns a CSV and a natural-language prediction question into an inspected dataset, a human-reviewed modeling plan, trained models, diagnostics, explanations and a reproducible report.

**Implemented stack:** Python, LangGraph, FastAPI, Pandas, NumPy, scikit-learn, XGBoost, Matplotlib, Plotly, SHAP, MLflow, React, Vite and Docker. Gemini and Groq reasoning are supported through optional server-side configuration. Local planning runs without an API key.

## Features and workflow

Upload and preview a CSV, define a prediction objective, review the proposed training plan, compare trained models, inspect diagnostics, make predictions, and download reports and artifacts. Run History preserves past analyses; Experiments shows candidate models and tracking details. The frontend uses actual backend state and results.

### Five agents, six workflow stages

| Order | Runtime stage | Responsibility |
| --- | --- | --- |
| 1 | `data_understanding` | Profile and clean the dataset |
| 2 | `analysis_features` | Explore training data and propose features and a plan |
| 3 | `human_review` | Human approval, supported plan edits, or rejection |
| 4 | `modeling` | Train and compare candidate models |
| 5 | `evaluation` | Evaluate the selected model and diagnose errors |
| 6 | `reporting` | Explain findings and generate reports |

**Human review is a checkpoint, not an autonomous agent.** The orchestrator coordinates five specialist agents and this review stage. Training waits for approval. Changing the target or problem type rebuilds the analysis and requests another review.

The mission-control frontend redesign presents these stages around an Orchestrator Orbit, with a selected-stage dossier, execution logs, and dark navy/lime styling. That frontend change is separate from this README update: the layout available in a checkout depends on whether the frontend redesign has been incorporated. Six orbit nodes represent six stages, not six AI agents.

See [synopsis alignment](docs/SYNOPSIS_ALIGNMENT.md), [architecture](docs/ARCHITECTURE.md), and [verification](docs/VERIFICATION.md) for implementation details.

## Storage

React/Vite communicates with FastAPI through `/api`; LangGraph coordinates execution and the background worker runs training and reporting.

| Default location | Purpose |
| --- | --- |
| `workspace/runs.sqlite` | Run records and execution events |
| `workspace/checkpoints.sqlite` | LangGraph workflow checkpoints and review pauses |
| `workspace/mlflow.db` | Local MLflow experiment tracking |
| `workspace/<run_id>/` | Datasets, fitted models, charts, reports, and reproducibility files |
| `workspace/mlartifacts/` | Local MLflow artifacts |

SQLite requires no separate database server. Preserve the workspace across restarts and deployments. `CLOUDFLOW_WORKSPACE` and `MLFLOW_TRACKING_URI` can override the defaults.

## Quick start on Windows

Requirements: Python 3.11 and Node.js 22.12+ or 24+.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm ci
cd ..
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m scripts.dev
```

Open **http://localhost:5173**. The launcher starts FastAPI, its automatic background worker and Vite. Press Ctrl+C in the launcher terminal to stop its processes. `./scripts/start.ps1 -Install` is an alternative setup-and-launch helper.

When dependencies are already installed, only the final command is needed. Do not place an LLM key in the frontend environment.

`requirements.lock.txt` records the exact tested Windows/Python 3.11 packages. Use `pip install -r requirements.lock.txt` to recreate that environment; `requirements.txt` provides the cross-platform dependency ranges. Linux/macOS and Docker have not been runtime-tested on this Windows host.

Screenshots in `docs/screenshots/` document an earlier frontend revision, rather than the mission-control redesign.

### Start again after installation

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.dev
```

Alternatively, use two PowerShell terminals starting at the repository root:

```powershell
# Terminal 1: backend and automatic worker
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2: frontend
cd frontend
npm run dev
```

Choose the combined launcher or the separate terminals to avoid duplicate servers. Keep the terminals open and press Ctrl+C to stop. Confirm <http://localhost:8000/api/health> responds before uploading. If an upload returns 502, inspect both terminal outputs and check that the frontend proxy can reach the backend on port 8000.

## Quick start on Linux/macOS

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cd frontend && npm ci && cd ..
cp .env.example .env
python -m scripts.dev
```

To run separate terminals:

```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
# another terminal:
cd frontend
npm run dev
```

The API automatically starts a worker unless `CLOUDFLOW_AUTO_WORKER=false`. When using that setting, start `python -m orchestrator.worker` separately. Use the same `CLOUDFLOW_WORKSPACE` for API and worker. A single automatic API process is sufficient; do not enable several reloaders against one local workspace.

- UI: http://localhost:5173
- API documentation: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

## Try a complete analysis

1. Upload `data/churn.csv` (synthetic customer classification) or `data/housing.csv` (synthetic price regression).
2. Describe the goal, such as “Predict Churn and explain the most influential customer characteristics.” Select `Churn` as the target, or `price` for the housing sample.
3. Launch analysis. Data Understanding inspects/cleans the dataset; Analysis & Features produces training-only EDA and a feature proposal.
4. At **Your review**, inspect and optionally edit the target, task, features, models and preprocessing. Choose **Approve & train**. Changing the target/task rebuilds analysis and asks for review again.
5. Watch model training and diagnostic feedback in Activity. Open **Results & diagnostics** for CV comparisons, final holdout metrics and interactive charts.
6. Open **Predict** to submit new raw feature values to the trained pipeline. Use **Artifacts → Download all** to save the report and reproducibility bundle.

The original three-row `sample_orders.csv` remains as a tiny EDA fixture; it is not a trainable demo. The supplied synthetic samples can be regenerated with `python -m scripts.generate_samples`.

## Optional Gemini/Groq reasoning

See [LLM integration and verification](docs/LLM_INTEGRATION.md) for configuration, evidence boundaries, per-stage success/fallback labels, executed checks, and remaining scope. The configured badge indicates presence of configuration, not successful provider use.

Edit the root `.env`:

```dotenv
LLM_PROVIDER=groq
LLM_API_KEY=your-provider-key
LLM_MODEL=a-model-available-in-your-provider-account
```

For Gemini, set `LLM_PROVIDER=gemini` with a Gemini API key and model identifier. Restart the API/worker, then enable **Use AI reasoning** on the new-analysis form. The configuration page shows readiness and never returns the key. This sends the objective, column summaries and computed findings to the selected provider. Numerical processing and metric computation remain deterministic Python operations.

If a provider request fails or violates the expected schema, the run records a warning and continues with local reasoning. Reports distinguish measured results from optional AI interpretation. Without a key, leave `LLM_PROVIDER=none`.

## Docker deployment

Install and start Docker Engine/Desktop first. From the repository root:

```bash
docker compose up --build -d
```

Open **http://localhost:8080**. Compose runs an Nginx frontend, FastAPI and a separate resource-limited worker. The named `cloudflow-data` volume preserves run records, LangGraph checkpoints, models and MLflow records. Ports bind to localhost.

```bash
docker compose logs -f api worker
docker compose down
# Optional MLflow browser interface:
docker compose --profile tracking up -d
```

MLflow UI: http://localhost:5000. Do not use `docker compose down -v` unless you intend to delete persisted analyses. The root Dockerfile is the supported build; agent-directory Dockerfiles are compatibility wrappers around `cloudflow-backend:latest`.

## Experiment tracking

Every successful candidate logs its parameters, random seed, metric, CV scores, duration and serialized fitted model to MLflow. The selected candidate also receives holdout metrics and report artifacts. The in-app Experiments page works from persisted workflow state and shows whether each candidate was logged to MLflow.

Default tracking storage is `workspace/mlflow.db`; model/report artifacts are under `workspace/mlartifacts`. To inspect locally:

```bash
python -m mlflow ui --backend-store-uri sqlite:///workspace/mlflow.db --host 127.0.0.1 --port 5000
```

Set `MLFLOW_TRACKING_URI` for a separately managed tracking server in local development. MLflow failures are visible warnings; local model artifacts remain available.

## Results and reproducibility

Each run has an isolated `workspace/<run_id>/` directory. Downloads include:

- Cleaned raw data and transformed training/test feature matrices.
- Approved plan, data profile, cleaning summary, EDA statistics and PNG charts.
- Candidate pipelines, selected `model.joblib`, CV results, held-out predictions and metrics.
- SHAP importance and local explanations, or an explicitly identified fallback.
- Interactive Plotly chart JSON; final report in HTML, Markdown and JSON.
- A reproduction notebook and JSON metadata with split indices, hashes, seeds and package versions.

The model bundle contains the entire fitted preprocessing pipeline. It is trained on the training partition, preserving the independence of the reported holdout. The exported notebook is provided for reproduction and is not represented as an executed notebook.

The HTML report embeds all EDA PNG images and the Plotly runtime. Downloading `report.html` alone is sufficient to open its images and charts offline; the individual PNGs also remain available in the artifact ZIP. Previously downloaded HTML files are unchanged by a project update: download the report again after refreshing an older run's export:

```bash
python -m scripts.repair_reports --all-completed
# Or refresh one completed run:
python -m scripts.repair_reports --run-id <run_id>
```

This rebuilds the HTML from saved images and chart data without retraining, recomputing metrics or calling an LLM.

From the project environment, verify a run or extracted artifact bundle:

```bash
python -m scripts.reproduce --run-dir workspace/<run_id>
```

This rebuilds the winning candidate from its recorded configuration and checks that holdout predictions match. Use the package versions recorded in `reproducibility.json`; fitted Python model files should only be loaded from trusted sources.

## API integration

All frontend requests use one client in `frontend/src/lib/api.js`. The default base is `/api`: Vite proxies it locally and Nginx proxies it in Docker. `frontend/.env.example` documents `VITE_API_BASE_URL` for an alternative backend.

The primary flow is:

```text
POST /api/datasets/preview
POST /api/runs
GET  /api/runs/{id}          (poll)
GET  /api/runs/{id}/events   (activity)
POST /api/runs/{id}/approval
GET  /api/runs/{id}          (poll to terminal state)
GET  /api/runs/{id}/download
POST /api/runs/{id}/predict
```

See [REST contracts and examples](docs/API.md). Run creation returns 202 acceptance; completion occurs only after all five agents and reporting have finished. Repeated approval and terminal-state mutations return 409. Artifact downloads are scoped to registered paths within the selected run.

## Development checks

```bash
python -m pytest
python -m compileall -q api agents shared orchestrator scripts tests
cd frontend
npm run lint
npm run build
# With API/worker and Vite running:
npx playwright test
```

Playwright is configured for installed Microsoft Edge. On Linux, install a Playwright-supported browser and adjust the configured channel. Tests use synthetic data and actually execute both classification and regression workflows; provider transport tests use mocks and do not require credentials. See [verification results](docs/VERIFICATION.md) for exactly what was run.
