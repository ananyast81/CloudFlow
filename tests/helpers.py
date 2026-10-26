import json

from orchestrator.execution import execute_run
from shared.repository import RunRepository


def submit(client, frame, **options):
    response = client.post('/api/runs', files={"file": ("test.csv", frame.to_csv(index=False).encode(), "text/csv")},
        data={"objective": "Predict the outcome and explain influential factors.", "options": json.dumps(options)})
    assert response.status_code == 202, response.text
    return response.json()["run_id"]


def execute(settings, run_id):
    repository = RunRepository(settings.workspace)
    record = repository.claim("test-worker")
    assert record is not None and record.run_id == run_id
    execute_run(settings, run_id, "test-worker")
    return repository.get(run_id)


def approve(client, record, models=None):
    plan = record.state.plan.model_dump()
    if models is not None:
        plan["models"] = models
    response = client.post(f"/api/runs/{record.run_id}/approval", json={"approved": True, "plan": plan})
    assert response.status_code == 202, response.text
