"""Integration tests for the feedback AI pipeline that hit the *real*
OpenAI API - unlike tests/test_tool_classifier.py and
tests/backend/test_feedback.py, which script every model response through
a fake ChatOpenAI/monkeypatched function, the tests below call
ticket_router.services.feedback_classification_service.classify_feedback()
end to end: the real system prompt, the real forced tool-call schema, and
a real network round trip.

These are opt-in, not part of the default `pytest` run:
    - They cost real tokens and take real network time (seconds, not
      milliseconds), which would make the everyday test suite slow/flaky/
      billed.
    - They require a real OPENAI_API_KEY (the mocked suite deliberately
      works with a fake "test-key" - see every other test file's
      `_fake_api_key` fixture).

Run them explicitly once you have a real OPENAI_API_KEY configured:
    RUN_LIVE_LLM_TESTS=1 pytest tests/integration -q

Every other assertion in this file is deliberately loose on free-text
fields (summary/reasoning wording) - LLM output for those is inherently
non-identical run to run. What's asserted is the *structural* contract
(the response always validates against FeedbackClassification, i.e.
forced-JSON-schema enforcement actually holds against the real API) and,
for the unambiguous examples below, the *specific* enum fields a person
reading the same review would also pick - proving the prompt/few-shot
design generalizes past its own worked examples, not just the schema.
"""

import os
from types import SimpleNamespace

import pytest

from ticket_router.ai import tool_classifier as tool_classifier_module
from ticket_router.config import config
from ticket_router.models import (
    ASSIGNED_TEAMS,
    FEEDBACK_CATEGORIES,
    FEEDBACK_SENTIMENTS,
    FeedbackClassification,
)
from ticket_router.prompts import (
    FEEDBACK_CLASSIFICATION_SYSTEM_PROMPT,
    FEEDBACK_FEW_SHOT_EXAMPLES,
)
from ticket_router.services.feedback_classification_service import classify_feedback

_RUN_LIVE = os.getenv("RUN_LIVE_LLM_TESTS") == "1"
_HAS_REAL_KEY = bool(config.OPENAI_API_KEY)

_SKIP_REASON = (
    "Live LLM tests are opt-in: set RUN_LIVE_LLM_TESTS=1 with a real "
    "OPENAI_API_KEY configured to run them (see module docstring)."
)


def _assert_schema_valid(result: FeedbackClassification) -> None:
    """The structural contract every live call must satisfy, regardless of
    which specific labels the model picked - i.e. that JSON-schema
    enforcement (the forced tool call + Pydantic validation in
    run_classifier) actually held against a real response.
    """
    assert isinstance(result, FeedbackClassification)
    assert result.sentiment in FEEDBACK_SENTIMENTS
    assert result.category in FEEDBACK_CATEGORIES
    assert result.team in ASSIGNED_TEAMS
    assert isinstance(result.theme, str) and result.theme.strip() != ""
    assert isinstance(result.summary, str) and result.summary.strip() != ""
    assert isinstance(result.reasoning, str) and result.reasoning.strip() != ""
    assert 0.0 <= result.confidence <= 1.0


def _assert_not_the_failure_fallback(result: FeedbackClassification) -> None:
    """classify_feedback() never raises - it degrades to a fixed
    (Neutral/Other/Customer Success, confidence 0.0) default on any AI
    failure (see its docstring). A live test whose whole point is
    exercising the real API should fail loudly if that's what actually
    happened, rather than silently asserting against the fallback values.
    """
    assert result.confidence > 0.0, (
        "classify_feedback() returned the fail-soft default (confidence=0.0) - "
        "the real API call failed instead of being exercised. Check "
        "OPENAI_API_KEY / network access."
    )


class TestFeedbackPromptDesign:
    """Fast, deterministic, no network - the prompt/few-shot design is
    static data, so these run every time (not gated behind RUN_LIVE_LLM_TESTS)
    and catch a broken prompt/schema wiring before any live test would.
    """

    def test_prompt_documents_every_category_and_sentiment(self):
        for category in FEEDBACK_CATEGORIES:
            assert category in FEEDBACK_CLASSIFICATION_SYSTEM_PROMPT
        for sentiment in FEEDBACK_SENTIMENTS:
            assert sentiment in FEEDBACK_CLASSIFICATION_SYSTEM_PROMPT

    def test_prompt_declares_the_forced_tool_output_contract(self):
        assert '"classify_feedback"' in FEEDBACK_CLASSIFICATION_SYSTEM_PROMPT
        assert "OUTPUT CONTRACT" in FEEDBACK_CLASSIFICATION_SYSTEM_PROMPT
        assert "NEVER wrap your output in markdown code fences" in FEEDBACK_CLASSIFICATION_SYSTEM_PROMPT

    def test_every_few_shot_example_is_embedded_in_the_prompt_verbatim(self):
        # Proves the examples aren't just defined in Python but actually
        # reach the model - a stale/disconnected example list would fail
        # this without needing a live call.
        assert len(FEEDBACK_FEW_SHOT_EXAMPLES) >= 5
        for example in FEEDBACK_FEW_SHOT_EXAMPLES:
            assert example.feedback in FEEDBACK_CLASSIFICATION_SYSTEM_PROMPT
            assert example.theme in FEEDBACK_CLASSIFICATION_SYSTEM_PROMPT

    def test_few_shot_examples_cover_every_sentiment_and_most_categories(self):
        # The mentor-facing bar (see M5S3 in the mission) is "deliberate,
        # explainable choices" - a concrete floor for that is covering the
        # full sentiment range and a good spread of categories, not just
        # one clear-cut Positive/General-Praise example repeated.
        covered_sentiments = {e.sentiment for e in FEEDBACK_FEW_SHOT_EXAMPLES}
        covered_categories = {e.category for e in FEEDBACK_FEW_SHOT_EXAMPLES}
        assert covered_sentiments == set(FEEDBACK_SENTIMENTS)
        assert len(covered_categories) >= 5


@pytest.mark.live_llm
@pytest.mark.skipif(not (_RUN_LIVE and _HAS_REAL_KEY), reason=_SKIP_REASON)
class TestFeedbackClassifierLive:
    """Calls the real classifier end to end. Grouped as one class so the
    skip condition (and the reason) is defined exactly once.
    """

    # --- schema enforcement + category/sentiment/theme/summary correctness ---

    @pytest.mark.parametrize(
        "text,expected_category,expected_sentiment",
        [
            (
                "Your subscription price is way too expensive compared to every "
                "other tool we've tried this year.",
                "Pricing",
                "Negative",
            ),
            (
                "I love how clean and intuitive the new interface looks after "
                "the redesign, navigation is so much easier now.",
                "UI/UX",
                "Positive",
            ),
            (
                "It would be great if you could add support for exporting "
                "reports directly to PDF someday.",
                "Feature Request",
                "Neutral",
            ),
            (
                "The support rep I chatted with yesterday resolved my issue in "
                "minutes and was incredibly kind about it.",
                "Customer Support Experience",
                "Positive",
            ),
            (
                "Pages take forever to load, especially the reports section - "
                "it's really frustrating to use day to day.",
                "Performance",
                "Negative",
            ),
        ],
    )
    def test_classifies_unambiguous_reviews_correctly(self, text, expected_category, expected_sentiment):
        result = classify_feedback(text)

        _assert_schema_valid(result)
        _assert_not_the_failure_fallback(result)
        assert result.category == expected_category
        assert result.sentiment == expected_sentiment
        assert result.confidence >= 0.5

    # --- determinism (M5S2: same input twice -> same score) ---

    def test_classifying_the_same_input_twice_yields_identical_structured_fields(self):
        text = (
            "The mobile app constantly crashes whenever I try to upload a "
            "photo to my profile, it's happened at least five times this week."
        )

        first = classify_feedback(text)
        second = classify_feedback(text)

        _assert_not_the_failure_fallback(first)
        _assert_not_the_failure_fallback(second)
        assert first.category == second.category
        assert first.sentiment == second.sentiment
        assert first.theme == second.theme
        assert first.confidence == second.confidence

    # --- retry/repair logic, exercised against the real API on the retry ---

    def test_recovers_via_the_real_api_after_a_simulated_invalid_first_response(self, monkeypatch):
        """Forces run_classifier's validation-failure retry path (see
        ticket_router/ai/tool_classifier.py) deterministically - the first
        model response is swapped for a scripted, schema-invalid one (missing
        every required field but `sentiment`) - while the retry attempt is
        left untouched, so it's a real network call. This proves the retry
        path is correctly wired to the real client, which the fully-mocked
        tests/test_tool_classifier.py can't prove on its own (there, both
        attempts are fake).
        """
        real_invoke = tool_classifier_module._invoke
        call_count = {"n": 0}

        def flaky_invoke(model, system_prompt, tool, tool_name, content, max_tokens):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return SimpleNamespace(
                    tool_calls=[{"name": tool_name, "args": {"sentiment": "Positive"}, "id": "1"}]
                )
            return real_invoke(model, system_prompt, tool, tool_name, content, max_tokens)

        monkeypatch.setattr(tool_classifier_module, "_invoke", flaky_invoke)

        result = classify_feedback(
            "The onboarding flow was smooth and I was up and running in minutes."
        )

        assert call_count["n"] == 2, "expected exactly one retry against the real API"
        _assert_schema_valid(result)
        _assert_not_the_failure_fallback(result)

    # --- edge cases ---

    def test_very_short_input_still_produces_a_valid_classification(self):
        result = classify_feedback("Bad.")

        _assert_schema_valid(result)
        # Prompt's CONFIDENCE RULES call for lower confidence on very short,
        # low-detail input - a real invalid/never-happens case would be no
        # different in kind to any other low-signal message, so this is a
        # loose sanity bound, not an exact expected value.
        assert result.confidence <= 0.9

    def test_long_review_is_truncated_but_still_classified(self):
        # Comfortably over MAX_TICKET_LENGTH (8000 chars, see
        # ticket_router/models.py) - proves truncate_message's cut doesn't
        # break the request or the response's schema validity.
        paragraph = (
            "The platform has been mostly reliable but there are a few "
            "recurring pain points worth mentioning in detail. "
        )
        text = paragraph * 200
        assert len(text) > 8000

        result = classify_feedback(text)

        _assert_schema_valid(result)
        _assert_not_the_failure_fallback(result)

    def test_mixed_sentiment_input_still_picks_one_valid_sentiment(self):
        text = (
            "I really love the new dashboard design, but the app has been "
            "crashing constantly since the last update and it's frustrating."
        )

        result = classify_feedback(text)

        _assert_schema_valid(result)
        _assert_not_the_failure_fallback(result)

    def test_blank_input_never_raises(self):
        # classify_feedback() has no upfront blank-input guard of its own
        # (unlike TicketRequest's Pydantic validator at the API boundary) -
        # it either gets a real (if low-signal) response from the API, or
        # any AI-side failure degrades to the documented fail-soft default.
        # Either way, the important guarantee under test is "never raises".
        result = classify_feedback("")

        _assert_schema_valid(result)

    def test_spam_like_input_still_produces_a_valid_classification(self):
        text = "BUY NOW!!! CLICK HERE http://example-spam.test FREE MONEY !!! LIMITED TIME"

        result = classify_feedback(text)

        # No category is designed to model "spam" - the taxonomy's "Other"
        # exists exactly for input that doesn't genuinely fit anywhere else
        # (see FEEDBACK_CATEGORY_DEFINITIONS). What matters is that garbage
        # input still comes back schema-valid instead of erroring.
        _assert_schema_valid(result)

    def test_emoji_and_special_characters_still_produce_a_valid_classification(self):
        text = "This app is 🔥🔥🔥 amazing!! 😍 but it sometimes crashes 💀... ¯\\_(ツ)_/¯"

        result = classify_feedback(text)

        _assert_schema_valid(result)
        _assert_not_the_failure_fallback(result)
