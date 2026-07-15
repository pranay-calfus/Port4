"""Pie charts for the admin dashboard (ticket status, and department mix for
the super-admin view), built with Altair (already a Streamlit dependency -
no new package needed).

Colors are drawn from a fixed, CVD-validated 7-hue categorical set (see the
dataviz skill's reference palette) rather than 8: running the palette's own
`validate_palette.js --pairs all` against all 8 hues showed two pairs
(blue/violet and aqua/magenta) fall well below the safe separation floor for
protanopia/deuteranopia once every slice can sit next to every other slice,
which is exactly the case in a pie chart (unlike a bar/line chart, where only
neighbors touch). Dropping violet leaves 7 hues with only one borderline
pair (aqua/magenta, still within the checked-and-accepted "floor band"),
assigned to two statuses/departments unlikely to dominate the same chart at
once. Every chart still ships a legend and a plain-text count/percentage
line, so identity never depends on color alone even for that pair.
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
    "NEW": "blue",
    "OPEN": "yellow",
    "IN_PROGRESS": "orange",
    "ON_HOLD": "red",
    "PENDING_CUSTOMER": "magenta",
    "RESOLVED": "aqua",
    "CLOSED": "green",
}

# Only 7 of the 8 real teams get a dedicated hue (same reasoning as above);
# any team not listed here (or "Unassigned") falls back to neutral gray.
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
    "Billing Team": "blue",
    "Support Team": "yellow",
    "Engineering": "orange",
    "QA": "red",
    "Security Team": "magenta",
    "Sales Team": "aqua",
    "Logistics": "green",
}


def _color_for(name: str, hue_map: dict[str, str], mode: str) -> str:
    hue_name = hue_map.get(name)
    if hue_name is None:
        return _MUTED_HUE
    return (_LIGHT_HUES if mode == "light" else _DARK_HUES)[hue_name]


def _render_pie_chart(
    counts: dict[str, int],
    order: list[str],
    hue_map: dict[str, str],
    mode: str,
    empty_message: str,
) -> None:
    # Fixed order first (never re-sorted by value - color follows the
    # entity, not its rank), then anything outside the known order (e.g. an
    # "Unassigned" department) appended afterward in whatever order it came.
    rows = [(name, counts[name]) for name in order if counts.get(name, 0) > 0]
    rows += [(name, count) for name, count in counts.items() if name not in order and count > 0]
    if not rows:
        st.caption(empty_message)
        return

    df = pd.DataFrame(rows, columns=["label", "count"])
    total = int(df["count"].sum())
    df["pct"] = df["count"] / total

    domain = [row[0] for row in rows]
    color_range = [_color_for(name, hue_map, mode) for name in domain]
    ink = "#f8fafc" if mode == "dark" else "#0f172a"
    surface = "#000000" if mode == "dark" else "#f7f8fa"

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
        .properties(height=260, background="transparent")
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, width="stretch")
    # Direct labels as plain text - the accessibility relief so identity
    # never depends on reading color alone, even for the one borderline hue
    # pair noted in the module docstring.
    st.caption(" · ".join(f"{name}: {count} ({count / total:.0%})" for name, count in rows))


def render_status_pie_chart(counts: dict[str, int], mode: str) -> None:
    _render_pie_chart(counts, STATUS_ORDER, _STATUS_HUE, mode, "No tickets to chart yet.")


def render_department_pie_chart(counts: dict[str, int], mode: str) -> None:
    _render_pie_chart(counts, DEPARTMENT_ORDER, _DEPARTMENT_HUE, mode, "No tickets to chart yet.")
