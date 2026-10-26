# LLM integration and verification

## Scope and baseline

Starting commit: `357ce91df19654f1ba9b4a7573507b6831778ba2` from `ananyast81/CloudFlow`, protected branch `codex/complete-synopsis-pipeline`.
Implementation branch: `codex/llm-integration`. All work was isolated in a separate worktree. No existing service was restarted or deployed.

The starting code already had Gemini/Groq adapters, optional problem interpretation, optional report narration, server-side configuration, `use_llm` API/frontend support, and three mocked provider tests. Configuration alone enabled requests, but did not fix validation, provenance, or evidence-minimization defects.

The initial long Windows path caused dependency installation and artifact-path failures. The unchanged suite first reported 26 passed and 4 failed (EDA artifact paths and MLflow logging). After moving only the new worktree to a shorter path and using an isolated environment, the unchanged suite passed: **30 passed, 4 upstream warnings**. No tests or application code were changed to obtain that baseline.

## Configuration and use

From the repository root, copy `.env.example` to `.env` only if no `.env` exists. Edit it locally or set backend environment variables:

```dotenv
LLM_PROVIDER=groq
LLM_API_KEY=your-provider-key
LLM_MODEL=your-account-model-id
```

For Gemini, set `LLM_PROVIDER=gemini`, use a Gemini key, and use the model ID without the `models/` prefix. Choose a JSON-capable model available in your account; no model availability is assumed. Restart your API and any external worker after changing configuration. Never commit populated `.env` files or put keys in frontend configuration.

```powershell
# Start locally using your project environment
.\.venv\Scripts\python.exe -m scripts.dev
```

Open New Run, upload a dataset, select target/task, and enable **Use AI reasoning**. Review the proposed plan before approving training. Existing runs do not change automatically. Settings and `/api/config` show whether configuration is present; this is not a live credential/connectivity test.

Provider references consulted: [Gemini generateContent](https://ai.google.dev/api/generate-content), [Groq API](https://console.groq.com/docs/api-reference), [Groq JSON output](https://console.groq.com/docs/structured-outputs). JSON mode still requires local schema validation.

## What changed and why

- Provider suggestions now reject unknown fields, unsupported tasks, unknown columns, and incompatible or mismatched target/task suggestions before applying any decision. Explicit user choices and reviewed plans retain precedence. Ambiguity still requires clarification.
- Empty, blocked, truncated, malformed, and oversized responses fail safely. Gemini thought parts are excluded from the final JSON response. Provider bodies, keys, and validation details are not included in warnings; only sanitized error codes are recorded. A response echoing the configured credential is rejected.
- Each stage makes one provider attempt, without automatic retries. Connection timeout: 10 seconds; read/write/pool timeouts: 45 seconds. Output token limits remain bounded. Serialized prompt limit: 48 KiB; decompressed response limit: 64 KiB. These HTTP operation limits are not a guaranteed total wall-clock deadline.
- Report prompts now contain a whitelist of aggregate evaluation metrics rather than the whole evaluation object, which included raw prediction/error examples.
- `llm-usage.json` records configuration and outcomes separately for planning and narration. Reports contain an AI usage section. Existing report `planning_mode` identifies a provider only after successful planning, instead of implying success whenever AI was enabled.

## Data shared and trusted execution

Planning receives the objective, column profiles (names, types, counts), and requested target/task. Narration receives the objective, measured answer, aggregate metrics, at most eight feature-importance entries, and a warning count. Feature names and objectives may contain user text; they remain untrusted data. Entire datasets, raw prediction/error records, class-label records, and local SHAP example records are not sent by the narration call.

The LLM returns validated suggestions or narrative text. Its interpretation still requires human review and is not independent verification. It cannot execute code or modify measured findings. Cleaning, splitting, EDA, feature transformations, CV, tuning, winner selection, retries, training, predictions, metrics, SHAP, and MLflow remain deterministic trusted implementations.

## Outcomes and fallback

- `configured`: configuration presence, not successful usage; recorded independently of status.
- `disabled`: AI was off and no provider call was made.
- `succeeded`: a response was received, validated, and accepted for that phase.
- `fallback`: the request or suggestion failed and local behavior was retained, with a sanitized warning.
- `not_attempted`: narration has not run yet.
- `unknown`: legacy planning provenance is unavailable; the report does not assume provider success.

Planning and narration can succeed/fail independently. For example, failed planning plus successful narration leaves `planning_mode=local` and includes AI narration. Reanalysis clears stale narration outcomes. AI-disabled runs make no provider calls even with credentials configured. The existing API rejects an AI-enabled run if configuration is incomplete. Existing saved reports are not rewritten automatically.

## Verification environment and commands

Windows x64, isolated Python 3.12.14 environment, dependencies installed from the existing `requirements.txt` without editing dependency manifests/lockfiles. This does not establish Python 3.11 pinned-lock compatibility. A temporary `Q:` alias avoided Windows installation-path limits; it pointed only at the isolated worktree. Application data and test artifacts stayed under its ignored `.audit/` directory.

```powershell
# Environment isolation for tests; no real provider credentials or tracking server
$env:LLM_PROVIDER='none'
$env:LLM_API_KEY=''
$env:LLM_MODEL=''
$env:MLFLOW_TRACKING_URI=''
$env:LANGSMITH_TRACING='false'
$env:CLOUDFLOW_WORKSPACE='Q:\.audit\app-workspace'
$env:MPLCONFIGDIR='Q:\.audit\matplotlib'

# Baseline, before edits
Q:\.audit\v\Scripts\python.exe -m pytest -q --basetemp=.audit/b
# Post-change
Q:\.audit\v\Scripts\python.exe -m pytest -q --basetemp=.audit/p
```

Verification results are recorded below after execution. Provider tests mock the HTTP boundary; pipeline tests execute real training, approval/resume, EDA, SHAP, MLflow, predictions, and report/download operations. No live provider request was authorized or executed; no credentials were requested in chat.

## Separate follow-up scope

The synopsis describes broader LLM decision-making. This change completes the existing problem-interpretation and narration paths only. Reasoning about feature strategy, model selection, and diagnostic improvement remains rule-based. Any additional LLM-assisted decisions need a separately reviewed scope, validation boundaries, and tests. Docker runtime/cloud deployment, public authentication/HTTPS, live-provider connectivity, and cross-platform/pinned-Python verification remain separate work. Frontend layout, numerical algorithms, orchestration, approval, shared schemas, and deployment architecture are unchanged.

## Executed results

- Baseline at the short worktree path: **30 passed**, 4 upstream deprecation warnings, 50.67 seconds.
- Full post-change suite: **76 passed**, 4 upstream deprecation warnings, 140.20 seconds.
- Six additional focused checks after test-import cleanup: **6 passed**, 49 deselected, 7.23 seconds. All 82 collected cases have therefore passed across these runs; a single combined 82-case run was not executed.
- Compared baseline/post-change classification and regression artifacts: aggregate metrics, primary/baseline scores, selected candidate IDs, test-row counts, and prediction CSV bytes were identical.
- `python -m compileall -q shared/llm.py shared/config.py agents/data_prep_agent/main.py agents/eval_report_agent/main.py tests/test_llm.py`: passed.
- `python -m pip check`: no broken requirements.
- `git diff --check`: passed.

The additional focused command was:

```powershell
Q:\.audit\v\Scripts\python.exe -m pytest -q tests/test_llm.py -k 'report_schema or thought_parts or reanalysis_preserves' --basetemp=.audit/f
```

Tests cover both providers, invalid JSON/fields/tasks, empty/blocked/truncated/oversized responses, authentication/rate-limit/server failures, timeouts/connections, missing configuration, explicit-choice precedence, ambiguity, instruction-like dataset text, response credential echoes, prompt limits, actual pipeline success/fallback/disabled outcomes, and preserved reviewed plans. Mocked success proves local handling, not real model availability or live credentials. Docker, cloud deployment, and frontend browser checks were not rerun because those components were not modified.
