"""The shared reliability engine behind every AI classification capability
in this app except ticket routing (see the module note below for why).
`run_classifier()` generalizes the exact pattern `OpenAIProvider.route_ticket()`
already implements: truncate the input, try each model in `build_model_chain()`
in order (forced tool call, skip to the next model on a retryable failure),
parse+repair+validate the JSON into a Pydantic model, and on a validation
failure retry the same model chain once more with the error appended as
context before giving up.

Adding a new AI capability (a sixth classifier down the line) means writing
a prompt + tool schema + Pydantic result model and calling `run_classifier`
- no change to this file, and no need to hand-roll the fallback/retry
pattern a third or fourth time.

Note: ticket_router.services.ticket_routing_service.route_ticket() and
ticket_router.ai.openai_provider.OpenAIProvider are deliberately left as
their own implementation rather than being rebuilt on top of this module -
they're the most heavily-tested part of the AI layer (see
tests/test_retry.py's FakeProvider injection and tests/test_openai_provider.py's
direct assertions on OpenAIProvider's internals) and already implement this
same pattern correctly. This module exists so feedback and submission-type
classification - which previously made a single single-model attempt with
no fallback - get the same reliability guarantees via one new shared piece,
without touching that well-tested code.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from ticket_router.ai.openai_provider import _is_non_retryable, build_model_chain
from ticket_router.config import config
from ticket_router.errors import AIResponseError, AIUnavailableError
from ticket_router.logger import logger
from ticket_router.services.json_repair import repair_and_parse
from ticket_router.services.prompt_service import summarize_validation_error, truncate_message


def _invoke(model: str, system_prompt: str, tool: dict, tool_name: str, content: str, max_tokens: int):
    llm = ChatOpenAI(
        api_key=config.OPENAI_API_KEY,
        model=model,
        max_tokens=max_tokens,
        temperature=0,
    ).bind_tools([tool], tool_choice=tool_name)
    return llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=content)])


def _call_with_fallback(
    system_prompt: str, tool: dict, tool_name: str, content: str, max_tokens: int
) -> tuple[str, str]:
    """Returns (raw_json_args, model_used). Raises AIUnavailableError if
    every model in build_model_chain() fails.
    """
    if not config.OPENAI_API_KEY:
        raise AIUnavailableError(
            "AI service unavailable: OPENAI_API_KEY is not configured. Set it in .env."
        )

    attempted: list[str] = []
    last_error: str | None = None

    for model in build_model_chain():
        attempted.append(model)
        try:
            response = _invoke(model, system_prompt, tool, tool_name, content, max_tokens)
        except Exception as error:  # noqa: BLE001 - evaluated below
            if _is_non_retryable(error):
                logger.error(
                    "OpenAI API call failed (non-retryable)",
                    {"model": model, "tool": tool_name, "error": str(error)},
                )
                raise AIUnavailableError(
                    "AI service is currently unavailable.",
                    {"cause": str(error), "model": model},
                ) from error
            last_error = str(error)
            logger.warning(
                "OpenAI model failed, falling back to next model",
                {"model": model, "tool": tool_name, "error": last_error},
            )
            continue

        tool_calls = response.tool_calls
        if not tool_calls:
            last_error = "response did not include a structured tool call"
            logger.warning(
                "OpenAI model returned no tool call, falling back to next model",
                {"model": model, "tool": tool_name},
            )
            continue

        if model != config.OPENAI_MODEL:
            logger.info(f"{tool_name} used a fallback model", {"model": model})
        return json.dumps(tool_calls[0]["args"]), model

    logger.error(
        "All OpenAI models failed", {"tool": tool_name, "attempted": attempted, "lastError": last_error}
    )
    raise AIUnavailableError(
        "AI service is currently unavailable across all configured models.",
        {"attemptedModels": attempted, "lastError": last_error},
    )


def _parse_and_validate(raw: str, result_model: type[BaseModel]) -> BaseModel:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = repair_and_parse(raw)
        if parsed is None:
            raise ValueError("response was not valid JSON, even after repair attempts") from None
    return result_model.model_validate(parsed)


def run_classifier(
    *,
    system_prompt: str,
    message: str,
    tool: dict,
    tool_name: str,
    result_model: type[BaseModel],
    max_tokens: int = 1024,
) -> BaseModel:
    """Runs the full JSON-reliability pipeline for one classification call:
    truncate the input, call `tool` across the fallback model chain, parse
    and validate the JSON into `result_model`; on validation failure, retry
    once more with the error appended as context. Raises
    AIUnavailableError/AIResponseError on persistent failure - callers that
    want a soft default instead of raising should catch AppError (see
    ticket_router.services.feedback_classification_service.classify_feedback
    for the pattern).

    Sets `model_used` on the result when that field exists on `result_model`
    (not every classifier result tracks it - e.g. SubmissionTypeResult
    doesn't).
    """
    text, truncated = truncate_message(message)
    if truncated:
        logger.warning(
            f"{tool_name} input truncated before sending to AI", {"original_length": len(message)}
        )

    raw, model_used = _call_with_fallback(system_prompt, tool, tool_name, text, max_tokens)
    try:
        result = _parse_and_validate(raw, result_model)
        if hasattr(result, "model_used"):
            result.model_used = model_used
        return result
    except (ValueError, PydanticValidationError) as first_error:
        error_summary = summarize_validation_error(first_error)
        logger.warning(
            f"{tool_name}: initial AI response failed validation, retrying once",
            {"error": error_summary},
        )

    retry_content = (
        f"{text}\n\n[SYSTEM NOTICE] Your previous response failed validation: "
        f"{error_summary}. Re-emit strictly valid arguments via the {tool_name} tool only."
    )
    raw2, model_used2 = _call_with_fallback(system_prompt, tool, tool_name, retry_content, max_tokens)
    try:
        result = _parse_and_validate(raw2, result_model)
        if hasattr(result, "model_used"):
            result.model_used = model_used2
        return result
    except (ValueError, PydanticValidationError) as second_error:
        final_summary = summarize_validation_error(second_error)
        logger.error(
            f"{tool_name}: AI response failed validation after retry", {"error": final_summary}
        )
        raise AIResponseError(
            "The AI service could not produce a valid response after retries.",
            {"lastError": final_summary},
        ) from second_error
