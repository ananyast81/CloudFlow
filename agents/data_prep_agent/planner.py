"""Standalone preparation adapter. The full workflow planner is main.py."""
from shared.data import infer_target
from shared.schemas import DataPrepPlan, PlannedOperation


def get_operation_catalogue():
    from agents.data_prep_agent.operations import OPERATION_CATALOGUE
    return OPERATION_CATALOGUE


def create_data_prep_plan(problem_statement: str, dataset_profile: dict) -> DataPrepPlan:
    columns = [item["name"] for item in dataset_profile["column_profiles"]]
    operations = [PlannedOperation(operation=name, reason=reason) for name, reason in [
        ("inspect_missing", "Measure missing values without fitting imputers."),
        ("inspect_duplicates", "Identify exact duplicate rows."),
        ("inspect_types", "Record observed data types.")]]
    if dataset_profile.get("duplicate_rows", 0):
        operations.append(PlannedOperation(operation="remove_duplicates", params={"keep": "first"}, reason="Remove exact duplicates before splitting."))
    operations.append(PlannedOperation(operation="verify_dataset", reason="Verify the prepared output."))
    return DataPrepPlan(target_required=False, target_column=infer_target(columns, problem_statement),
        relevant_columns=columns, operations=operations,
        reasoning="Conservative standalone cleaning. Learned imputers, encoders and scalers belong inside the full pipeline's training folds.")


def validate_plan(plan, df):
    columns = set(df.columns)
    if plan.target_required and plan.target_column not in columns:
        raise ValueError("A valid target column is required.")
    if set(plan.relevant_columns + plan.identifier_columns) - columns:
        raise ValueError("The plan references unknown columns.")
    for item in plan.operations:
        if item.operation not in get_operation_catalogue():
            raise ValueError("Unsupported operation.")
        referenced = item.params.get("columns", [])
        if not isinstance(referenced, list) or set(referenced) - columns:
            raise ValueError("Invalid operation column selection.")
