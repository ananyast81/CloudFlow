"""MLflow tracking is real; failures are surfaced as warnings, never fabricated IDs."""
from pathlib import Path

from mlflow import MlflowClient

from shared.config import Settings


class ExperimentTracker:
    def __init__(self, settings: Settings):
        self.client = MlflowClient(tracking_uri=settings.tracking_uri)
        experiment = self.client.get_experiment_by_name("CloudFlow")
        if experiment is None:
            try:
                self.experiment_id = self.client.create_experiment("CloudFlow", artifact_location=(settings.workspace / "mlartifacts").as_uri())
            except Exception:
                self.experiment_id = self.client.get_experiment_by_name("CloudFlow").experiment_id
        else:
            self.experiment_id = experiment.experiment_id

    def log_candidate(self, run_id: str, candidate, plan, options, dataset_hash: str, model_path: Path):
        record = self.client.create_run(self.experiment_id, tags={
            "mlflow.runName": f"{run_id[:8]} / {candidate.candidate_id}", "cloudflow.run_id": run_id,
            "cloudflow.candidate_id": candidate.candidate_id, "dataset.sha256": dataset_hash,
            "task_type": plan.task_type, "target": plan.target_column})
        tracking_id = record.info.run_id
        try:
            for key, value in {**candidate.parameters, "random_state": options.random_state,
                               "cv_folds_requested": options.cv_folds, "test_size": options.test_size,
                               "primary_metric": plan.primary_metric, "round": candidate.round}.items():
                self.client.log_param(tracking_id, key, value)
            self.client.log_metric(tracking_id, "cv_score", candidate.cv_score)
            self.client.log_metric(tracking_id, "cv_std", candidate.cv_std)
            self.client.log_metric(tracking_id, "train_score", candidate.train_score)
            self.client.log_metric(tracking_id, "duration_seconds", candidate.duration_seconds)
            self.client.log_artifact(tracking_id, str(model_path), "model")
            self.client.set_terminated(tracking_id, "FINISHED")
        except Exception:
            self.client.set_terminated(tracking_id, "FAILED")
            raise
        return tracking_id
