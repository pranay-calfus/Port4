from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ticket_router.config import config
from ticket_router.services import resolution_service


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")
    yield


def _fake_response(resolved: bool, reasoning: str = "test reasoning") -> SimpleNamespace:
    return SimpleNamespace(
        tool_calls=[
            {
                "name": "check_resolution",
                "args": {"resolved": resolved, "reasoning": reasoning},
                "id": "1",
            }
        ]
    )


def _patch_llm(monkeypatch, mock_invoke):
    monkeypatch.setattr(
        resolution_service,
        "_build_llm",
        lambda: SimpleNamespace(invoke=mock_invoke),
    )


def test_returns_resolved_true_when_customer_confirms(monkeypatch):
    _patch_llm(monkeypatch, MagicMock(return_value=_fake_response(True, "customer said thanks")))

    result = resolution_service.check_resolution("transcript", "That fixed it, thanks!")

    assert result.resolved is True
    assert result.reasoning == "customer said thanks"


def test_returns_resolved_false_by_default(monkeypatch):
    _patch_llm(
        monkeypatch, MagicMock(return_value=_fake_response(False, "just a follow-up question"))
    )

    result = resolution_service.check_resolution("transcript", "Any update?")

    assert result.resolved is False


def test_missing_api_key_returns_resolved_false_without_calling_llm(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    build_llm = MagicMock()
    monkeypatch.setattr(resolution_service, "_build_llm", build_llm)

    result = resolution_service.check_resolution("transcript", "Thanks, all set!")

    assert result.resolved is False
    build_llm.assert_not_called()


def test_llm_failure_degrades_to_resolved_false(monkeypatch):
    _patch_llm(monkeypatch, MagicMock(side_effect=RuntimeError("rate limited")))

    result = resolution_service.check_resolution("transcript", "Thanks, all set!")

    assert result.resolved is False


def test_no_tool_call_degrades_to_resolved_false(monkeypatch):
    _patch_llm(monkeypatch, MagicMock(return_value=SimpleNamespace(tool_calls=[])))

    result = resolution_service.check_resolution("transcript", "Thanks, all set!")

    assert result.resolved is False


def test_invalid_tool_args_degrade_to_resolved_false(monkeypatch):
    response = SimpleNamespace(
        tool_calls=[{"name": "check_resolution", "args": {"resolved": "not-a-bool"}, "id": "1"}]
    )
    _patch_llm(monkeypatch, MagicMock(return_value=response))

    result = resolution_service.check_resolution("transcript", "Thanks, all set!")

    assert result.resolved is False
