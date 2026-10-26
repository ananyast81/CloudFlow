import json
import uuid

import pytest

from api.app import create_app
from fastapi.testclient import TestClient
from shared.repository import RunRepository
from tests.helpers import execute, submit


@pytest.mark.parametrize("name,contents,expected", [
    ("bad.txt", b"a,b\n1,2", 400), ("empty.csv", b"", 422),
    ("duplicate.csv", b"a,a\n1,2", 422), ("bad.csv", b"a,b\n1,2\n3,4,5", 422),
    ("nul.csv", b"a,b\n1,\x00", 422), ("headers.csv", b"a,b\n", 422),
    ("large.csv", b"a,b\n" + b"x" * (10 * 1024 * 1024), 413),
], ids=['wrong-extension', 'empty', 'duplicate-headers', 'row-width', 'nul-byte', 'no-data', 'over-size-limit'])
def test_reject_invalid_uploads(client, name, contents, expected):
    result = client.post('/api/datasets/preview', files={"file": (name, contents, "text/csv")})
    assert result.status_code == expected
    assert client.get('/api/runs').json()["total"] == 0


def test_preview_matches_backend_and_never_creates_run(client, classification_data):
    result = client.post('/api/datasets/preview', files={"file": ('churn.csv', classification_data.to_csv(index=False), 'text/csv')}, data={"objective": "Predict Churn"})
    assert result.status_code == 200
    data = result.json()
    assert data["suggested_target"] == "Churn"
    assert data["profile"]["rows"] == 100
    assert len(data["rows"]) == 8
    assert client.get('/api/runs').json()["total"] == 0


def test_api_contract_and_persistence(client, settings, classification_data):
    run_id = submit(client, classification_data, target_column="Churn")
    assert client.get(f'/api/runs/{run_id}').json()["status"] == "queued"
    assert RunRepository(settings.workspace).get(run_id).filename == "test.csv"
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get('/api/runs').json()["total"] == 1
        assert restarted.get(f'/runs/{run_id}').status_code == 200
    assert client.post(f'/api/runs/{run_id}/approval', json={"approved": True}).status_code == 409
    assert client.post(f'/api/runs/{run_id}/predict', json={"rows": [{"Age": 30}]}).status_code == 409
    assert client.get(f'/api/runs/{run_id}/download').status_code == 409
    assert client.post(f'/api/runs/{run_id}/cancel').status_code == 200
    assert client.post(f'/api/runs/{run_id}/cancel').status_code == 409
    assert client.get(f'/api/runs/{uuid.uuid4().hex}').status_code == 404
    assert client.get('/api/runs/invalid').status_code == 400
    assert client.get(f'/api/runs/{run_id}/artifacts/%2e%2e/runs.sqlite').status_code == 404


def test_options_and_llm_validation(client, classification_data):
    for options in ['{"max_retries":9}', '{"unknown":true}', '{"use_llm":true}', '{"target_column":"does_not_exist"}']:
        response = client.post('/api/runs', files={"file": ('x.csv', classification_data.to_csv(index=False))},
            data={"objective": "Predict customer churn", "options": options})
        assert response.status_code == 422, response.text
    config = client.get('/api/config').json()
    assert 'llm_api_key' not in json.dumps(config)


def test_approval_validation_and_rejection(client, settings, classification_data):
    run_id = submit(client, classification_data, target_column="Churn")
    record = execute(settings, run_id)
    assert record.status == "awaiting_approval", record.error
    plan = record.state.plan.model_dump()
    plan['feature_columns'].append('Churn')
    assert client.post(f'/api/runs/{run_id}/approval', json={"approved": True, "plan": plan}).status_code == 422
    response = client.post(f'/api/runs/{run_id}/approval', json={"approved": False, "comment": "Wrong question"})
    assert response.status_code == 202
    assert client.get(f'/api/runs/{run_id}').json()["status"] == "cancelled"
    assert RunRepository(settings.workspace).claim("other-worker") is None


def test_cors(client):
    allowed = client.options('/api/runs', headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert allowed.headers['access-control-allow-origin'] == 'http://localhost:5173'
    blocked = client.options('/api/runs', headers={"Origin": "https://untrusted.invalid", "Access-Control-Request-Method": "POST"})
    assert 'access-control-allow-origin' not in blocked.headers
