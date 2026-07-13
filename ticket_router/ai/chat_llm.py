from langchain_openai import ChatOpenAI

from ticket_router.ai.openai_provider import build_model_chain
from ticket_router.config import config
from ticket_router.errors import AIUnavailableError

# Free-form conversational LLM (no forced tool call) shared by every
# department agent - built with LangChain's own `.with_fallbacks()`
# primitive over the same OpenAI model chain used for ticket routing (see
# ticket_router.ai.openai_provider.build_model_chain), so a rate limit or
# outage on the primary model fails over declaratively rather than via a
# hand-rolled retry loop.


def build_chat_llm() -> ChatOpenAI:
    if not config.OPENAI_API_KEY:
        raise AIUnavailableError(
            "AI service unavailable: OPENAI_API_KEY is not configured. Set it in .env."
        )

    primary_model, *fallback_models = build_model_chain()
    primary = ChatOpenAI(api_key=config.OPENAI_API_KEY, model=primary_model, max_tokens=1024)
    if not fallback_models:
        return primary

    fallbacks = [
        ChatOpenAI(api_key=config.OPENAI_API_KEY, model=model, max_tokens=1024)
        for model in fallback_models
    ]
    return primary.with_fallbacks(fallbacks)
