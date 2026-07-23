from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field

from ticket_router.ai.tool_classifier import run_classifier
from ticket_router.config import config
from ticket_router.errors import AIResponseError, AIUnavailableError

TOOL = {"type": "function", "function": {"name": "test_tool", "parameters": {}}}
TOOL_NAME = "test_tool"


class _Result(BaseModel):
    value: str = Field(min_length=1)
    model_used: str | None = None


class _AuthError(Exception):
    status_code = 401


def _fake_response(args: dict) -> SimpleNamespace:
    return SimpleNamespace(tool_calls=[{"name": TOOL_NAME, "args": args, "id": "1"}])


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")
    # Fallback is opt-in - default to none configured so tests are
    # deterministic regardless of the developer's local .env.
    monkeypatch.setattr(config, "OPENAI_FALLBACK_MODELS", "")
    yield


def _patch_chat_openai(monkeypatch, mock_invoke) -> None:
    class _FakeChatOpenAI:
        def __init__(self, **kwargs) -> None:
            pass

        def bind_tools(self, tools, tool_choice):  # noqa: ARG002
            return SimpleNamespace(invoke=mock_invoke)

    monkeypatch.setattr("ticket_router.ai.tool_classifier.ChatOpenAI", _FakeChatOpenAI)


def _run(result_model=_Result):
    return run_classifier(
        system_prompt="sys", message="hello", tool=TOOL, tool_name=TOOL_NAME, result_model=result_model
    )


def test_succeeds_on_first_attempt_and_records_model_used(monkeypatch):
    mock_invoke = MagicMock(return_value=_fake_response({"value": "ok"}))
    _patch_chat_openai(monkeypatch, mock_invoke)

    result = _run()

    assert result.value == "ok"
    assert result.model_used == config.OPENAI_MODEL
    assert mock_invoke.call_count == 1


def test_falls_back_to_second_model_on_failure(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_FALLBACK_MODELS", "gpt-4o")
    mock_invoke = MagicMock(side_effect=[RuntimeError("rate limited"), _fake_response({"value": "ok"})])
    _patch_chat_openai(monkeypatch, mock_invoke)

    result = _run()

    assert result.value == "ok"
    assert mock_invoke.call_count == 2


def test_falls_back_when_a_model_returns_no_tool_call(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_FALLBACK_MODELS", "gpt-4o")
    mock_invoke = MagicMock(
        side_effect=[SimpleNamespace(tool_calls=[]), _fake_response({"value": "ok"})]
    )
    _patch_chat_openai(monkeypatch, mock_invoke)

    result = _run()

    assert result.value == "ok"
    assert mock_invoke.call_count == 2


def test_retries_once_on_invalid_response_and_succeeds(monkeypatch):
    mock_invoke = MagicMock(
        side_effect=[_fake_response({"value": ""}), _fake_response({"value": "ok"})]
    )
    _patch_chat_openai(monkeypatch, mock_invoke)

    result = _run()

    assert result.value == "ok"
    assert mock_invoke.call_count == 2


def test_raises_ai_response_error_when_both_attempts_are_invalid(monkeypatch):
    mock_invoke = MagicMock(return_value=_fake_response({"value": ""}))
    _patch_chat_openai(monkeypatch, mock_invoke)

    with pytest.raises(AIResponseError):
        _run()


def test_raises_ai_unavailable_when_every_model_fails(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_FALLBACK_MODELS", "gpt-4o")
    mock_invoke = MagicMock(side_effect=RuntimeError("service down"))
    _patch_chat_openai(monkeypatch, mock_invoke)

    with pytest.raises(AIUnavailableError) as exc_info:
        _run()

    assert mock_invoke.call_count == 2
    assert exc_info.value.details["attemptedModels"] == [config.OPENAI_MODEL, "gpt-4o"]


def test_authentication_error_fails_fast_without_trying_other_models(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_FALLBACK_MODELS", "gpt-4o,gpt-3.5-turbo")
    mock_invoke = MagicMock(side_effect=_AuthError("invalid api key"))
    _patch_chat_openai(monkeypatch, mock_invoke)

    with pytest.raises(AIUnavailableError):
        _run()

    assert mock_invoke.call_count == 1


def test_missing_api_key_raises_ai_unavailable(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")

    with pytest.raises(AIUnavailableError):
        _run()


def test_model_used_is_left_alone_when_result_model_lacks_the_field(monkeypatch):
    class _NoModelUsedResult(BaseModel):
        value: str

    mock_invoke = MagicMock(return_value=_fake_response({"value": "ok"}))
    _patch_chat_openai(monkeypatch, mock_invoke)

    result = _run(result_model=_NoModelUsedResult)

    assert result.value == "ok"
    assert not hasattr(result, "model_used")
