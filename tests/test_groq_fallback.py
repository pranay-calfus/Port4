import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import openai
import pytest

from ticket_router.ai.groq_provider import GroqProvider
from ticket_router.config import config
from ticket_router.errors import AIUnavailableError


def _fake_response(arguments: dict) -> SimpleNamespace:
    tool_call = SimpleNamespace(function=SimpleNamespace(arguments=json.dumps(arguments)))
    message = SimpleNamespace(tool_calls=[tool_call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _fake_response_without_tool_call() -> SimpleNamespace:
    message = SimpleNamespace(tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


VALID_ARGS = {
    "category": "Billing",
    "priority": "Medium",
    "assignedTeam": "Billing Team",
    "reasoning": "Some reason.",
    "confidence": 0.9,
}


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    yield


def _provider_with_mock_client(mock_create):
    provider = GroqProvider()
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=mock_create))
    )
    return provider


def test_falls_back_to_second_model_when_first_raises():
    mock_create = MagicMock(side_effect=[RuntimeError("rate limited"), _fake_response(VALID_ARGS)])
    provider = _provider_with_mock_client(mock_create)

    raw = provider.route_ticket("some ticket text")

    assert json.loads(raw) == VALID_ARGS
    assert mock_create.call_count == 2
    # the second attempt should use a different model than the first
    first_model = mock_create.call_args_list[0].kwargs["model"]
    second_model = mock_create.call_args_list[1].kwargs["model"]
    assert first_model != second_model


def test_falls_back_when_a_model_returns_no_tool_call():
    mock_create = MagicMock(
        side_effect=[_fake_response_without_tool_call(), _fake_response(VALID_ARGS)]
    )
    provider = _provider_with_mock_client(mock_create)

    raw = provider.route_ticket("some ticket text")

    assert json.loads(raw) == VALID_ARGS
    assert mock_create.call_count == 2


def test_raises_ai_unavailable_when_every_model_in_the_chain_fails():
    mock_create = MagicMock(side_effect=RuntimeError("service down"))
    provider = _provider_with_mock_client(mock_create)

    with pytest.raises(AIUnavailableError) as exc_info:
        provider.route_ticket("some ticket text")

    assert mock_create.call_count >= 2
    assert "attemptedModels" in exc_info.value.details


def test_authentication_error_fails_fast_without_trying_other_models():
    auth_error = openai.AuthenticationError(
        "invalid api key",
        response=httpx.Response(401, request=httpx.Request("POST", "https://api.groq.com")),
        body=None,
    )
    mock_create = MagicMock(side_effect=auth_error)
    provider = _provider_with_mock_client(mock_create)

    with pytest.raises(AIUnavailableError):
        provider.route_ticket("some ticket text")

    assert mock_create.call_count == 1


def test_succeeds_on_the_configured_primary_model_without_falling_back():
    mock_create = MagicMock(return_value=_fake_response(VALID_ARGS))
    provider = _provider_with_mock_client(mock_create)

    raw = provider.route_ticket("some ticket text")

    assert json.loads(raw) == VALID_ARGS
    assert mock_create.call_count == 1
    assert mock_create.call_args.kwargs["model"] == config.GROQ_MODEL
