"""Groups the free-generated `theme` labels on tickets/feedback (see
ticket_router.models.TicketRouteResult.theme) into canonical buckets for
dashboard aggregation - never touches the stored per-record value itself.

Themes are LLM output, not a fixed taxonomy (see THEME RULES in
ticket_router/prompts.py), so the same recurring problem can come back
phrased as "Billing Error", "Billing Errors", or "Payment Issue". Without
normalization each phrasing gets its own bar/slice in the dashboard even
though they're the same underlying issue. This module merges those
variants at aggregation time only - backend.services.ticket_service's
_top_themes/_theme_trend and weekly_summary_service's _theme_excerpts are
the only callers; every other read of a `theme` column (the feedback/
ticket detail views, FeedbackOut/TicketOut) still returns the AI's
original, unmodified string.
"""

import re

_PUNCT_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")

# Plural -> singular heuristics, in the order they're tried. Deliberately a
# simple suffix-based stemmer, not a full NLP library: the vocabulary here
# is short (2-4 word) AI-generated theme phrases like "Billing Errors" or
# "Login Issues", not general English prose, so a handful of regular-plural
# rules covers the overwhelming majority of real cases. Known gap: a few
# irregular plurals (e.g. "buses" -> "buse" instead of "bus") aren't handled
# correctly - accepted as out of scope for this vocabulary.
_IES_RE = re.compile(r"^(.*[^aeiou])ies$")
_SIBILANT_ES_RE = re.compile(r"^(.*(?:x|z|ch|sh))es$")


def _singularize_word(word: str) -> str:
    if len(word) <= 3:
        return word
    m = _IES_RE.match(word)
    if m:
        return f"{m.group(1)}y"
    m = _SIBILANT_ES_RE.match(word)
    if m:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def normalize_theme(theme: str) -> str:
    """Canonicalizes a theme label into a grouping key: lowercase, trimmed,
    punctuation stripped, whitespace collapsed, each word singularized. Not
    meant for display - see THEME_SYNONYMS/group_themes for the label a
    group of matching raw themes is actually displayed as.
    """
    text = _PUNCT_RE.sub("", theme.strip().lower())
    text = _WHITESPACE_RE.sub(" ", text).strip()
    words = [_singularize_word(w) for w in text.split(" ") if w]
    return " ".join(words)


# Canonical display label for known synonymous/duplicate phrasings, keyed
# by the *normalized* form (see normalize_theme). "Billing Error", "Billing
# Errors", and "Payment Issue" all normalize to a key below, so all three
# merge into one "Billing Issues" bucket instead of three near-duplicate
# bars. Extend this as new recurring synonyms are noticed in practice.
THEME_SYNONYMS: dict[str, str] = {
    "billing error": "Billing Issues",
    "billing issue": "Billing Issues",
    "payment issue": "Billing Issues",
    "payment error": "Billing Issues",
    "payment failure": "Billing Issues",
}


def group_themes(items: list[dict], *, theme_key=lambda item: item["theme"]) -> dict[str, str]:
    """Maps each distinct raw theme string appearing in `items` to the
    canonical label its normalized group should be displayed as. A group
    with a THEME_SYNONYMS entry always uses that canonical name; otherwise
    the group's own most-frequent original raw variant wins (preserving
    whatever casing/acronyms the AI actually used, e.g. "UI Improvements"),
    with ties broken by whichever variant appeared first in `items`.

    Callers tally/bucket by looking up each item's raw theme in the
    returned dict - see _top_themes/_theme_trend in ticket_service.py and
    _theme_excerpts in weekly_summary_service.py.
    """
    raw_counts: dict[str, int] = {}
    first_seen_order: list[str] = []
    for item in items:
        raw = theme_key(item)
        if raw is None:
            continue
        if raw not in raw_counts:
            first_seen_order.append(raw)
        raw_counts[raw] = raw_counts.get(raw, 0) + 1

    groups: dict[str, list[str]] = {}
    for raw in first_seen_order:
        groups.setdefault(normalize_theme(raw), []).append(raw)

    raw_to_label: dict[str, str] = {}
    for key, variants in groups.items():
        canonical = THEME_SYNONYMS.get(key) or max(variants, key=lambda raw: raw_counts[raw])
        for raw in variants:
            raw_to_label[raw] = canonical
    return raw_to_label
