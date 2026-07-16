"""Metric charts for the admin dashboards, built with Altair (already a
Streamlit dependency - no new package needed).

Colors are drawn from a fixed, CVD-validated 7-hue categorical set (see the
dataviz skill's reference palette). Two different chart forms are used
deliberately:

- Priority (3 categories) is a pie - small enough that every slice can sit
  next to every other slice ("all-pairs" safety) without exceeding the
  palette's capacity, validated with the skill's validate_palette.js
  --pairs all.
- Status, Department, and Emotion (5-7 categories) are horizontal bars in a
  FIXED category order (never re-sorted by value) - a pie at that many
  categories cannot be made all-pairs safe with this 8-hue system (verified:
  every 7-of-8 subset still has at least one hard-fail pair under
  --pairs all). A bar chart only needs *adjacent* pairs to be safe, which a
  carefully chosen fixed order achieves - but only if the order truly never
  changes, so bars are intentionally NOT sorted by value here.

Every chart still ships a legend/axis labels and a plain-text count/
percentage line, so identity never depends on color alone.
"""

import altair as alt
import pandas as pd
import streamlit as st

_LIGHT_HUES = {
    "blue": "#2a78d6",
    "aqua": "#1baf7a",
    "yellow": "#eda100",
    "green": "#008300",
    "red": "#e34948",
    "magenta": "#e87ba4",
    "orange": "#eb6834",
}
_DARK_HUES = {
    "blue": "#3987e5",
    "aqua": "#199e70",
    "yellow": "#c98500",
    "green": "#008300",
    "red": "#e66767",
    "magenta": "#d55181",
    "orange": "#d95926",
}
_MUTED_HUE = "#898781"  # overflow / unmapped categories - de-emphasis gray

# --- Fixed, validated category orders -----------------------------------
# Each sequence is a Hamiltonian path over the hues below where every
# CONSECUTIVE pair cleared validate_palette.js (both light and dark,
# --pairs adjacent) - the ordering is load-bearing, not decorative.

STATUS_ORDER = [
    "NEW",
    "OPEN",
    "IN_PROGRESS",
    "PENDING_CUSTOMER",
    "ON_HOLD",
    "RESOLVED",
    "CLOSED",
]
_STATUS_HUE = {
    "NEW": "orange",
    "OPEN": "blue",
    "IN_PROGRESS": "aqua",
    "PENDING_CUSTOMER": "yellow",
    "ON_HOLD": "magenta",
    "RESOLVED": "green",
    "CLOSED": "red",
}

DEPARTMENT_ORDER = [
    "Billing Team",
    "Support Team",
    "Engineering",
    "QA",
    "Security Team",
    "Sales Team",
    "Logistics",
]
_DEPARTMENT_HUE = {
    "Billing Team": "orange",
    "Support Team": "blue",
    "Engineering": "aqua",
    "QA": "yellow",
    "Security Team": "magenta",
    "Sales Team": "green",
    "Logistics": "red",
}

PRIORITY_ORDER = ["High", "Medium", "Low"]
_PRIORITY_HUE = {"High": "red", "Medium": "blue", "Low": "green"}

EMOTION_ORDER = ["Neutral", "Angry", "Worried", "Frustrated", "Disappointed"]
_EMOTION_HUE = {
    "Neutral": "green",
    "Angry": "red",
    "Worried": "blue",
    "Frustrated": "yellow",
    "Disappointed": "magenta",
}


def _color_for(name: str, hue_map: dict[str, str], mode: str) -> str:
    hue_name = hue_map.get(name)
    if hue_name is None:
        return _MUTED_HUE
    return (_LIGHT_HUES if mode == "light" else _DARK_HUES)[hue_name]


def _pretty_label(name: str) -> str:
    """Turns e.g. PENDING_CUSTOMER into "Pending Customer"; already-nice
    labels like "Billing Team" or "Neutral" pass through unchanged. Purely
    cosmetic - the underlying category name (used for color lookups) is
    untouched.
    """
    spaced = name.replace("_", " ")
    return spaced.title() if spaced.isupper() else spaced


def _ordered_rows(counts: dict[str, int], order: list[str]) -> list[tuple[str, int]]:
    # Fixed order first (never re-sorted by value - color follows the
    # entity, not its rank, and for the bar charts the adjacency safety
    # itself depends on this order never changing), then anything outside
    # the known order (e.g. an "Unassigned" department) appended after.
    rows = [(name, counts[name]) for name in order if counts.get(name, 0) > 0]
    rows += [(name, count) for name, count in counts.items() if name not in order and count > 0]
    return rows


def _ink_and_surface(mode: str) -> tuple[str, str]:
    ink = "#f8fafc" if mode == "dark" else "#0f172a"
    surface = "#000000" if mode == "dark" else "#f7f8fa"
    return ink, surface


def _render_pie_chart(
    counts: dict[str, int],
    order: list[str],
    hue_map: dict[str, str],
    mode: str,
    empty_message: str,
) -> None:
    rows = _ordered_rows(counts, order)
    if not rows:
        st.caption(empty_message)
        return

    df = pd.DataFrame(rows, columns=["label", "count"])
    total = int(df["count"].sum())
    df["pct"] = df["count"] / total

    domain = [row[0] for row in rows]
    color_range = [_color_for(name, hue_map, mode) for name in domain]
    ink, surface = _ink_and_surface(mode)

    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=55, stroke=surface, strokeWidth=2)
        .encode(
            theta=alt.Theta("count:Q", stack=True, sort=None),
            color=alt.Color(
                "label:N",
                scale=alt.Scale(domain=domain, range=color_range),
                legend=alt.Legend(title=None, labelColor=ink, symbolType="circle"),
                sort=domain,
            ),
            order=alt.Order("label:N", sort="ascending"),
            tooltip=[
                alt.Tooltip("label:N", title="Status"),
                alt.Tooltip("count:Q", title="Tickets"),
                alt.Tooltip("pct:Q", title="Share", format=".0%"),
            ],
        )
        .properties(height=240, background="transparent")
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, width="stretch")
    st.caption(" · ".join(f"{name}: {count} ({count / total:.0%})" for name, count in rows))


def _render_bar_chart(
    counts: dict[str, int],
    order: list[str],
    hue_map: dict[str, str],
    mode: str,
    empty_message: str,
) -> None:
    rows = _ordered_rows(counts, order)
    if not rows:
        st.caption(empty_message)
        return

    # "label" keeps the raw category name (BILLING_TEAM, PENDING_CUSTOMER,
    # ...) for the color lookup below; "display_label" is what's actually
    # shown on the axis/legend/tooltip - kept as a separate column so
    # prettifying it can never desync it from its color.
    df = pd.DataFrame(rows, columns=["label", "count"])
    total = int(df["count"].sum())
    df["pct"] = df["count"] / total
    df["display_label"] = df["label"].map(_pretty_label)

    domain = [row[0] for row in rows]
    display_domain = [_pretty_label(name) for name in domain]
    color_range = [_color_for(name, hue_map, mode) for name in domain]
    ink, surface = _ink_and_surface(mode)

    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            y=alt.Y(
                "display_label:N",
                sort=display_domain,
                title=None,
                # Generous, fixed padding between bands is what actually
                # prevents bars from visually touching/overlapping - a
                # bare band scale's default padding shrinks as more
                # categories are added, which is what caused the overlap.
                scale=alt.Scale(paddingInner=0.35, paddingOuter=0.2),
                axis=alt.Axis(labelColor=ink, labelLimit=170, labelPadding=8, labelFontSize=12),
            ),
            x=alt.X("count:Q", title=None, axis=alt.Axis(labelColor=ink, grid=False)),
            color=alt.Color(
                "display_label:N",
                scale=alt.Scale(domain=display_domain, range=color_range),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("display_label:N", title="Category"),
                alt.Tooltip("count:Q", title="Tickets"),
                alt.Tooltip("pct:Q", title="Share", format=".0%"),
            ],
        )
        .properties(height=38 * len(rows) + 24, background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(domainColor=surface, tickColor=surface)
    )
    st.altair_chart(chart, width="stretch")
    st.caption(
        " · ".join(f"{_pretty_label(name)}: {count} ({count / total:.0%})" for name, count in rows)
    )


def render_status_bar_chart(counts: dict[str, int], mode: str) -> None:
    _render_bar_chart(counts, STATUS_ORDER, _STATUS_HUE, mode, "No tickets to chart yet.")


def render_department_bar_chart(counts: dict[str, int], mode: str) -> None:
    _render_bar_chart(counts, DEPARTMENT_ORDER, _DEPARTMENT_HUE, mode, "No tickets to chart yet.")


def render_priority_pie_chart(counts: dict[str, int], mode: str) -> None:
    _render_pie_chart(counts, PRIORITY_ORDER, _PRIORITY_HUE, mode, "No tickets to chart yet.")


def render_emotion_bar_chart(counts: dict[str, int], mode: str) -> None:
    _render_bar_chart(counts, EMOTION_ORDER, _EMOTION_HUE, mode, "No AI-categorized tickets yet.")
