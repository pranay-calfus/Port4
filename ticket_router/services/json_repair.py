import json
import re

# Fallback JSON-repair utilities. Groq's forced tool-calling makes these
# rarely necessary (tool call arguments already arrive as a JSON string
# matching our schema), but they exist as defense-in-depth for the case a
# response is malformed - e.g. wrapped in prose or code fences.

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def strip_code_fences(raw: str) -> str:
    return _CODE_FENCE_RE.sub("", raw.strip()).strip()


def extract_first_json_object(raw: str) -> str | None:
    start = raw.find("{")
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]
    return None


def fix_trailing_commas(raw: str) -> str:
    return _TRAILING_COMMA_RE.sub(r"\1", raw)


def repair_and_parse(raw: str) -> object | None:
    """Attempts to coerce a raw, possibly malformed string into a parsed
    JSON value. Returns None instead of raising so callers can decide what
    to do next (e.g. fall through to the retry path).
    """
    candidates = [raw, strip_code_fences(raw)]

    extracted = extract_first_json_object(strip_code_fences(raw))
    if extracted:
        candidates.append(extracted)
        candidates.append(fix_trailing_commas(extracted))

    for candidate in candidates:
        try:
            return json.loads(fix_trailing_commas(candidate))
        except (json.JSONDecodeError, TypeError):
            continue
    return None
