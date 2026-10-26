"""Data Understanding agent used by the LangGraph application."""
from pathlib import Path

import pandas as pd

from shared.config import Settings
from shared.contracts import AnalysisPlan, PipelineState
from shared.data import infer_target, infer_task, prepare_data, profile_frame, save_preparation
from shared.files import write_json
from shared.llm import Reasoner, ReasoningSuggestion


def run(state: PipelineState, run_dir: Path, settings: Settings) -> dict:
    original = pd.read_csv(run_dir / "input.csv")
    profile = profile_frame(original)
    target = state.options.target_column or infer_target(list(original.columns), state.objective)
    requested_task = state.options.task_type
    reasoning = "Local planning from column names, target values and explicit user choices. Review before training."
    warnings = list(state.warnings)
    if state.options.use_llm:
        try:
            suggestion = Reasoner(settings).request("Suggest the target and classification/regression task. Use null when ambiguous.",
                {"objective": state.objective, "profile": profile, "requested_target": target}, ReasoningSuggestion)
            if not target and suggestion.target_column in original.columns:
                target = suggestion.target_column
            if requested_task == "auto" and suggestion.task_type in {"classification", "regression"}:
                requested_task = suggestion.task_type
            reasoning = suggestion.reasoning
        except Exception as exc:
            warnings.append(f"AI planning unavailable ({type(exc).__name__}); local planning was used.")
    if not target:
        raise ValueError("The target is ambiguous. Select a target column on New run and launch again.")
    if target not in original:
        raise ValueError(f"Target column '{target}' does not exist.")
    task = infer_task(original[target]) if requested_task == "auto" else requested_task
    cleaned, split, preparation = prepare_data(original, target, task, state.options)
    save_preparation(run_dir, cleaned, split, preparation)
    write_json(run_dir / "data-prep/profile.json", profile)
    features = [c for c in original if c != target]
    # Preserve an edited plan when the user requests a new target/task review.
    plan = state.plan if state.plan and state.plan.target_column == target and state.plan.task_type == task else AnalysisPlan(
        target_column=target, task_type=task, feature_columns=features,
        primary_metric="f1_weighted" if task == "classification" else "rmse", reasoning=reasoning)
    return {"profile": profile, "preparation": preparation, "plan": plan.model_dump(), "warnings": warnings}
