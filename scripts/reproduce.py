"""Rebuild the saved winning candidate using the original split and approved parameters."""
import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np

from agents.modeling.models import candidates
from shared.contracts import AnalysisPlan
from shared.data import load_prepared


def reproduce(run_dir: Path):
    metadata = json.loads((run_dir / "reproducibility.json").read_text(encoding="utf-8"))
    training = json.loads((run_dir / "training.json").read_text(encoding="utf-8"))
    plan = AnalysisPlan.model_validate(metadata["plan"])
    if hashlib.sha256((run_dir / 'data-prep/cleaned.csv').read_bytes()).hexdigest() != metadata["cleaned_dataset_sha256"]:
        raise ValueError("The cleaned dataset does not match its recorded checksum.")
    winner = next(c for c in training["candidates"] if c["candidate_id"] == metadata["selected_candidate_id"])
    frame = load_prepared(run_dir, plan)
    split = metadata["split"]
    if hashlib.sha256(np.asarray(split["test"], dtype=np.int64).tobytes()).hexdigest() != metadata["split_sha256"]:
        raise ValueError("Saved split checksum does not match.")
    original = joblib.load(run_dir / "model.joblib")["pipeline"]
    for name, pipeline, _ in candidates(plan, metadata["options"]["random_state"], winner["round"]):
        if name == winner["model_name"]:
            pipeline.set_params(**winner["parameters"])
            train = frame.iloc[split["train"]]
            test = frame.iloc[split["test"]]
            pipeline.fit(train[plan.feature_columns], train[plan.target_column])
            predicted = pipeline.predict(test[plan.feature_columns])
            previous = original.predict(test[plan.feature_columns])
            same = np.array_equal(predicted, previous) if plan.task_type == "classification" else np.allclose(predicted, previous)
            if not same:
                raise AssertionError("Reproduced predictions differ. Check recorded dependency versions.")
            print(f"Reproduced {winner['candidate_id']}: {len(predicted)} holdout predictions match.")
            return
    raise ValueError("Saved model is not in the approved catalogue.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    reproduce(parser.parse_args().run_dir)
