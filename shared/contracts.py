"""Versioned, JSON-only state and REST contracts. No DataFrames in checkpoints."""
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

TaskType = Literal["classification", "regression"]
ModelName = Literal["linear", "random_forest", "svm", "gradient_boosting", "xgboost"]
RunStatus = Literal["queued", "running", "awaiting_approval", "completed", "failed", "cancelled"]
STAGES = ["data_understanding", "analysis_features", "human_review", "modeling", "evaluation", "reporting"]
TERMINAL = {"completed", "failed", "cancelled"}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class RunOptions(Contract):
    target_column: str | None = Field(default=None, max_length=200)
    task_type: Literal["auto", "classification", "regression"] = "auto"
    test_size: float = Field(default=0.2, ge=0.1, le=0.4)
    cv_folds: int = Field(default=3, ge=2, le=5)
    max_retries: int = Field(default=1, ge=0, le=2)
    random_state: int = Field(default=42, ge=0, le=2**31 - 1)
    use_llm: bool = False


class AnalysisPlan(Contract):
    target_column: str = Field(min_length=1, max_length=200)
    task_type: TaskType
    feature_columns: list[str] = Field(min_length=1, max_length=100)
    models: list[ModelName] = Field(default_factory=lambda: ["linear", "random_forest", "xgboost"], min_length=1, max_length=5)
    numeric_imputation: Literal["median", "mean"] = "median"
    scale_numeric: bool = True
    balance_classes: bool = True
    derive_dates: bool = True
    select_features: bool = False
    primary_metric: Literal["f1_weighted", "accuracy", "rmse", "mae", "r2"]
    reasoning: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def coherent(self):
        if self.target_column in self.feature_columns:
            raise ValueError("The target cannot be included in the feature columns.")
        if len(set(self.feature_columns)) != len(self.feature_columns) or len(set(self.models)) != len(self.models):
            raise ValueError("Features and models must be unique.")
        metrics = {"classification": {"f1_weighted", "accuracy"}, "regression": {"rmse", "mae", "r2"}}
        if self.primary_metric not in metrics[self.task_type]:
            raise ValueError("The primary metric does not match the task type.")
        return self


class ReviewDecision(Contract):
    approved: bool
    plan: AnalysisPlan | None = None
    comment: str = Field(default="", max_length=1000)


class AgentProgress(Contract):
    status: Literal["pending", "running", "completed", "waiting", "failed", "cancelled"] = "pending"
    summary: str = "Waiting for the previous stage."
    decisions: list[str] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None


class CandidateResult(Contract):
    candidate_id: str
    model_name: str
    round: int
    cv_score: FiniteFloat
    cv_std: FiniteFloat
    train_score: FiniteFloat
    parameters: dict[str, Any]
    duration_seconds: FiniteFloat
    mlflow_run_id: str | None = None


class PipelineState(Contract):
    schema_version: int = 1
    run_id: str
    objective: str
    options: RunOptions
    plan: AnalysisPlan | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    preparation: dict[str, Any] = Field(default_factory=dict)
    eda: dict[str, Any] = Field(default_factory=dict)
    candidates: list[CandidateResult] = Field(default_factory=list)
    selected_candidate_id: str | None = None
    evaluation: dict[str, Any] = Field(default_factory=dict)
    report: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    attempt: int = 0
    retry: bool = False
    approved: bool = False


class RunRecord(Contract):
    run_id: str
    filename: str
    objective: str
    options: RunOptions
    status: RunStatus = "queued"
    stage: str = "queued"
    created_at: str = Field(default_factory=utcnow)
    updated_at: str = Field(default_factory=utcnow)
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    dataset_sha256: str
    agents: dict[str, AgentProgress] = Field(default_factory=lambda: {key: AgentProgress() for key in STAGES})
    state: PipelineState | None = None
    approval: ReviewDecision | None = None
    artifacts: list[dict[str, Any]] = Field(default_factory=list)


class PredictionRequest(Contract):
    rows: list[dict[str, str | int | FiniteFloat | bool | None]] = Field(min_length=1, max_length=500)
