# REST contract

Canonical base path: `/api`. Development UI requests are proxied from Vite to `127.0.0.1:8000`. Docker Nginx proxies the same prefix to the API service. Legacy unprefixed routes remain available for earlier clients. The full generated OpenAPI contract is served at `/openapi.json`, with Swagger UI at `/docs`.

| Method | Endpoint | Contract |
|---|---|---|
| GET | `/api/health` | API/storage status and automatic worker state |
| GET | `/api/config` | Limits, defaults, installed versions and non-secret provider configuration |
| POST | `/api/datasets/preview` | Multipart `file`, optional `objective`; full validation, profile and first eight rows |
| POST | `/api/runs` | Multipart `file`, `objective`, JSON string `options`; returns 202 and `run_id` |
| GET | `/api/runs?limit=25&offset=0` | Paginated run summaries, newest first |
| GET | `/api/runs/{id}` | Persisted run, per-agent status, schema-validated state and artifact inventory |
| GET | `/api/runs/{id}/events?after=0` | Ordered events with cursor IDs, time, stage, level and message |
| POST | `/api/runs/{id}/approval` | JSON `approved`, optional full `plan`, optional `comment`; returns 202 |
| POST | `/api/runs/{id}/cancel` | Cancel a queued, running or paused run |
| GET | `/api/runs/{id}/artifacts` | Relative paths, sizes, media types and SHA-256 hashes |
| GET | `/api/runs/{id}/artifacts/{path}` | Download a registered artifact; PNG and JSON can display inline |
| GET | `/api/runs/{id}/download` | ZIP bundle after completion/failure/cancellation |
| GET | `/api/experiments?limit=25&offset=0` | Candidate results from a paginated set of runs, including MLflow IDs |
| POST | `/api/runs/{id}/predict` | JSON `rows`, each containing all approved raw features; completed runs only |

## Run options

```json
{
  "target_column": "Churn",
  "task_type": "classification",
  "test_size": 0.2,
  "cv_folds": 3,
  "max_retries": 1,
  "random_state": 42,
  "use_llm": false
}
```

Task type may be `auto`, `classification` or `regression`. Holdout fraction is 0.1–0.4, folds 2–5, retries 0–2. Auto inference is only a proposal and always requires review. Unknown properties are rejected. At least 12 distinct usable rows and a nonconstant target are required. Classification supports 2–30 classes, with at least three examples per class and sufficient representation after splitting. CSV limits: 10 MB, 20,000 rows, 100 columns, 1,000,000 cells.

## Review

Read `state.plan` from the run. Submit the complete amended plan if editing, or omit it to approve the existing plan:

```json
{"approved": true, "comment": "Features are available at prediction time."}
```

Editable plan fields include `target_column`, `task_type`, `feature_columns`, `models`, `numeric_imputation`, `scale_numeric`, `balance_classes`, `derive_dates`, `select_features` and `primary_metric`. Candidate names are `linear`, `random_forest`, `svm`, `gradient_boosting`, `xgboost`; a dummy baseline is automatic. A target/task change causes a new review checkpoint. Declining stops the run.

Statuses: `queued → running → awaiting_approval → queued → running → completed`. `failed` and `cancelled` are terminal. API callers must poll the returned run ID; `POST /runs` acceptance is not completion.

## Prediction

```json
{"rows": [{"Age": 35, "MonthlyCharges": 89.0, "Contract": "Monthly"}]}
```

The response contains `predictions`, `target_column`, and classification `classes`/`probabilities` when supported. Supply every approved feature key; use JSON null for missing values. Unknown categories are handled by the fitted encoder. Predictions never fit preprocessing again. Maximum 500 rows per call. Model artifacts are loaded only from server-created run directories, never from a supplied model path.

Validation returns 422 (or 400 for unsupported file type), oversized files 413, missing runs/artifacts 404, and invalid state transitions 409. The frontend surfaces backend messages. Download paths must appear in the persisted artifact inventory and resolve inside the run directory.

`report.html` is a standalone download: its EDA PNGs use embedded data URLs and its interactive charts include the Plotly runtime. It can be opened offline without an adjacent `eda/plots` folder. The full ZIP continues to include the original individual PNG artifacts.
