"""Reporting agent: verifiable report, explainability and reproducibility artifacts."""
import hashlib
import importlib.metadata
import json
from pathlib import Path

import nbformat
import joblib
import pandas as pd
import plotly.graph_objects as go

from agents.eval_report_agent.explain import explain
from agents.eval_report_agent.html_report import write_html_report
from shared.contracts import PipelineState
from shared.files import write_json
from shared.data import load_prepared
from shared.llm import Reasoner, ReportNarrative


def run(state: PipelineState, run_dir: Path, settings) -> dict:
    explanation, warning = explain(state, run_dir)
    warnings = list(state.warnings) + ([warning] if warning else [])
    evaluation = state.evaluation
    best = next(c for c in state.candidates if c.candidate_id == state.selected_candidate_id)
    saved_pipeline = joblib.load(run_dir / "model.joblib")["pipeline"]
    prepared = load_prepared(run_dir, state.plan)
    partitions = json.loads((run_dir / "split.json").read_text())
    transformer = saved_pipeline.named_steps["features"]
    for label in ("train", "test"):
        rows = prepared.iloc[partitions[label]]
        transformed = transformer.transform(rows[state.plan.feature_columns])
        export = pd.DataFrame(transformed, columns=transformer.get_feature_names_out(), index=rows.index)
        export.index.name = "source_row_index"
        export.to_csv(run_dir / f"features_{label}.csv", index=True)
    lower = state.plan.primary_metric in {"mae", "rmse"}
    comparison = go.Figure(go.Bar(x=[c.candidate_id for c in state.candidates],
        y=[-c.cv_score if lower else c.cv_score for c in state.candidates],
        error_y={"type": "data", "array": [c.cv_std for c in state.candidates]},
        marker_color=["#3558dd" if c.candidate_id == best.candidate_id else "#bcc9ef" for c in state.candidates]))
    comparison.update_layout(title="Model comparison · training cross-validation", template="plotly_white", height=380,
        yaxis_title=state.plan.primary_metric, margin={"t": 55, "b": 100, "l": 55, "r": 25})
    write_json(run_dir / "comparison-chart.json", json.loads(comparison.to_json()))
    score = evaluation["primary_score"]
    answer = (f"For '{state.plan.target_column}', {best.model_name} achieved {state.plan.primary_metric} "
              f"{score:.4f} on {evaluation['test_rows']} held-out rows. "
              + ("It improved on the baseline." if evaluation["beats_baseline"] else "It did not improve on the baseline."))
    recommendations = [
        "Review the error examples and per-class or residual diagnostics before using predictions.",
        "Validate on new data from the intended deployment population.",
        "Check whether each selected feature is available at prediction time to rule out target leakage."]
    if not evaluation["beats_baseline"]:
        recommendations.insert(0, "Collect better predictors or more representative data before considering deployment.")
    narrative = None
    if state.options.use_llm:
        try:
            narrative = Reasoner(settings).request("Interpret the evidence and suggest next steps. Do not introduce new numerical claims.",
                {"objective": state.objective, "answer": answer, "evaluation": evaluation,
                 "top_features": explanation["importance"][:8], "warnings": warnings}, ReportNarrative).model_dump()
        except Exception as exc:
            warnings.append(f"AI report narrative unavailable ({type(exc).__name__}); evidence-based local report retained.")
    report = {"title": "CloudFlow analysis report", "run_id": state.run_id, "objective": state.objective,
        "answer": answer, "planning_mode": settings.llm_provider if state.options.use_llm else "local",
        "plan": state.plan.model_dump(), "dataset_summary": state.profile, "preparation": state.preparation,
        "eda_scope": "Training rows only", "eda_findings": {
            "excluded_features": state.eda.get("excluded_features", {}),
            "feature_strategy": state.eda.get("feature_strategy", {}),
            "numeric_summaries": state.eda.get("numeric_summaries", {}),
            "target_analysis": state.eda.get("target_analysis")},
        "models": [c.model_dump() for c in state.candidates], "evaluation": evaluation,
        "explainability": {k: v for k, v in explanation.items() if k != "local_explanations"},
        "recommendations": recommendations, "warnings": list(dict.fromkeys(warnings)),
        "ai_narrative": narrative, "limitations": evaluation["limitations"]}
    write_json(run_dir / "report.json", report)
    markdown = ["# CloudFlow analysis report", "", state.objective, "", "## Answer", answer,
        "", "## Dataset and preparation", f"{state.profile['rows']} raw rows; {state.preparation['rows_after']} cleaned rows.",
        *[f"- {step}" for step in state.preparation["steps"]], "", "## Approved plan",
        f"Target: {state.plan.target_column}; task: {state.plan.task_type}.",
        "Features: " + ", ".join(state.plan.feature_columns), "", "## Holdout metrics",
        *[f"- {key}: {value:.6f}" if value is not None else f"- {key}: unavailable" for key, value in evaluation["metrics"].items()],
        "", "## Models tested (training CV)", *[f"- {c.candidate_id}: {(-c.cv_score if lower else c.cv_score):.6f} ± {c.cv_std:.6f}" for c in state.candidates],
        "", "## EDA and feature preparation", *[f"- {key}: {value}" for key, value in state.eda.get("feature_strategy", {}).items()],
        "", "## Explainability", explanation["method"], *[f"- {item['feature']}: {item['importance']:.6f}" for item in explanation["importance"][:15]],
        "", "## Diagnostics", *[f"- {r}" for r in evaluation.get("retry_reasons", [])],
        f"Baseline score on the same holdout: {evaluation['baseline_score']:.6f}.",
        "", "## Recommendations", *[f"- {r}" for r in recommendations],
        "", "## Limitations and warnings", *[f"- {w}" for w in [*evaluation["limitations"], *warnings]]]
    if narrative:
        markdown += ["", "## AI interpretation (review against measured results)", narrative["interpretation"], *[f"- {r}" for r in narrative["recommendations"]]]
    (run_dir / "report.md").write_text("\n".join(markdown), encoding="utf-8")
    write_html_report(run_dir, "\n".join(markdown), state.eda.get("plots", []))
    notebook = nbformat.v4.new_notebook(cells=[
        nbformat.v4.new_markdown_cell("# CloudFlow reproducibility notebook\nRun from the downloaded artifact directory using the project environment. Only load model files you trust."),
        nbformat.v4.new_code_cell("import json\nfrom pathlib import Path\nimport pandas as pd\nimport joblib\nroot = Path('.')\nreport = json.loads((root / 'report.json').read_text(encoding='utf-8'))\nreport['evaluation']['metrics']"),
        nbformat.v4.new_code_cell("bundle = joblib.load(root / 'model.joblib')\nplan = bundle['plan']\ndata = pd.read_csv(root / 'data-prep' / 'cleaned.csv')\nbundle['pipeline'].predict(data[plan['feature_columns']].head())"),
        nbformat.v4.new_code_cell("import plotly.graph_objects as go\ngo.Figure(json.loads((root / 'comparison-chart.json').read_text())).show()"),
        nbformat.v4.new_markdown_cell("To rerun training, use `python -m scripts.reproduce --run-dir <artifact-directory>`. It uses the saved plan, options, split, dataset, seed and candidate grid. The notebook itself was generated, not executed.")])
    nbformat.write(notebook, run_dir / "reproduce.ipynb")
    versions = {name: importlib.metadata.version(name) for name in ["pandas", "numpy", "scikit-learn", "xgboost", "shap", "mlflow", "langgraph", "plotly", "matplotlib"]}
    write_json(run_dir / "reproducibility.json", {"schema_version": 1, "run_id": state.run_id,
        "options": state.options.model_dump(), "plan": state.plan.model_dump(),
        "split": json.loads((run_dir / "split.json").read_text()), "versions": versions,
        "selected_candidate_id": best.candidate_id, "final_round": state.attempt,
        "split_sha256": state.preparation["split_sha256"],
        "cleaned_dataset_sha256": hashlib.sha256((run_dir / 'data-prep/cleaned.csv').read_bytes()).hexdigest()})
    if best.mlflow_run_id:
        try:
            from shared.tracking import ExperimentTracker
            client = ExperimentTracker(settings).client
            for name in ["report.json", "report.html", "explainability.json", "reproducibility.json"]:
                client.log_artifact(best.mlflow_run_id, str(run_dir / name))
        except Exception as exc:
            warnings.append(f"MLflow report upload failed ({type(exc).__name__}).")
    return {"report": report, "warnings": list(dict.fromkeys(warnings))}
