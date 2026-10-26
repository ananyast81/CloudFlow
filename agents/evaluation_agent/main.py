"""CV-only feedback followed by one final holdout evaluation."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix, f1_score,
    mean_absolute_error, mean_squared_error, precision_score, r2_score, recall_score, roc_auc_score)

from shared.contracts import PipelineState
from shared.data import load_prepared
from shared.files import json_safe, write_json


def run(state: PipelineState, run_dir: Path, settings) -> dict:
    plan = state.plan
    best = next(c for c in state.candidates if c.candidate_id == state.selected_candidate_id)
    baseline = max((c for c in state.candidates if c.model_name == "baseline"), key=lambda c: c.cv_score)
    reasons = []
    if best.model_name == "baseline" or best.cv_score <= baseline.cv_score + 0.01 * max(1, abs(baseline.cv_score)):
        reasons.append("Cross-validation has not established a useful improvement over the baseline.")
    gap = best.train_score - best.cv_score
    if gap > max(0.1, 0.25 * abs(best.cv_score)):
        reasons.append("Training score exceeds validation score, suggesting overfitting.")
    if plan.task_type == "classification" and best.cv_score < 0.65:
        reasons.append("Cross-validation classification score is below the 0.65 review threshold.")
    diagnostics = {"retry_reasons": reasons, "round": state.attempt, "cv_train_gap": gap,
        "retry_basis": "Training cross-validation only; holdout remains untouched during retries."}
    if reasons and state.attempt < state.options.max_retries:
        write_json(run_dir / f"diagnostics_round_{state.attempt}.json", diagnostics)
        return {"retry": True, "attempt": state.attempt + 1, "evaluation": diagnostics}

    frame = load_prepared(run_dir, plan)
    split = json.loads((run_dir / "split.json").read_text())
    test = frame.iloc[split["test"]]
    X, y = test[plan.feature_columns], test[plan.target_column]
    pipeline = joblib.load(run_dir / "model.joblib")["pipeline"]
    predicted = pipeline.predict(X)
    baseline_pipeline = joblib.load(run_dir / "models" / f"{baseline.candidate_id}.joblib")
    baseline_predicted = baseline_pipeline.predict(X)
    warnings = list(state.warnings)
    if plan.task_type == "classification":
        metrics = {"accuracy": accuracy_score(y, predicted), "precision_weighted": precision_score(y, predicted, average="weighted", zero_division=0),
            "recall_weighted": recall_score(y, predicted, average="weighted", zero_division=0),
            "f1_weighted": f1_score(y, predicted, average="weighted", zero_division=0)}
        labels = pipeline.classes_.tolist()
        matrix = confusion_matrix(y, predicted, labels=labels).tolist()
        per_class = classification_report(y, predicted, labels=labels, output_dict=True, zero_division=0)
        baseline_score = (accuracy_score(y, baseline_predicted) if plan.primary_metric == "accuracy" else f1_score(y, baseline_predicted, average="weighted", zero_division=0))
        try:
            probabilities = pipeline.predict_proba(X)
            metrics["roc_auc"] = roc_auc_score(y, probabilities[:, 1] if len(labels) == 2 else probabilities,
                labels=labels, multi_class="ovr", average="weighted")
        except (AttributeError, ValueError):
            metrics["roc_auc"] = None
            warnings.append("ROC-AUC is unavailable for this fitted model or holdout class coverage.")
        figure = go.Figure(go.Heatmap(z=matrix, x=labels, y=labels, colorscale="Blues", showscale=True))
        figure.update_layout(title="Holdout confusion matrix", xaxis_title="Predicted", yaxis_title="Actual")
        error_rows = [{"row_index": int(idx), "actual": str(actual), "prediction": str(pred)}
                      for idx, actual, pred in zip(test.index, y, predicted) if actual != pred][:25]
        extra = {"labels": labels, "confusion_matrix": matrix, "per_class": per_class,
                 "error_count": int(np.sum(np.asarray(y) != predicted))}
    else:
        metrics = {"mae": mean_absolute_error(y, predicted), "rmse": np.sqrt(mean_squared_error(y, predicted)), "r2": r2_score(y, predicted)}
        baseline_metrics = {"mae": mean_absolute_error(y, baseline_predicted), "rmse": np.sqrt(mean_squared_error(y, baseline_predicted)), "r2": r2_score(y, baseline_predicted)}
        baseline_score = baseline_metrics[plan.primary_metric]
        residuals = np.asarray(y) - predicted
        figure = go.Figure(go.Scatter(x=np.asarray(predicted[:1000]).tolist(), y=residuals[:1000].tolist(), mode="markers", marker={"color": "#4669e8", "opacity": 0.65}))
        figure.update_layout(title="Holdout residuals (up to 1,000 rows)", xaxis_title="Prediction", yaxis_title="Actual minus prediction")
        order = np.argsort(np.abs(residuals))[::-1][:25]
        error_rows = [{"row_index": int(test.index[i]), "actual": float(y.iloc[i]), "prediction": float(predicted[i]), "absolute_error": float(abs(residuals[i]))} for i in order]
        extra = {"residual_mean": float(residuals.mean()), "residual_std": float(residuals.std())}
    figure.update_layout(template="plotly_white", margin={"t": 55, "b": 45, "l": 55, "r": 25}, height=380)
    # list values, rather than typed binary arrays, keep the frontend chart contract simple.
    write_json(run_dir / "evaluation-chart.json", json.loads(figure.to_json()))
    primary = metrics[plan.primary_metric]
    lower = plan.primary_metric in {"mae", "rmse"}
    beats = primary < baseline_score if lower else primary > baseline_score
    result = json_safe({**diagnostics, **extra, "metrics": metrics, "primary_metric": plan.primary_metric,
        "primary_score": primary, "baseline_score": baseline_score, "beats_baseline": beats,
        "test_rows": len(test), "selected_candidate_id": best.candidate_id, "selected_model": best.model_name,
        "cv_score": -best.cv_score if lower else best.cv_score,
        "generalization_gap": primary + best.cv_score if lower else best.cv_score - primary,
        "error_examples": error_rows, "test_evaluated_once": True, "retry_limit_reached": bool(reasons),
        "limitations": ["Cross-validation scores used for tuning are optimistic; use the untouched test metrics for final assessment.",
                         "Associations and feature attributions do not establish causation.",
                         "The exported model is fitted on training rows only, preserving the reported holdout evaluation."]})
    if not beats:
        warnings.append("The selected model did not beat the holdout baseline. Treat it as an experiment, not a deployment recommendation.")
    output = pd.DataFrame({"source_row_index": test.index, "actual": y.to_numpy(), "prediction": predicted})
    output.to_csv(run_dir / "predictions.csv", index=False)
    write_json(run_dir / "evaluation.json", result)
    if best.mlflow_run_id:
        try:
            from shared.tracking import ExperimentTracker
            client = ExperimentTracker(settings).client
            for key, value in metrics.items():
                if value is not None and np.isfinite(value):
                    client.log_metric(best.mlflow_run_id, f"holdout_{key}", float(value))
            client.log_artifact(best.mlflow_run_id, str(run_dir / "evaluation.json"))
        except Exception as exc:
            warnings.append(f"MLflow final metric logging failed ({type(exc).__name__}).")
    return {"evaluation": result, "retry": False, "warnings": list(dict.fromkeys(warnings))}
