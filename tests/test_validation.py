import pytest
from pydantic import ValidationError

from tests.fixtures.mock_ai_responses import (
    MALFORMED_CONFIDENCE_AS_STRING,
    MALFORMED_CONFIDENCE_OUT_OF_RANGE,
    MALFORMED_INVALID_CATEGORY,
    MALFORMED_INVALID_EMOTION,
    MALFORMED_MISSING_FIELD,
    VALID_RESPONSES,
)
from ticket_router.models import TicketRouteResult

# 10 consecutive JSON validation tests, per the mission's reliability
# requirement: every response must be parseable, and every required field
# must be present.


def test_1_validates_billing_response_with_all_required_fields():
    result = TicketRouteResult.model_validate(VALID_RESPONSES[0])
    assert result.category == "Billing"
    dumped = result.model_dump(by_alias=True)
    assert set(dumped) == {
        "category",
        "priority",
        "assignedTeam",
        "emotion",
        "theme",
        "summary",
        "reasoning",
        "confidence",
    }


def test_2_validates_technical_support_response():
    result = TicketRouteResult.model_validate(VALID_RESPONSES[1])
    assert result.category == "Technical Support"


def test_3_validates_security_response_with_high_priority():
    result = TicketRouteResult.model_validate(VALID_RESPONSES[2])
    assert result.priority == "High"


def test_4_validates_feature_request_response_with_low_priority():
    result = TicketRouteResult.model_validate(VALID_RESPONSES[3])
    assert result.priority == "Low"


def test_5_rejects_response_missing_reasoning_field():
    with pytest.raises(ValidationError) as exc_info:
        TicketRouteResult.model_validate(MALFORMED_MISSING_FIELD)
    assert any(err["loc"] == ("reasoning",) for err in exc_info.value.errors())


def test_6_rejects_response_with_invalid_category_enum_value():
    with pytest.raises(ValidationError):
        TicketRouteResult.model_validate(MALFORMED_INVALID_CATEGORY)


def test_7_rejects_response_with_confidence_out_of_range():
    with pytest.raises(ValidationError):
        TicketRouteResult.model_validate(MALFORMED_CONFIDENCE_OUT_OF_RANGE)


def test_8_rejects_response_with_confidence_as_string_type_coercion_disallowed():
    # Pydantic v2's default (non-strict) mode coerces numeric strings, so we
    # validate in strict mode here to enforce the same "confidence must be a
    # real number" contract the mission calls for.
    with pytest.raises(ValidationError):
        TicketRouteResult.model_validate(MALFORMED_CONFIDENCE_AS_STRING, strict=True)


def test_9_ignores_unexpected_extra_fields_but_still_validates_known_good_data():
    payload = {**VALID_RESPONSES[4], "extraField": "ignore me"}
    result = TicketRouteResult.model_validate(payload)
    assert not hasattr(result, "extraField")


def test_rejects_response_with_invalid_emotion_enum_value():
    with pytest.raises(ValidationError):
        TicketRouteResult.model_validate(MALFORMED_INVALID_EMOTION)


def test_10_validates_all_remaining_sample_ai_responses_with_no_missing_fields():
    for response in VALID_RESPONSES[4:]:
        result = TicketRouteResult.model_validate(response)
        assert result.reasoning
        assert 0 <= result.confidence <= 1
