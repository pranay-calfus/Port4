from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ticket_router.config import config
from ticket_router.errors import AIResponseError, AIUnavailableError
from ticket_router.services import weekly_summary_service

_METRICS = {
    "period": {"from": "2026-07-13", "to": "2026-07-19"},
    "total_feedback": 3,
    "sentiment_breakdown": {
        "Positive": {"count": 1, "pct": 33.3},
        "Neutral": {"count": 0, "pct": 0.0},
        "Negative": {"count": 2, "pct": 66.7},
    },
    "category_breakdown": {"Pricing": 2, "General Praise": 1},
    "team_breakdown": {"Sales Team": 2, "Customer Success": 1},
    "top_themes": [{"theme": "Pricing Feedback", "count": 2}],
    "theme_excerpts": {"Pricing Feedback": ["Your pricing feels a bit high."]},
}

_VALID_ARGS = {
    "overview": "3 pieces of feedback this week, mostly negative and centered on pricing.",
    "overall_sentiment": "Negative (66.7%), driven by pricing complaints.",
    "key_insights": ["The 'Pricing Feedback' theme accounts for 2 of 3 items this week."],
    "risks": ["Repeated pricing complaints could signal churn risk."],
    "recommendations": ["Have Sales Team review competitor pricing given the 'Pricing Feedback' theme."],
    "positive_highlights": [],
}


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(config, "OPENAI_FALLBACK_MODELS", "")
    yield


def _fake_response(args: dict) -> SimpleNamespace:
    return SimpleNamespace(
        tool_calls=[{"name": "generate_weekly_summary", "args": args, "id": "1"}]
    )


def _patch_chat_openai(monkeypatch, mock_invoke) -> None:
    class _FakeChatOpenAI:
        def __init__(self, **kwargs) -> None:
            pass

        def bind_tools(self, tools, tool_choice):  # noqa: ARG002
            return SimpleNamespace(invoke=mock_invoke)

    monkeypatch.setattr("ticket_router.ai.tool_classifier.ChatOpenAI", _FakeChatOpenAI)


def test_generates_narrative_from_metrics(monkeypatch):
    mock_invoke = MagicMock(return_value=_fake_response(_VALID_ARGS))
    _patch_chat_openai(monkeypatch, mock_invoke)

    result = weekly_summary_service.generate_weekly_narrative(_METRICS)

    assert result.overview == _VALID_ARGS["overview"]
    assert result.key_insights == _VALID_ARGS["key_insights"]
    assert result.risks == _VALID_ARGS["risks"]
    assert result.positive_highlights == []
    assert result.model_used == config.OPENAI_MODEL


def test_same_metrics_twice_produce_identical_output(monkeypatch):
    """Sentiment/theme numbers are deterministic Python aggregation, not
    AI-derived - but the narrative itself should also be stable for
    identical input, same as every other classifier in this app
    (temperature=0 via run_classifier)."""
    mock_invoke = MagicMock(return_value=_fake_response(_VALID_ARGS))
    _patch_chat_openai(monkeypatch, mock_invoke)

    first = weekly_summary_service.generate_weekly_narrative(_METRICS)
    second = weekly_summary_service.generate_weekly_narrative(_METRICS)

    assert first.model_dump() == second.model_dump()


def test_missing_api_key_raises_ai_unavailable(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")

    with pytest.raises(AIUnavailableError):
        weekly_summary_service.generate_weekly_narrative(_METRICS)


def test_invalid_response_raises_ai_response_error_after_retries(monkeypatch):
    invalid_args = {**_VALID_ARGS, "overview": ""}
    mock_invoke = MagicMock(return_value=_fake_response(invalid_args))
    _patch_chat_openai(monkeypatch, mock_invoke)

    with pytest.raises(AIResponseError):
        weekly_summary_service.generate_weekly_narrative(_METRICS)
