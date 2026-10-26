import json
import hashlib
from io import BytesIO
from zipfile import ZipFile

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from scripts.reproduce import reproduce
from scripts.repair_reports import repair_report
from tests.test_reports import ImageSources
from shared.contracts import AnalysisPlan, RunOptions
from shared.data import prepare_data
from shared.features import build_feature_pipeline
from shared.repository import RunRepository
from tests.helpers import approve, execute, submit


@pytest.mark.parametrize('kind', ['classification', 'regression'])
def test_real_end_to_end_pipeline(kind, client, settings, classification_data, regression_data):
    frame = classification_data if kind == 'classification' else regression_data
    target = 'Churn' if kind == 'classification' else 'price'
    run_id = submit(client, frame, target_column=target, task_type=kind, max_retries=0)
    record = execute(settings, run_id)
    assert record.status == 'awaiting_approval', record.error
    assert not (settings.workspace / run_id / 'model.joblib').exists()
    assert record.state.eda['row_count'] == record.state.preparation['training_rows']
    assert target not in record.state.plan.feature_columns
    # Construct a fresh application and checkpointer: review survives process restarts.
    with TestClient(create_app(settings)) as restarted:
        review_record = RunRepository(settings.workspace).get(run_id)
        review_record.state.plan.numeric_imputation = 'mean'
        approve(restarted, review_record, ['linear', 'random_forest', 'svm', 'gradient_boosting', 'xgboost'])
    record = execute(settings, run_id)
    assert record.status == 'completed', record.error
    assert all(agent.status == 'completed' for agent in record.agents.values())
    assert {c.model_name for c in record.state.candidates} == {'baseline', 'linear', 'random_forest', 'svm', 'gradient_boosting', 'xgboost'}
    assert all(c.mlflow_run_id for c in record.state.candidates), record.state.warnings
    assert record.state.evaluation['test_evaluated_once'] is True
    assert record.state.report['explainability']['method'] == 'SHAP', record.state.warnings
    assert record.state.report['eda_findings']['feature_strategy']['numeric'].startswith('mean imputation')
    run_dir = settings.workspace / run_id
    for path in ['model.joblib', 'predictions.csv', 'report.json', 'report.html', 'report.md', 'reproduce.ipynb', 'reproducibility.json', 'explainability.json']:
        assert client.get(f'/api/runs/{run_id}/artifacts/{path}').status_code == 200
    response = client.get(f'/api/runs/{run_id}/download')
    with ZipFile(BytesIO(response.content)) as zipped:
        assert 'report.html' in zipped.namelist()
        assert 'input.csv' not in zipped.namelist()
        sources = ImageSources(zipped.read('report.html').decode('utf-8')).sources
        assert len(sources) == len(record.state.eda['plots']) > 0
        assert all(source.startswith('data:image/png;base64,') for source in sources)
    # Repair existing exports without touching the fitted model or measured findings.
    unchanged = {name: (run_dir / name).read_bytes() for name in ['model.joblib', 'report.json', 'predictions.csv']}
    (run_dir / 'report.html').write_text('<img src="eda/plots/missing.png">', encoding='utf-8')
    repaired = repair_report(settings, run_id)
    response = client.get(f'/api/runs/{run_id}/artifacts/report.html')
    assert response.content == repaired.read_bytes()
    assert all(source.startswith('data:image/png;base64,') for source in ImageSources(response.text).sources)
    artifact = next(a for a in client.get(f'/api/runs/{run_id}/artifacts').json()['artifacts'] if a['path'] == 'report.html')
    assert artifact['sha256'] == hashlib.sha256(response.content).hexdigest()
    assert all((run_dir / name).read_bytes() == contents for name, contents in unchanged.items())
    row = frame[record.state.plan.feature_columns].iloc[0].to_dict()
    prediction = client.post(f'/api/runs/{run_id}/predict', json={'rows': [row]})
    assert prediction.status_code == 200, prediction.text
    model = joblib.load(run_dir / 'model.joblib')['pipeline']
    expected = model.predict(pd.DataFrame([row]))[0]
    if kind == 'classification':
        assert prediction.json()['predictions'][0] == expected
        assert abs(sum(prediction.json()['probabilities'][0]) - 1) < 1e-6
    else:
        assert prediction.json()['predictions'][0] == pytest.approx(expected)
        assert 'rmse' in record.state.evaluation['metrics']
    assert client.post(f'/api/runs/{run_id}/predict', json={'rows': [{}]}).status_code == 422
    assert len(client.get('/api/experiments').json()['experiments']) == 6
    reproduce(run_dir)


def test_changed_target_requires_second_review(client, settings, classification_data):
    run_id = submit(client, classification_data, target_column='Churn', task_type='classification')
    record = execute(settings, run_id)
    assert record.status == 'awaiting_approval', record.error
    plan = record.state.plan.model_dump()
    plan.update(target_column='MonthlyCharges', task_type='regression', primary_metric='rmse', feature_columns=['Age', 'Contract'])
    response = client.post(f'/api/runs/{run_id}/approval', json={'approved': True, 'plan': plan})
    assert response.status_code == 202
    revised = execute(settings, run_id)
    assert revised.status == 'awaiting_approval', revised.error
    assert revised.state.plan.target_column == 'MonthlyCharges'
    assert revised.state.eda['target_analysis']['config']['task_type'] == 'regression'
    assert not revised.state.approved
    assert not (settings.workspace / run_id / 'model.joblib').exists()


def test_fold_preprocessing_and_inference_schema():
    plan = AnalysisPlan(target_column='y', task_type='regression', feature_columns=['x', 'category', 'signup_date', 'flag'], primary_metric='rmse')
    X = pd.DataFrame({'x': [1., 2., np.nan, 4.], 'category': ['a', 'a', None, 'b'],
        'signup_date': ['2024-01-01', '2024-02-01', None, '2024-03-01'], 'flag': [True, False, True, False]})
    pipeline = build_feature_pipeline(plan)
    train = pipeline.fit_transform(X)
    imputer = pipeline.named_steps['encode'].named_transformers_['numeric'].named_steps['impute']
    assert imputer.statistics_[0] == 2
    test = pd.DataFrame({'x': [10000.], 'category': ['new'], 'signup_date': ['bad'], 'flag': [True]})
    transformed = pipeline.transform(test)
    assert np.isfinite(transformed).all()
    assert transformed.shape[1] == train.shape[1]
    assert imputer.statistics_[0] == 2


def test_deduplication_and_target_missing_before_split(classification_data):
    frame = pd.concat([classification_data, classification_data.iloc[:5]], ignore_index=True)
    frame.loc[0, 'Churn'] = None
    cleaned, split, report = prepare_data(frame, 'Churn', 'classification', RunOptions())
    assert not cleaned.duplicated().any()
    assert not cleaned['Churn'].isna().any()
    assert set(split['train']).isdisjoint(split['test'])
    assert len(split['train']) + len(split['test']) == len(cleaned)
    assert report['duplicates_removed'] == 4


def test_bounded_retry_uses_cv_without_holdout(client, settings, classification_data, monkeypatch):
    from agents.evaluation_agent import main as evaluator
    from shared.contracts import CandidateResult, PipelineState
    plan = AnalysisPlan(target_column='Churn', task_type='classification', feature_columns=['Age'], primary_metric='accuracy')
    state = PipelineState(run_id='a' * 32, objective='Predict Churn', options=RunOptions(max_retries=1),
        plan=plan, approved=True, selected_candidate_id='linear_r0', candidates=[
            CandidateResult(candidate_id='baseline_r0', model_name='baseline', round=0, cv_score=.5, cv_std=.1, train_score=.5, parameters={}, duration_seconds=1),
            CandidateResult(candidate_id='linear_r0', model_name='linear', round=0, cv_score=.51, cv_std=.1, train_score=.9, parameters={}, duration_seconds=1)])
    def forbid_holdout(*args, **kwargs):
        raise AssertionError('Holdout loaded during retry decision')
    monkeypatch.setattr(evaluator, 'load_prepared', forbid_holdout)
    run_dir = settings.workspace / state.run_id
    run_dir.mkdir(parents=True)
    patch = evaluator.run(state, run_dir, settings)
    assert patch['retry'] is True and patch['attempt'] == 1
    assert 'metrics' not in patch['evaluation']


def test_worker_claims_once_and_expires_lease(settings, client, classification_data):
    run_id = submit(client, classification_data, target_column='Churn')
    first = RunRepository(settings.workspace)
    second = RunRepository(settings.workspace)
    assert first.claim('owner-a').run_id == run_id
    assert second.claim('owner-b') is None
    with first.connection() as db:
        db.execute('UPDATE runs SET lease=0 WHERE id=?', (run_id,))
    second.claim('owner-b')
    assert first.get(run_id).status == 'failed'


def test_multiclass_xgboost_label_roundtrip_and_selected_features(tmp_path):
    from agents.modeling.models import candidates
    from sklearn.datasets import load_iris
    iris = load_iris(as_frame=True)
    frame = iris.data
    labels = pd.Series([iris.target_names[index] for index in iris.target], name='species')
    plan = AnalysisPlan(target_column='species', task_type='classification', feature_columns=list(frame),
                        models=['xgboost'], primary_metric='f1_weighted', select_features=True)
    name, pipeline, _ = list(candidates(plan, 42, 0))[-1]
    assert name == 'xgboost'
    pipeline.fit(frame, labels)
    predicted = pipeline.predict(frame.iloc[:3])
    assert set(predicted).issubset(set(labels))
    probabilities = pipeline.predict_proba(frame.iloc[:3])
    assert probabilities.shape == (3, 3)
    assert np.allclose(probabilities.sum(axis=1), 1)
    assert pipeline.named_steps['features'].transform(frame).shape[1] == 3
    from agents.eval_report_agent.explain import explain
    from shared.contracts import PipelineState
    (tmp_path / 'data-prep').mkdir()
    frame.assign(species=labels).to_csv(tmp_path / 'data-prep/cleaned.csv', index=False)
    (tmp_path / 'split.json').write_text(json.dumps({'train': list(range(120)), 'test': list(range(120, 150))}))
    joblib.dump({'pipeline': pipeline, 'plan': plan.model_dump()}, tmp_path / 'model.joblib')
    explanation, warning = explain(PipelineState(run_id='a' * 32, objective='Predict species', options=RunOptions(), plan=plan), tmp_path)
    assert explanation['method'] == 'SHAP', warning
    assert len(explanation['importance']) == 3


def test_graph_retrains_within_limit_and_retains_best_candidate(client, settings):
    rng = np.random.default_rng(91)
    frame = pd.DataFrame({'x': rng.normal(size=160), 'label': rng.choice(['A', 'B'], 160)})
    run_id = submit(client, frame, target_column='label', task_type='classification', max_retries=1)
    record = execute(settings, run_id)
    assert record.status == 'awaiting_approval', record.error
    approve(client, record, ['linear'])
    record = execute(settings, run_id)
    assert record.status == 'completed', record.error
    assert record.state.attempt == 1
    assert {c.round for c in record.state.candidates} == {0, 1}
    assert len(record.state.candidates) == 4
    best = max(record.state.candidates, key=lambda c: c.cv_score)
    assert record.state.selected_candidate_id == best.candidate_id
    assert record.state.evaluation['test_evaluated_once'] is True
    assert (settings.workspace / run_id / 'diagnostics_round_0.json').is_file()
