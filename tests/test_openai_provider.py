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


class _AuthError(Exception):
    status_code = 401


def _fake_response(arguments: dict) -> SimpleNamespace:
    return SimpleNamespace(tool_calls=[{"name": "route_ticket", "args": arguments, "id": "1"}])


def _fake_response_without_tool_call() -> SimpleNamespace:
    return SimpleNamespace(tool_calls=[])


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")
    yield


def _provider_with_mock_invoke(mock_invoke):
    """Replaces _get_llm so every model in the chain resolves to a fake
    llm sharing the same `invoke` mock, letting tests drive per-attempt
    behavior via `side_effect` without touching real ChatOpenAI clients.
    """
    provider = OpenAIProvider()
    provider._get_llm = MagicMock(return_value=SimpleNamespace(invoke=mock_invoke))
    return provider


def test_succeeds_and_records_the_model_used():
    mock_invoke = MagicMock(return_value=_fake_response(VALID_ARGS))
    provider = _provider_with_mock_invoke(mock_invoke)

    raw = provider.route_ticket("some ticket text")

    assert json.loads(raw) == VALID_ARGS
    assert provider.last_model_used == config.OPENAI_MODEL


def test_missing_api_key_raises_ai_unavailable(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    provider = OpenAIProvider()

    with pytest.raises(AIUnavailableError):
        provider.route_ticket("some ticket text")


def test_succeeds_on_the_configured_primary_model_without_falling_back():
    mock_invoke = MagicMock(return_value=_fake_response(VALID_ARGS))
    provider = _provider_with_mock_invoke(mock_invoke)

    raw = provider.route_ticket("some ticket text")

    assert json.loads(raw) == VALID_ARGS
    assert mock_invoke.call_count == 1
    get_llm_calls = [c.args[0] for c in provider._get_llm.call_args_list if c.args]
    assert get_llm_calls[-1] == config.OPENAI_MODEL


def test_falls_back_to_second_model_when_first_raises():
    mock_invoke = MagicMock(side_effect=[RuntimeError("rate limited"), _fake_response(VALID_ARGS)])
    provider = _provider_with_mock_invoke(mock_invoke)

    raw = provider.route_ticket("some ticket text")

    assert json.loads(raw) == VALID_ARGS
    assert mock_invoke.call_count == 2
    # the second attempt should use a different model than the first
    get_llm_calls = [c.args[0] for c in provider._get_llm.call_args_list if c.args]
    first_model = get_llm_calls[-2]
    second_model = get_llm_calls[-1]
    assert first_model != second_model


def test_falls_back_when_a_model_returns_no_tool_call():
    mock_invoke = MagicMock(
        side_effect=[_fake_response_without_tool_call(), _fake_response(VALID_ARGS)]
    )
    provider = _provider_with_mock_invoke(mock_invoke)

    raw = provider.route_ticket("some ticket text")

    assert json.loads(raw) == VALID_ARGS
    assert mock_invoke.call_count == 2


def test_raises_ai_unavailable_when_every_model_in_the_chain_fails():
    mock_invoke = MagicMock(side_effect=RuntimeError("service down"))
    provider = _provider_with_mock_invoke(mock_invoke)

    with pytest.raises(AIUnavailableError) as exc_info:
        provider.route_ticket("some ticket text")

    assert mock_invoke.call_count >= 2
    assert "attemptedModels" in exc_info.value.details


def test_authentication_error_fails_fast_without_trying_other_models():
    mock_invoke = MagicMock(side_effect=_AuthError("invalid api key"))
    provider = _provider_with_mock_invoke(mock_invoke)

    with pytest.raises(AIUnavailableError):
        provider.route_ticket("some ticket text")

    assert mock_invoke.call_count == 1
