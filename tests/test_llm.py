import json

import httpx
import pytest

from shared.config import Settings
from shared.llm import Reasoner, ReasoningSuggestion


@pytest.mark.parametrize('provider', ['groq', 'gemini'])
def test_provider_protocol_and_schema_validation(monkeypatch, tmp_path, provider):
    config = Settings(workspace=tmp_path, llm_provider=provider, llm_api_key='test-key', llm_model='test-model')
    captured = []
    def send(request):
        captured.append(request)
        payload = {'target_column': 'Churn', 'task_type': 'classification', 'reasoning': 'Explicit target.'}
        envelope = {'choices': [{'message': {'content': json.dumps(payload)}}]} if provider == 'groq' else {'candidates': [{'content': {'parts': [{'text': json.dumps(payload)}]}}]}
        return httpx.Response(200, json=envelope)
    original_client = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: original_client(transport=httpx.MockTransport(send)))
    suggestion = Reasoner(config).request('Plan the task.', {'objective': 'Predict Churn'}, ReasoningSuggestion)
    assert suggestion.target_column == 'Churn'
    request = captured[0]
    assert ('api.groq.com' if provider == 'groq' else 'generativelanguage.googleapis.com') == request.url.host
    assert 'test-key' not in str(request.url)


def test_provider_errors_do_not_expose_secrets(monkeypatch, tmp_path):
    cfg = Settings(workspace=tmp_path, llm_provider='gemini', llm_api_key='secret-test', llm_model='test')
    original = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: original(transport=httpx.MockTransport(lambda request: httpx.Response(401, text='secret-test'))))
    with pytest.raises(ValueError) as error:
        Reasoner(cfg).request('Plan', {}, ReasoningSuggestion)
    assert 'secret-test' not in str(error.value)
