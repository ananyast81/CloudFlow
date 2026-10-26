"""Data Understanding agent used by the LangGraph application."""
from pathlib import Path

import pandas as pd

from shared.config import Settings
from shared.contracts import AnalysisPlan, PipelineState
from shared.data import infer_target, infer_task, prepare_data, profile_frame, save_preparation
from shared.files import write_json
from shared.llm import LLMError, Reasoner, ReasoningSuggestion, record_usage


def run(state: PipelineState, run_dir: Path, settings: Settings) -> dict:
    original = pd.read_csv(run_dir / "input.csv")
    profile = profile_frame(original)
    target = state.options.target_column or infer_target(list(original.columns), state.objective)
    requested_task = state.options.task_type
    reasoning = "Local planning from column names, target values and explicit user choices. Review before training."
    warnings = list(state.warnings)
    usage_status, usage_error = "disabled", None
    if state.options.use_llm:
        try:
            suggestion = Reasoner(settings).request("Suggest the target and classification/regression task. Use null when ambiguous.",
                {"objective": state.objective, "profile": profile, "requested_target": target,
                 "requested_task": requested_task}, ReasoningSuggestion)
            if suggestion.target_column is not None and suggestion.target_column not in original.columns:
                raise LLMError("unknown_column")
            proposed_target = target or suggestion.target_column
            proposed_task = requested_task
            if requested_task == "auto" and suggestion.task_type is not None:
                # A task suggested for another target must not leak onto this target.
                if target and suggestion.target_column not in (None, target):
                    raise LLMError("conflicting_target")
                if proposed_target:
                    values = original[proposed_target].dropna()
                    numeric = pd.to_numeric(values, errors="coerce")
                    if suggestion.task_type == "regression" and (
                        not numeric.notna().all() or numeric.isin([float("inf"), -float("inf")]).any()
                    ):
                        raise LLMError("incompatible_task")
                    if suggestion.task_type == "classification" and values.nunique() > 30:
                        raise LLMError("incompatible_task")
                proposed_task = suggestion.task_type
            # Apply only after all validation; explicit choices remain authoritative.
            target, requested_task = proposed_target, proposed_task
            reasoning = "AI interpretation (explicit user choices take precedence): " + suggestion.reasoning
            usage_status = "succeeded"
        except Exception as exc:
            usage_status = "fallback"
            usage_error = exc.code if isinstance(exc, LLMError) else type(exc).__name__
            warnings.append(f"AI planning unavailable ({usage_error}); local planning was used.")
    record_usage(run_dir, settings, "planning", usage_status, usage_error)
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
