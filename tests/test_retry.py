import json

import pytest
from pydantic import ValidationError

from tests.fixtures.mock_ai_responses import (
    CODE_FENCED_JSON,
    MALFORMED_CONFIDENCE_OUT_OF_RANGE,
    MALFORMED_INVALID_CATEGORY,
    PROSE_WRAPPED_JSON,
    TRAILING_COMMA_JSON,
    VALID_RESPONSES,
)
from ticket_router.errors import AIResponseError, AIUnavailableError
from ticket_router.models import TicketRequest
from ticket_router.services.json_repair import (
    extract_first_json_object,
    fix_trailing_commas,
    repair_and_parse,
    strip_code_fences,
)
from ticket_router.services.ticket_routing_service import route_ticket


class FakeProvider:
    """Test double for AIProvider - returns pre-scripted raw JSON strings
    instead of making real network calls.
    """

    def __init__(self, responses: list) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str | None]] = []

    def route_ticket(self, message: str, retry_context: str | None = None) -> str:
        self.calls.append((message, retry_context))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response if isinstance(response, str) else json.dumps(response)


def test_1_rejects_empty_input_at_the_validation_layer_without_calling_the_ai():
    with pytest.raises(ValidationError):
        TicketRequest(message="")
    with pytest.raises(ValidationError):
        TicketRequest(message="   ")


def test_2_repairs_a_markdown_code_fenced_json_string():
    parsed = repair_and_parse(CODE_FENCED_JSON)
    assert parsed["category"] == "Billing"


def test_3_repairs_a_json_string_with_a_trailing_comma():
    parsed = repair_and_parse(TRAILING_COMMA_JSON)
    assert parsed["category"] == "Billing"


def test_4_extracts_a_json_object_wrapped_in_prose():
    parsed = repair_and_parse(PROSE_WRAPPED_JSON)
    assert parsed["category"] == "Billing"


def test_4b_repair_helper_functions_behave_correctly_in_isolation():
    assert strip_code_fences('```json\n{"a":1}\n```') == '{"a":1}'
    assert fix_trailing_commas('{"a":1,}') == '{"a":1}'
    assert extract_first_json_object('prefix {"a":1} suffix') == '{"a":1}'


def test_5_retries_once_and_succeeds_when_the_second_ai_call_returns_a_valid_response():
    provider = FakeProvider([MALFORMED_INVALID_CATEGORY, VALID_RESPONSES[0]])

    result = route_ticket("some ticket text", provider)

    assert result.category == "Billing"
    assert len(provider.calls) == 2
    assert provider.calls[1][1] is not None  # retry_context was passed


def test_6_raises_ai_response_error_when_both_attempts_return_invalid_data():
    provider = FakeProvider([MALFORMED_INVALID_CATEGORY, MALFORMED_CONFIDENCE_OUT_OF_RANGE])

    with pytest.raises(AIResponseError):
        route_ticket("some ticket text", provider)

    assert len(provider.calls) == 2


def test_7_surfaces_ai_unavailable_error_when_the_provider_itself_fails():
    provider = FakeProvider([AIUnavailableError("AI service unavailable: missing API key")])

    with pytest.raises(AIUnavailableError):
        route_ticket("some ticket text", provider)


def test_8_succeeds_on_the_first_attempt_without_retrying_when_the_response_is_already_valid():
    provider = FakeProvider([VALID_RESPONSES[1]])

    result = route_ticket("some ticket text", provider)

    assert result.category == "Technical Support"
    assert len(provider.calls) == 1
