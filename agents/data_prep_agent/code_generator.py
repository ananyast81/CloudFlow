"""Produce reproducible notebook text from allowlisted operations, without an LLM."""
from pydantic import BaseModel, Field
from shared.schemas import DataPrepPlan


class GeneratedCell(BaseModel):
    step: int
    operation: str
    title: str
    params: dict = Field(default_factory=dict)
    code: str


class GeneratedNotebookCode(BaseModel):
    cells: list[GeneratedCell]


def generate_notebook_code(problem_statement, plan, dataset_profile):
    plan = DataPrepPlan.model_validate(plan)
    cells = []
    for index, item in enumerate(plan.operations, 1):
        code = f"df, details = execute_operation(df, {item.operation!r}, {item.params!r})\noperation_results['step_{index}'] = details"
        cells.append(GeneratedCell(step=index, operation=item.operation, title=item.reason, params=item.params, code=code))
    return GeneratedNotebookCode(cells=cells)
