"""Modeling agent. Every candidate uses the same training-only CV folds."""
import hashlib
import json
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.model_selection import GridSearchCV, KFold, StratifiedKFold

from agents.modeling.models import candidates
from shared.contracts import CandidateResult, PipelineState
from shared.data import load_prepared, validate_plan_columns
from shared.files import write_json
from shared.tracking import ExperimentTracker
from shared.repository import RunRepository

SCORERS = {"f1_weighted": "f1_weighted", "accuracy": "accuracy", "rmse": "neg_root_mean_squared_error", "mae": "neg_mean_absolute_error", "r2": "r2"}


def run(state: PipelineState, run_dir: Path, settings) -> dict:
    if not state.approved:
        raise ValueError("Training requires an approved analysis plan.")
    plan = state.plan
    frame = load_prepared(run_dir, plan)
    validate_plan_columns(plan, frame)
    split = json.loads((run_dir / "split.json").read_text())
    train = frame.iloc[split["train"]]
    X, y = train[plan.feature_columns], train[plan.target_column]
    folds = state.options.cv_folds
    if plan.task_type == "classification":
        folds = min(folds, int(y.value_counts().min()))
        splitter = StratifiedKFold(folds, shuffle=True, random_state=state.options.random_state)
    else:
        folds = min(folds, len(y) // 2)
        splitter = KFold(folds, shuffle=True, random_state=state.options.random_state)
    if folds < 2:
        raise ValueError("There are too few training examples for cross-validation.")
    fixed_folds = list(splitter.split(X, y))
    results = list(state.candidates)
    warnings = list(state.warnings)
    model_dir = run_dir / "models"
    model_dir.mkdir(exist_ok=True)
    tracker = None
    try:
        tracker = ExperimentTracker(settings)
    except Exception as exc:
        warnings.append(f"MLflow could not initialize ({type(exc).__name__}); local results remain available.")
    dataset_hash = hashlib.sha256((run_dir / "input.csv").read_bytes()).hexdigest()
    succeeded = 0
    for name, pipeline, grid in candidates(plan, state.options.random_state, state.attempt):
        candidate_id = f"{name}_r{state.attempt}"
        RunRepository(settings.workspace).event(state.run_id, "modeling", f"Training {candidate_id} with {folds} cross-validation folds.")
        start = time.monotonic()
        try:
            search = GridSearchCV(pipeline, grid, scoring=SCORERS[plan.primary_metric], cv=fixed_folds,
                                  n_jobs=1, return_train_score=True, error_score="raise", refit=True)
            search.fit(X, y)
            index = search.best_index_
            scores = [search.cv_results_[f"split{fold}_test_score"][index] for fold in range(folds)]
            if not np.isfinite(scores).all():
                raise ValueError("Cross-validation returned non-finite scores.")
            result = CandidateResult(candidate_id=candidate_id, model_name=name, round=state.attempt,
                cv_score=float(search.best_score_), cv_std=float(np.std(scores)),
                train_score=float(search.cv_results_["mean_train_score"][index]),
                parameters=search.best_params_, duration_seconds=time.monotonic() - start)
            path = model_dir / f"{candidate_id}.joblib"
            joblib.dump(search.best_estimator_, path)
            if tracker:
                try:
                    result.mlflow_run_id = tracker.log_candidate(state.run_id, result, plan, state.options, dataset_hash, path)
                except Exception as exc:
                    warnings.append(f"MLflow logging failed for {candidate_id} ({type(exc).__name__}).")
            results.append(result)
            RunRepository(settings.workspace).event(state.run_id, "modeling", f"Finished {candidate_id}; CV score {result.cv_score:.4f}.")
            if name != "baseline":
                succeeded += 1
        except Exception as exc:
            warnings.append(f"{candidate_id} failed: {type(exc).__name__}: {str(exc)[:250]}")
            RunRepository(settings.workspace).event(state.run_id, "modeling", f"Candidate {candidate_id} failed ({type(exc).__name__}).", "warning")
    if not succeeded and not any(c.model_name != "baseline" for c in results):
        raise ValueError("All predictive candidates failed. " + " ".join(warnings[-5:]))
    # Baseline can win: do not claim predictive improvement where none exists.
    winner = max(results, key=lambda c: c.cv_score)
    best = joblib.load(model_dir / f"{winner.candidate_id}.joblib")
    joblib.dump({"pipeline": best, "plan": plan.model_dump(), "schema_version": 1}, run_dir / "model.joblib")
    summary = {"candidates": [c.model_dump() for c in results], "selected_candidate_id": winner.candidate_id,
        "primary_metric": plan.primary_metric, "cv_folds": folds, "score_direction": "higher is better; MAE/RMSE are negated",
        "selection": "Highest training cross-validation score across all approved candidates and retry rounds. The test set was not used."}
    write_json(run_dir / "training.json", summary)
    return {"candidates": summary["candidates"], "selected_candidate_id": winner.candidate_id, "warnings": warnings}
