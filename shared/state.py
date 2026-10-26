# Defines what data gets passed form 1 agent to the next

from pydantic import BaseModel
from typing import Optional


# ---------- Data profiling ----------
class ColumnProfile(BaseModel):
    name: str
    dtype: str
    missing_count: int
    n_unique: int
    sample_values: list[str]

class DatasetProfiler(BaseModel):
    rows: int
    cols: int
    duplicate_rows: int
    duplicate_col_names: list[str]
    column_profiles: list[ColumnProfile]


# ---------- Data preparation ----------
class DataPrepResult(BaseModel):
    rows_before: int
    rows_after: int
    duplicates_removed: int
    issues_found: list[str]
    cleaning_steps: list[str]
    cleaned_dataset_path: list[str]


# The application has one canonical, validated cross-agent state.
from shared.contracts import PipelineState
