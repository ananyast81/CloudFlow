"""Analysis & Features agent: training-only EDA and a reviewable feature proposal."""
import json
import re
from pathlib import Path

from agents.eda_agent.chart_planning_tools import build_chart_plan
from agents.eda_agent.chart_rendering_tools import render_chart_plan
from agents.eda_agent.eda_tools import summarize_dataset
from shared.contracts import PipelineState
from shared.data import load_prepared
from shared.eda_schemas import ChartConfig, TargetConfig
from shared.files import write_json
from shared.features import describe_strategy


def run(state: PipelineState, run_dir: Path, settings) -> dict:
    plan = state.plan.model_copy(deep=True)
    df = load_prepared(run_dir, plan)
    split = json.loads((run_dir / "split.json").read_text())
    training = df.iloc[split["train"]]
    excluded = {}
    for col in plan.feature_columns:
        values = training[col]
        if values.nunique() <= 1:
            excluded[col] = "Empty or constant in training rows."
        elif re.search(r"(^id$|_id$|^id_|identifier$)", col, re.I):
            excluded[col] = "Identifier-like name; excluded by default."
        elif values.dtype == object and values.nunique() > 100 and values.nunique() / len(values) > 0.8:
            excluded[col] = "Mostly unique text; unsuitable for bounded tabular encoding."
    features = [c for c in plan.feature_columns if c not in excluded]
    if not features:
        raise ValueError("No usable features remain after excluding identifiers, constant values and unique text.")
    plan.feature_columns = features
    # EDA sees no holdout values. Chart count and pair limits bound work.
    summary = summarize_dataset(training[features + [plan.target_column]],
        target=TargetConfig(target_column=plan.target_column, task_type=plan.task_type))
    summary.chart_plan = build_chart_plan(summary, ChartConfig(max_charts=6, max_per_kind=2))
    eda_dir = run_dir / "eda"
    eda_dir.mkdir(exist_ok=True)
    # A changed target rebuilds the EDA checkpoint. Replace only generated chart files.
    for previous in (eda_dir / "plots").glob("*.png"):
        previous.unlink()
    render_chart_plan(summary, eda_dir)
    # All public artifact paths are relative to the run directory.
    for plot in summary.plots:
        plot.path = (eda_dir / plot.path).resolve().relative_to(run_dir.resolve()).as_posix()
    for request in summary.chart_plan.selected:
        if request.path:
            request.path = (eda_dir / request.path).resolve().relative_to(run_dir.resolve()).as_posix()
    if summary.target_analysis:
        summary.target_analysis.plot_paths = [p.path for p in summary.plots if plan.target_column in p.columns or p.column == plan.target_column]
    eda = summary.model_dump(mode="json")
    eda["scope"] = "training rows only"
    eda["excluded_features"] = excluded
    eda["feature_strategy"] = describe_strategy(plan)
    write_json(eda_dir / "summary.json", eda)
    write_json(run_dir / "plan.json", plan.model_dump())
    warnings = list(state.warnings)
    if plan.task_type == "classification":
        counts = training[plan.target_column].value_counts()
        if counts.min() / counts.max() < 0.25:
            warnings.append("Class imbalance detected. Review per-class recall as well as weighted F1.")
    warnings.append("Random splitting assumes independent rows; time series and grouped observations need a task-specific split.")
    return {"plan": plan.model_dump(), "eda": eda, "warnings": list(dict.fromkeys(warnings))}
