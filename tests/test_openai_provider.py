import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ticket_router.ai.openai_provider import OpenAIProvider
from ticket_router.config import config
from ticket_router.errors import AIUnavailableError

VALID_ARGS = {
    "category": "Billing",
    "priority": "Medium",
    "assignedTeam": "Billing Team",
    "reasoning": "Some reason.",
    "confidence": 0.9,
}


def _fake_response(arguments: dict) -> SimpleNamespace:
    tool_call = SimpleNamespace(function=SimpleNamespace(arguments=json.dumps(arguments)))
    message = SimpleNamespace(tool_calls=[tool_call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _fake_response_without_tool_call() -> SimpleNamespace:
    message = SimpleNamespace(tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")
    yield


def _provider_with_mock_client(mock_create):
    provider = OpenAIProvider()
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=mock_create))
    )
    return provider


def test_succeeds_and_records_the_model_used():
    mock_create = MagicMock(return_value=_fake_response(VALID_ARGS))
    provider = _provider_with_mock_client(mock_create)

    raw = provider.route_ticket("some ticket text")

    assert json.loads(raw) == VALID_ARGS
    assert provider.last_model_used == config.OPENAI_MODEL


def test_missing_api_key_raises_ai_unavailable(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    provider = OpenAIProvider()

    with pytest.raises(AIUnavailableError):
        provider.route_ticket("some ticket text")


def test_any_call_failure_raises_ai_unavailable():
    mock_create = MagicMock(side_effect=RuntimeError("rate limited"))
    provider = _provider_with_mock_client(mock_create)

    with pytest.raises(AIUnavailableError):
        provider.route_ticket("some ticket text")


def test_no_tool_call_raises_ai_unavailable():
    mock_create = MagicMock(return_value=_fake_response_without_tool_call())
    provider = _provider_with_mock_client(mock_create)

    with pytest.raises(AIUnavailableError):
        provider.route_ticket("some ticket text")
