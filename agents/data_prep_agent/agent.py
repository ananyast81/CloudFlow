"""Backward-compatible standalone data preparation. Full runs use orchestrator.graph."""
import re
from pathlib import Path

from agents.data_prep_agent.code_generator import generate_notebook_code
from agents.data_prep_agent.notebook_runner import run_notebook
from agents.data_prep_agent.planner import create_data_prep_plan, validate_plan
from agents.data_prep_agent.profiler import profile_df
from shared.dataset_validation import load_dataset
from shared.files import write_json

DEFAULT_WORKSPACE = Path(__file__).resolve().parents[2] / "workspace"


def run_data_prep(input_path, problem_statement, run_id, workspace_root=DEFAULT_WORKSPACE):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", str(run_id)):
        raise ValueError("Invalid run ID.")
    if not problem_statement.strip():
        raise ValueError("The problem statement cannot be blank.")
    original = load_dataset(str(input_path))
    initial = profile_df(original).model_dump()
    plan = create_data_prep_plan(problem_statement, initial)
    validate_plan(plan, original)
    generated = generate_notebook_code(problem_statement, plan, initial)
    output = Path(workspace_root).resolve() / run_id / "data-prep"
    prepared, report = run_notebook(generated, input_path, output)
    report.update(run_id=run_id, problem_statement=problem_statement, status="completed",
                  initial_profile=initial, final_profile=profile_df(prepared).model_dump(), plan=plan.model_dump())
    write_json(output / "initial_profile.json", initial)
    write_json(output / "operation_plan.json", plan.model_dump())
    write_json(output / "preparation_report.json", report)
    return prepared, report
