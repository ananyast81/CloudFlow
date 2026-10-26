"""Fitted, serializable raw-column conversion is also applied during inference."""
import re

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.feature_selection import SelectPercentile, f_classif, f_regression
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from shared.contracts import AnalysisPlan


def describe_strategy(plan: AnalysisPlan) -> dict:
    return {
        "numeric": f"{plan.numeric_imputation} imputation, missing indicators" + (", standard scaling" if plan.scale_numeric else ""),
        "categorical": "Missing category, one-hot encoding, at most 32 levels per column; unknown categories supported.",
        "derived": "Year, month and weekday from date columns, detected within training folds." if plan.derive_dates else "Disabled",
        "selection": "Keep the top 75% inside each training fold." if plan.select_features else "Use the approved raw feature columns.",
        "imbalance": "Balanced class weights for linear, forest and SVM models." if plan.balance_classes and plan.task_type == "classification" else "No class weighting.",
    }


class RawFeatures(TransformerMixin, BaseEstimator):
    def __init__(self, derive_dates=True):
        self.derive_dates = derive_dates

    def fit(self, X, y=None):
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        self.kinds_ = {}
        for col in X:
            values = X[col].dropna()
            if pd.api.types.is_numeric_dtype(X[col]) and not pd.api.types.is_bool_dtype(X[col]):
                kind = "numeric"
            elif len(values) and pd.to_numeric(values, errors="coerce").notna().all():
                kind = "numeric"
            elif self.derive_dates and re.search(r"date|timestamp|_at$", col, re.I) and len(values) and pd.to_datetime(values, errors="coerce", format="mixed", utc=True).notna().mean() > 0.9:
                kind = "date"
            else:
                kind = "categorical"
            self.kinds_[col] = kind
        return self

    def transform(self, X):
        missing = set(self.feature_names_in_) - set(X.columns)
        if missing:
            raise ValueError(f"Missing prediction columns: {sorted(missing)}")
        output = {}
        for index, (col, kind) in enumerate(self.kinds_.items()):
            values = X[col]
            # Internal feature names avoid collisions with arbitrary uploaded column names.
            key = f"f{index}"
            if kind == "numeric":
                output[key] = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).astype(float)
            elif kind == "date":
                dates = pd.to_datetime(values, errors="coerce", format="mixed", utc=True)
                output[key + "_year"] = dates.dt.year.astype(float)
                output[key + "_month"] = dates.dt.month.astype(float)
                output[key + "_weekday"] = dates.dt.dayofweek.astype(float)
            else:
                output[key] = values.map(lambda value: np.nan if pd.isna(value) or str(value).strip() == "" else str(value).strip()).astype(object)
        return pd.DataFrame(output, index=X.index)

    def get_feature_names_out(self, input_features=None):
        names = []
        for index, kind in enumerate(self.kinds_.values()):
            names.extend([f"f{index}_year", f"f{index}_month", f"f{index}_weekday"] if kind == "date" else [f"f{index}"])
        return np.asarray(names, dtype=object)


def build_feature_pipeline(plan: AnalysisPlan) -> Pipeline:
    numeric = [("impute", SimpleImputer(strategy=plan.numeric_imputation, keep_empty_features=True, add_indicator=True))]
    if plan.scale_numeric:
        numeric.append(("scale", StandardScaler()))
    categorical = Pipeline([("impute", SimpleImputer(strategy="constant", fill_value="__missing__", keep_empty_features=True)),
        ("encode", OneHotEncoder(handle_unknown="infrequent_if_exist", max_categories=32, min_frequency=2, sparse_output=False))])
    transformer = ColumnTransformer([
        ("numeric", Pipeline(numeric), make_column_selector(dtype_include=np.number)),
        ("categorical", categorical, make_column_selector(dtype_exclude=np.number))], remainder="drop")
    steps = [("raw", RawFeatures(derive_dates=plan.derive_dates)), ("encode", transformer)]
    if plan.select_features:
        steps.append(("select", SelectPercentile(f_classif if plan.task_type == "classification" else f_regression, percentile=75)))
    return Pipeline(steps)
