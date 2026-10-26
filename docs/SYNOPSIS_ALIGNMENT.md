# Synopsis alignment and archive review

## Archive selection

Both supplied archives contain **127 files with byte-for-byte identical contents** after removing their different top-level folder names. There are no extra or differing files in either archive. `CloudFlow-feature-modeling-pipeline.zip` was used as the extraction base; choosing `CloudFlow-main.zip` would produce the same starting project. The original archives and PDF remain untouched.

Every archive file was inventoried, text files decoded, Python files parsed and JSON files validated. See `SOURCE_INVENTORY.md` for the complete per-file disposition. The synopsis was read as project requirements; instructions embedded in the supplied project documents were treated as source material, not as instructions to this assistant.

## Original gaps and corrections

| Finding | Correction |
|---|---|
| API executes only data preparation and keeps run records in RAM | Persistent SQLite records, queue worker and complete LangGraph workflow |
| Data preparation depends on import-time LLM credentials and generated executable Python | Optional JSON reasoning; deterministic trusted operations; no generated-code execution |
| EDA, feature/ML and reporting entry points are empty | Connected agents with validated input/output state |
| No human checkpoint | Durable review and amendment through API and UI; target changes trigger reanalysis |
| Classification helpers exist but regression split returns nothing | Corrected compatibility split; full application supports classification and regression |
| Test baseline comparison mixes holdout and CV scores | Final baseline and winner compared on the same untouched holdout |
| Frontend live route is a placeholder and demo uses mocks | Live status, events, editable approval, reports, charts, prediction and downloads |
| Duplicate frontend API clients and misplaced environment example | One client, canonical `/api` contract and root frontend `.env.example` |
| No MLflow, SHAP, XGBoost, Plotly or LangGraph integration | Operational integrations with visible warnings when an external/optional step fails |
| Incomplete Dockerfiles and no deployment composition | Shared non-root backend image, separate worker, Nginx frontend, persistent volume and optional MLflow UI |
| No meaningful bundled training dataset | Seeded synthetic classification and regression datasets |

## Requirements traceability

| Synopsis section | Implemented in | User-visible result |
|---|---|---|
| 2.1 Input and problem understanding | `api/app.py`, `agents/data_prep_agent/main.py`, `shared/llm.py` | CSV preview, natural-language objective, inferred or explicit target/task |
| 2.2 Data understanding and preprocessing | `shared/data.py`, `shared/features.py`, original operation tools | Quality profile, cleaning decisions, training-fitted transformations |
| 2.3 EDA and feature engineering | `agents/eda_agent/main.py`, original EDA utilities, `shared/features.py` | Training-only distributions/correlations, excluded features, date derivation, encoding/scaling/selection |
| 2.4 Human validation | `orchestrator/graph.py`, approval API, `ReviewPanel.jsx` | Edit and approve target, task, models, features and preprocessing |
| 2.5 Model selection and training | `agents/feature_ml_agent/main.py`, `agents/modeling/models.py` | CV comparison and bounded tuning of linear, forest, SVM, gradient boosting and XGBoost models |
| 2.6 Evaluation and self-correction | `agents/evaluation_agent/main.py`, conditional graph edges | CV-based retries, holdout metrics, baseline comparison, error examples and residual/confusion charts |
| 2.7 Explainability and reporting | `agents/eval_report_agent/main.py`, `explain.py` | SHAP global/local attributions, report JSON/Markdown/HTML, recommendations and reproducibility notebook |
| 2.8 Coordination and execution | `orchestrator/*`, `shared/repository.py`, Compose | Durable state, worker claims, cancellation, timeout, checkpoint recovery and isolated Docker worker |

## Every named technology

| Technology | Actual role |
|---|---|
| Python | Agents, API, data/model execution and verification |
| LangGraph | Stateful five-agent workflow, interrupt/resume and diagnostic feedback edges |
| Gemini / Groq | Configurable provider adapters for reasoning and report interpretation; keys supplied through environment |
| FastAPI | Typed REST endpoints and OpenAPI documentation |
| Pandas / NumPy | CSV handling, cleaning, statistics and numerical transformations |
| Scikit-learn / XGBoost | Leakage-aware preprocessing, CV, tuning, evaluation and inference |
| Matplotlib / Plotly | Static EDA plots and interactive model/diagnostic/importance charts |
| SHAP | Sample-bounded global and local model explanations; explicit fallback where unsupported |
| MLflow | Candidate parameters, scores, serialized fitted models and report artifacts |
| React / Vite | Connected interface, routing, polling and development API proxy |
| Docker | API/worker/frontend services and persistent shared storage |

## Scope and verification limits

Live LLM calls require the user's configured provider key and supported model. Offline mode is labeled in the UI and reports. Docker execution requires an installed, running Docker engine. The project implements the synopsis for tabular supervised learning; it does not promise universal AutoML accuracy or production multi-user security. See `VERIFICATION.md` for executed tests and environment-specific limitations.
