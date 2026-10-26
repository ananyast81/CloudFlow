"""Bounded SHAP attribution with a clearly identified permutation fallback."""
import json
import re

import joblib
import numpy as np
import plotly.graph_objects as go
from sklearn.inspection import permutation_importance

from agents.feature_ml_agent.main import SCORERS
from agents.modeling.models import EncodedClassifier
from shared.data import load_prepared
from shared.files import write_json


def explain(state, run_dir):
    plan = state.plan
    frame = load_prepared(run_dir, plan)
    split = json.loads((run_dir / "split.json").read_text())
    train = frame.iloc[split["train"]][plan.feature_columns]
    test = frame.iloc[split["test"]]
    X = test[plan.feature_columns].head(24)
    bundle = joblib.load(run_dir / "model.joblib")
    pipeline = bundle["pipeline"]
    feature_pipeline = pipeline.named_steps["features"]
    model = pipeline.named_steps["model"]
    if isinstance(model, EncodedClassifier):
        model = model.estimator_
    warning = None
    try:
        import shap

        background = feature_pipeline.transform(train.head(32))
        transformed = feature_pipeline.transform(X)
        names = feature_pipeline.get_feature_names_out().tolist()
        def readable(name):
            return re.sub(r"f(\d+)(?=_|$)", lambda match: plan.feature_columns[int(match.group(1))], name, count=1)
        names = [readable(name.replace("numeric__", "").replace("categorical__", "")) for name in names]
        if transformed.shape[1] > 160:
            raise ValueError("Transformed feature count exceeds the SHAP explanation budget of 160.")
        specialized_failure = None
        explanation = None
        try:
            if hasattr(model, "feature_importances_"):
                explainer = shap.TreeExplainer(model)
                explanation = explainer(transformed, check_additivity=False)
            elif hasattr(model, "coef_"):
                explainer = shap.LinearExplainer(model, background)
                explanation = explainer(transformed)
        except Exception as exc:
            # XGBoost may change its internal model format before TreeExplainer supports it.
            # Its public prediction API still supports model-agnostic SHAP attribution.
            specialized_failure = type(exc).__name__
        if explanation is None:
            # Kernel/SVM, baseline and unsupported tree formats share a finite budget.
            transformed = transformed[:5]
            predict = model.predict_proba if hasattr(model, "predict_proba") else model.predict
            explainer = shap.PermutationExplainer(predict, background[:12], seed=state.options.random_state)
            explanation = explainer(transformed, max_evals=2 * transformed.shape[1] + 1)
        values = np.asarray(explanation.values)
        importance = np.abs(values).mean(axis=0)
        if importance.ndim == 2:
            importance = importance.mean(axis=-1)
        pairs = sorted(zip(names, importance.tolist()), key=lambda pair: pair[1], reverse=True)
        result = {"method": "SHAP", "explainer": type(explainer).__name__,
            "specialized_explainer_error": specialized_failure,
            "scope": "Transformed features; multiclass magnitudes averaged across outputs.",
            "sample_rows": len(values), "importance": [{"feature": name, "importance": value} for name, value in pairs],
            "local_explanations": {"feature_names": names, "values": values[:5].tolist(),
                                   "base_values": np.asarray(explanation.base_values)[:5].tolist(),
                                   "source_row_indices": test.index[:min(5, len(values))].tolist()}}
    except Exception as exc:
        warning = f"SHAP could not explain this model ({type(exc).__name__}). Training-set permutation importance is shown instead."
        training_rows = frame.iloc[split["train"]].head(200)
        output = permutation_importance(pipeline, training_rows[plan.feature_columns], training_rows[plan.target_column],
            scoring=SCORERS[plan.primary_metric], n_repeats=3, random_state=state.options.random_state, n_jobs=1)
        pairs = sorted(zip(plan.feature_columns, output.importances_mean.tolist()), key=lambda pair: pair[1], reverse=True)
        result = {"method": "Permutation importance", "scope": "Training sample; importance may be optimistic.",
                  "sample_rows": len(training_rows), "importance": [{"feature": n, "importance": v} for n, v in pairs], "warning": warning}
    top = result["importance"][:15][::-1]
    figure = go.Figure(go.Bar(x=[p["importance"] for p in top], y=[p["feature"] for p in top], orientation="h", marker_color="#6383ee"))
    figure.update_layout(title=f"{result['method']} · feature influence", template="plotly_white", height=420,
                        margin={"l": 180, "t": 55, "r": 25, "b": 45}, xaxis_title="Mean absolute attribution" if result["method"] == "SHAP" else "Decrease in score")
    write_json(run_dir / "explainability.json", result)
    write_json(run_dir / "importance-chart.json", json.loads(figure.to_json()))
    return result, warning
