# Verification record

Verified on 26 October 2026 using Windows x64, Python 3.11.9, Node.js 24.13.0, npm 11.6.2 and installed Microsoft Edge. Exact Python versions are recorded in `requirements.lock.txt`; frontend versions are locked in `frontend/package-lock.json`.

## Executed checks

| Check | Result |
|---|---|
| `python -m pytest -q` | **30 passed**; no failures or errors |
| All 20 original `scripts/check_*.py` utilities | **20 passed** in the project environment |
| `npm run test:e2e` | **2 passed**, using the real API, worker and browser |
| `npm run build` | Passed; Vite production bundle generated |
| `npm run lint` | Passed |
| Python `compileall` for API, agents, shared modules, orchestrator, scripts and tests | Passed |
| `python -m pip check` | No broken requirements |
| Compose YAML parsing and service inspection | Passed; runtime not executed |

The backend suite executes complete classification and regression analyses with all five model families plus dummy baselines. It checks persisted review/resume across application instances, edited preprocessing, changed-target reanalysis, MLflow run IDs, SHAP output, model reload and REST predictions, artifact downloads and reproducible holdout predictions.

It also executes the real LangGraph diagnostic retry loop, confirms the best candidate is retained across rounds, and checks that retry decisions do not read the holdout. Additional coverage includes multiclass XGBoost, feature selection, training-only imputation, unseen categories, malformed/oversized CSVs, invalid approvals, terminal transitions, atomic worker claims, lease expiry, CORS and both provider request/response protocols.

The browser test uploads the synthetic churn dataset, previews it, launches the workflow, reloads the waiting review, approves training, waits for completion, renders Plotly charts, makes a real prediction, downloads the artifact ZIP and opens run history. It asserts no browser page errors. The mobile test checks a 390px viewport for overflow and validates upload error messaging.

Screenshots were captured from the running application and visually inspected: [new analysis](screenshots/new-analysis.png), [completed results](screenshots/results.png), [mobile](screenshots/mobile.png).

## Compatibility findings

XGBoost 3.2 stores a base-score format that SHAP 0.49.1's specialized tree reader does not understand. The application uses bounded `PermutationExplainer` SHAP through the model's prediction API when a specialized explainer is unsupported. Both the multiclass test and a fresh browser-driven XGBoost run produced SHAP explanations. A separately labeled training permutation-importance fallback remains available if SHAP itself cannot run.

The passing backend suite emits four upstream deprecation warnings from MLflow/SQLAlchemy and SHAP/Matplotlib. They do not fail the current workflow. The large Plotly bundle is loaded only on results screens; the production build keeps it separate from the main application bundle.

## Not verified on this host

- **Live Gemini/Groq requests:** protocol, schema and error handling tests passed using mocked transports. Live use needs a configured provider key and model.
- **Docker containers:** Docker Engine is not installed here. Dockerfiles, Compose services, mounts and proxy configuration were inspected; container builds, Linux permissions and runtime behavior remain unverified.
- **Linux/macOS and hosted CI:** configuration is included, but these environments were not executed.
- **Production scale/security:** this is a localhost, single-user application, not an authenticated multi-tenant service. Test datasets are synthetic; metrics do not establish performance on a user's future dataset.

The machine-readable summary is in [verification-results.json](verification-results.json).

## Standalone report image repair

The original HTML export referred to EDA PNG files with relative paths, so downloading only the HTML produced broken image links. The export now embeds each PNG and reads chart JSON explicitly as UTF-8, preserving non-ASCII chart titles on Windows. Existing completed report exports can be rebuilt from saved artifacts with `scripts.repair_reports`; the repair refreshes download metadata without retraining or changing measured results.

After this change, **13 targeted backend tests passed**, covering standalone image contents, UTF-8 titles, missing/invalid images, classification and regression report generation, repair/download consistency, unchanged models and findings, and the existing pipeline scenarios. The repaired user report was downloaded through the REST endpoint and opened offline in Edge: all **6 PNG images** and **3 interactive charts** loaded, with no browser page errors. The browser workflow test now also checks a newly generated HTML download in an isolated offline browser context with no adjacent image directory.

Both updated browser tests passed, including a fresh pipeline run followed by standalone offline HTML verification. ESLint and Python compilation also passed after the repair.

Before GitHub publication, the complete backend suite was rerun: **30 passed**, with the same four upstream deprecation warnings. The frontend production build and ESLint also passed again.
