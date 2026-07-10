import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ticket_router.ai.combined_provider import CombinedProvider
from ticket_router.config import config

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


@pytest.fixture(autouse=True)
def _fake_api_keys(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-groq-key")
    yield


def _mock_client(mock_create):
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mock_create)))


def test_uses_openai_first_when_it_succeeds():
    openai_create = MagicMock(return_value=_fake_response(VALID_ARGS))
    provider = CombinedProvider()
    provider._openai._client = _mock_client(openai_create)
    groq_create = MagicMock(return_value=_fake_response(VALID_ARGS))
    provider._groq._client = _mock_client(groq_create)

    raw = provider.route_ticket("some ticket text")

    assert json.loads(raw) == VALID_ARGS
    assert groq_create.call_count == 0
    assert provider.last_model_used == f"openai/{config.OPENAI_MODEL}"


def test_falls_back_to_groq_when_openai_key_is_missing(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    provider = CombinedProvider()
    groq_create = MagicMock(return_value=_fake_response(VALID_ARGS))
    provider._groq._client = _mock_client(groq_create)

    raw = provider.route_ticket("some ticket text")

    assert json.loads(raw) == VALID_ARGS
    assert groq_create.call_count == 1
    assert provider.last_model_used == config.GROQ_MODEL


def test_falls_back_to_groq_when_openai_call_fails():
    openai_create = MagicMock(side_effect=RuntimeError("service unavailable"))
    provider = CombinedProvider()
    provider._openai._client = _mock_client(openai_create)
    groq_create = MagicMock(return_value=_fake_response(VALID_ARGS))
    provider._groq._client = _mock_client(groq_create)

    raw = provider.route_ticket("some ticket text")

    assert json.loads(raw) == VALID_ARGS
    assert openai_create.call_count == 1
    assert groq_create.call_count == 1
    assert provider.last_model_used == config.GROQ_MODEL
