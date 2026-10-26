import numpy as np
import pandas as pd

from agents.data_prep_agent.agent import run_data_prep
from shared.dataset_split import split_dataset
from shared.modeling import TrainingInput


def test_legacy_regression_split_returns_disjoint_partitions(regression_data):
    specification = TrainingInput(run_id='regression', dataset_path='unused.csv', problem_stmt='Predict price',
        target_column='price', task_type='regression', feature_columns=['area', 'rooms'], primary_metric='rmse')
    X_train, X_test, y_train, y_test = split_dataset(regression_data, specification)
    assert len(X_train) + len(X_test) == len(regression_data)
    assert set(X_train.index).isdisjoint(X_test.index)
    assert X_train.index.equals(y_train.index) and X_test.index.equals(y_test.index)


def test_standalone_preparation_needs_no_llm_key(tmp_path, monkeypatch):
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    input_path = tmp_path / 'input.csv'
    pd.DataFrame({'x': [1., 1., 2., np.nan], 'label': ['a', 'a', 'b', 'b']}).to_csv(input_path, index=False)
    frame, report = run_data_prep(input_path, 'Inspect label and x', 'standalone', tmp_path)
    assert len(frame) == 3
    assert frame['x'].isna().sum() == 1  # no leakage-prone imputation before a split
    assert (tmp_path / 'standalone/data-prep/cleaned.csv').is_file()
    assert report['status'] == 'completed'
