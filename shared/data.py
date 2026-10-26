"""Dataset boundaries and a single reproducible holdout split."""
import hashlib
import re
from io import BytesIO
from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from agents.eda_agent.csv_tools import load_csv_dataset
from shared.config import Settings
from shared.contracts import AnalysisPlan, RunOptions
from shared.eda_schemas import CSVReadLimits
from shared.files import json_safe, write_json


def read_upload(contents: bytes, settings: Settings) -> pd.DataFrame:
    df = load_csv_dataset(BytesIO(contents), limits=CSVReadLimits(
        max_bytes=settings.max_upload_bytes, max_rows=settings.max_rows,
        max_columns=settings.max_columns, max_cells=1_000_000))
    if any(len(c) > 200 or any(ord(ch) < 32 for ch in c) for c in df.columns):
        raise ValueError("Column names must be at most 200 characters and contain no control characters.")
    if len(df.columns) < 2:
        raise ValueError("Provide a target and at least one feature column.")
    return df


def normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for col in result:
        if pd.api.types.is_object_dtype(result[col]) or pd.api.types.is_string_dtype(result[col]):
            result[col] = result[col].map(lambda x: x.strip() if isinstance(x, str) else x)
            result[col] = result[col].replace("", np.nan)
        elif pd.api.types.is_numeric_dtype(result[col]):
            result[col] = result[col].replace([np.inf, -np.inf], np.nan)
    return result


def infer_target(columns: list[str], objective: str) -> str | None:
    mentioned = [c for c in columns if re.search(r"(?<!\w)" + re.escape(c.lower().replace("_", " ")) + r"(?!\w)", objective.lower().replace("_", " "))]
    if len(mentioned) == 1:
        return mentioned[0]
    conventional = [c for c in columns if c.lower() in {"target", "label", "outcome", "churn", "y"}]
    return conventional[0] if len(conventional) == 1 else None


def infer_task(series: pd.Series) -> str:
    values = series.dropna()
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().all() and values.nunique() > 12:
        return "regression"
    return "classification"


def profile_frame(df: pd.DataFrame) -> dict:
    normalized = normalize_frame(df)
    return json_safe({"rows": len(df), "columns": len(df.columns),
        "missing_cells": int(normalized.isna().sum().sum()),
        "duplicate_rows": int(normalized.duplicated().sum()),
        "column_profiles": [{"name": c, "dtype": str(df[c].dtype),
            "missing_count": int(normalized[c].isna().sum()),
            "unique_count": int(normalized[c].nunique())} for c in df],
        "column_names": df.columns.tolist()})


def prepare_data(df: pd.DataFrame, target: str, task_type: str, options: RunOptions):
    if target not in df:
        raise ValueError(f"Target column '{target}' is not present in the dataset.")
    cleaned = normalize_frame(df)
    duplicate_count = int(cleaned.duplicated().sum())
    cleaned = cleaned.drop_duplicates()
    missing_target = int(cleaned[target].isna().sum())
    cleaned = cleaned.dropna(subset=[target]).copy()
    if task_type == "regression":
        values = pd.to_numeric(cleaned[target], errors="coerce")
        if values.isna().any() or not np.isfinite(values).all():
            raise ValueError("Regression requires a finite numeric target. Correct invalid values or choose classification.")
        cleaned[target] = values.astype(float)
    else:
        cleaned[target] = cleaned[target].astype(str)
    cleaned = cleaned.reset_index(drop=True)
    if len(cleaned) < 12:
        raise ValueError("At least 12 usable, distinct rows are required for a holdout and cross-validation.")
    if cleaned[target].nunique() < 2:
        raise ValueError("The target must contain at least two distinct values.")
    stratify = None
    if task_type == "classification":
        counts = cleaned[target].value_counts()
        if len(counts) > 30 or counts.min() < 3:
            raise ValueError("Classification supports 2-30 classes with at least 3 rows per class. Check the target or add examples.")
        stratify = cleaned[target]
        if min(ceil(len(cleaned) * options.test_size), len(cleaned) - ceil(len(cleaned) * options.test_size)) < len(counts):
            raise ValueError("The holdout is too small to contain every class. Increase test size or add examples.")
    train, test = train_test_split(np.arange(len(cleaned)), test_size=options.test_size,
                                  random_state=options.random_state, stratify=stratify)
    if stratify is not None and cleaned.iloc[train][target].value_counts().min() < 2:
        raise ValueError("Every training class needs at least two rows for cross-validation. Add examples or reduce test size.")
    report = {"rows_before": len(df), "rows_after": len(cleaned), "duplicates_removed": duplicate_count,
        "missing_target_rows_removed": missing_target, "training_rows": len(train), "test_rows": len(test),
        "steps": ["Normalize blank text and infinite numeric values to missing.",
                  f"Remove {duplicate_count} exact duplicate rows before splitting.",
                  f"Remove {missing_target} rows without a target; never impute labels.",
                  "Reserve a reproducible holdout; fit imputation, encoding, scaling and feature selection inside training folds."],
        "split_strategy": "stratified random" if stratify is not None else "random",
        "split_sha256": hashlib.sha256(np.asarray(test, dtype=np.int64).tobytes()).hexdigest()}
    return cleaned, {"train": train.tolist(), "test": test.tolist()}, report


def save_preparation(run_dir: Path, df, split, report):
    (run_dir / "data-prep").mkdir(exist_ok=True)
    df.to_csv(run_dir / "data-prep/cleaned.csv", index=False)
    write_json(run_dir / "split.json", split)
    write_json(run_dir / "data-prep/preparation_report.json", report)


def load_prepared(run_dir: Path, plan: AnalysisPlan):
    # Explicit string target preserves labels like 0/1 and avoids cross-stage dtype drift.
    dtype = {plan.target_column: str} if plan.task_type == "classification" else None
    return pd.read_csv(run_dir / "data-prep/cleaned.csv", dtype=dtype)


def validate_plan_columns(plan: AnalysisPlan, df: pd.DataFrame) -> None:
    missing = set([plan.target_column, *plan.feature_columns]) - set(df.columns)
    if missing:
        raise ValueError(f"Unknown columns in the plan: {', '.join(sorted(missing))}")
