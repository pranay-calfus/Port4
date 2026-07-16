import html
from datetime import datetime

import streamlit as st

from ticket_router.models import EMOTION_EMOJI
from ticket_router.ui.html import flatten_html

LOW_CONFIDENCE_THRESHOLD = 0.65
MANUAL_BASELINE_SECONDS = 120

_PRIORITY_CLASS = {"High": "high", "Medium": "medium", "Low": "low"}


def _format_timestamp(value: str) -> str:
    """Formats an API timestamp ("2026-07-15T09:49:26.064108") into a short,
    human-readable one ("Jul 15, 2026 · 9:49 AM") instead of showing the
    raw ISO string with microseconds everywhere in the UI.
    """
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return value
    hour_12 = parsed.hour % 12 or 12
    return f'{parsed.strftime("%b %d, %Y")} · {hour_12}:{parsed.strftime("%M %p")}'


def render_ticket_ai_card(ticket: dict) -> None:
    """Renders a ticket's AI classification as a dark, sleek card - category,
    priority badge, assigned
    department, a confidence bar, and the one-line AI summary/reasoning.

    Takes plain ticket API fields (not the strict TicketRouteResult
    pydantic model) since a ticket's department can be "Unassigned" and its
    priority can have been reassigned since creation - neither of which
    would pass TicketRouteResult's validation, but both of which are still
    valid things to display here.
    """
    if not ticket.get("ai_summary"):
        st.info("AI categorization isn't available for this ticket yet - it needs manual triage.")
        return

    priority = ticket["priority"]
    accent = _PRIORITY_CLASS.get(priority, "medium")
    confidence = ticket.get("ai_confidence") or 0.0
    confidence_pct = round(confidence * 100)
    reasoning = html.escape(ticket.get("ai_summary") or "")
    category = html.escape(ticket.get("ai_category") or "—")
    team = html.escape(ticket.get("department") or "—")
    emotion_label = ticket.get("ai_emotion")
    emotion_emoji = EMOTION_EMOJI.get(emotion_label, "")
    emotion = html.escape(f"{emotion_emoji} {emotion_label}".strip() if emotion_label else "—")

    low_confidence_html = ""
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        low_confidence_html = f"""
        <div class="tr-low-confidence">
            Low confidence ({confidence_pct}%) - this ticket was short, ambiguous, or lacked detail.
            The classification below is still the model's best guess; consider a quick manual check
            or asking the customer for more detail.
        </div>
        """

    st.markdown(
        flatten_html(
            f"""
        <div class="tr-accent-{accent}" style="padding-left: 14px;">
            {low_confidence_html}
            <div style="display:flex; gap:12px; flex-wrap:wrap;">
                <div class="tr-field" style="flex:1; min-width:150px;">
                    <div class="tr-muted">Category</div>
                    <div class="tr-field-value">{category}</div>
                </div>
                <div class="tr-field" style="flex:1; min-width:150px;">
                    <div class="tr-muted">Priority</div>
                    <div style="margin-top:4px;"><span class="tr-badge tr-badge-{accent}">{priority}</span></div>
                </div>
                <div class="tr-field" style="flex:1; min-width:150px;">
                    <div class="tr-muted">Emotion</div>
                    <div style="margin-top:4px;"><span class="tr-pill">{emotion}</span></div>
                </div>
            </div>
            <div style="display:flex; gap:12px; flex-wrap:wrap;">
                <div class="tr-field" style="flex:1; min-width:180px;">
                    <div class="tr-muted">Assigned Team</div>
                    <div class="tr-field-value">{team}</div>
                </div>
                <div class="tr-field" style="flex:1; min-width:180px;">
                    <div class="tr-muted">Confidence</div>
                    <div class="tr-field-value">{confidence_pct}%</div>
                    <div style="height:6px; border-radius:999px; background:rgba(248,250,252,0.12); margin-top:6px; overflow:hidden;">
                        <div style="height:100%; width:{confidence_pct}%; background:#f8fafc;"></div>
                    </div>
                </div>
            </div>
            <div class="tr-field">
                <div class="tr-muted">Reason</div>
                <div class="tr-field-value" style="font-weight:400; color:#cbd5e1;">{reasoning}</div>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; color:#64748b; font-size:0.78rem;">
                <span>{html.escape(ticket.get("ticket_number", ""))}</span>
                <span>Created {html.escape(_format_timestamp(ticket.get("created_at", "")))}</span>
            </div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def render_priority_hint(ai_priority: str, chosen_priority: str) -> None:
    """Shown under the final-priority picker when the user's chosen priority
    differs from what the AI decided - a lightweight nudge, not a blocker,
    since the human's call is what actually sticks.
    """
    st.info(
        f"You set priority to **{chosen_priority}** - the AI suggested "
        f"**{ai_priority}** for this ticket."
    )


def render_comparison_section(samples_ms: list[float], manual_seconds: float | None = None) -> None:
    """Shows the mission-required manual-vs-AI time comparison. When the
    session has real measured AI samples, those numbers are actual evidence
    (measured `processingTime`), not an illustrative claim. Likewise, once
    the user has timed themselves via the "Manual Routing" control, the
    manual side switches from a documented typical baseline to their own
    measured time for this exact ticket.
    """
    has_data = len(samples_ms) > 0
    avg_ms = sum(samples_ms) / len(samples_ms) if has_data else None

    has_manual_data = manual_seconds is not None
    manual_baseline_seconds = manual_seconds if has_manual_data else MANUAL_BASELINE_SECONDS
    manual_display = f"{manual_seconds:.1f} s" if has_manual_data else "~2 min"
    manual_caption = (
        "Manual triage (you, measured)" if has_manual_data else "Manual triage (typical)"
    )

    if has_data:
        ai_display = f"{avg_ms:.0f} ms" if avg_ms < 1000 else f"{avg_ms / 1000:.2f} s"
        improvement_pct = round((1 - (avg_ms / 1000) / manual_baseline_seconds) * 100)
        saved_seconds = max(0, round(len(samples_ms) * (manual_baseline_seconds - avg_ms / 1000)))
        saved_label = f"{saved_seconds // 60} min {saved_seconds % 60} sec"
        ai_caption = "AI routing (your session avg.)"
        pill = f'<span class="tr-pill">{len(samples_ms)} ticket{"s" if len(samples_ms) != 1 else ""} measured</span>'
        baseline_phrase = (
            "your own measured manual time"
            if has_manual_data
            else f"a {MANUAL_BASELINE_SECONDS // 60}-minute manual triage baseline"
        )
        footer = (
            f"Based on the {len(samples_ms)} ticket{'s' if len(samples_ms) != 1 else ''} you've routed "
            f"this session (actual measured processing time), against {baseline_phrase}. "
            f"Estimated time saved so far: <b>{saved_label}</b>."
        )
    else:
        ai_display, improvement_pct = "~2 sec", round((1 - 2 / manual_baseline_seconds) * 100)
        ai_caption = "AI routing (illustrative)"
        pill = ""
        footer = (
            "Route a ticket above to replace these illustrative numbers with your own measured evidence. "
            + (
                "You've already timed your own manual routing for this ticket - route it with AI above "
                "to see the real comparison."
                if has_manual_data
                else "A support agent typically reads a ticket, decides its category and priority, and "
                "manually assigns it to the right team - a process that takes roughly two minutes. The "
                "AI router performs the same triage in a fraction of a second."
            )
        )

    st.markdown(
        flatten_html(
            f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span class="tr-muted" style="font-size:0.85rem;">MANUAL VS. AI ROUTING</span>
            {pill}
        </div>
        <div style="display:flex; gap:12px; flex-wrap:wrap;">
            <div class="tr-stat" style="flex:1; min-width:140px;">
                <div class="tr-stat-value" style="color:#cbd5e1;">{manual_display}</div>
                <div class="tr-stat-label">{manual_caption}</div>
            </div>
            <div class="tr-stat" style="flex:1; min-width:140px;">
                <div class="tr-stat-value" style="color:#f8fafc;">{ai_display}</div>
                <div class="tr-stat-label">{ai_caption}</div>
            </div>
            <div class="tr-stat" style="flex:1; min-width:140px;">
                <div class="tr-stat-value" style="color:#6ee7b7;">{improvement_pct}%</div>
                <div class="tr-stat-label">Faster than manual</div>
            </div>
        </div>
        <p style="color:#94a3b8; font-size:0.8rem; margin-top:10px;">{footer}</p>
        """
        ),
        unsafe_allow_html=True,
    )


def render_ticket_timeline(activity: list[dict]) -> None:
    """Renders a ticket's activity log as a connected vertical timeline
    (dot + line + event + timestamp) instead of a flat list of captions,
    so the ticket's stages actually read as a progression rather than a
    disconnected log dump.
    """
    if not activity:
        st.caption("No activity yet.")
        return

    items = []
    last_index = len(activity) - 1
    for i, entry in enumerate(activity):
        marker_html = '<div class="tr-timeline-dot"></div>'
        if i != last_index:
            marker_html += '<div class="tr-timeline-line"></div>'

        detail_html = ""
        if entry.get("detail"):
            detail_html = f'<div class="tr-timeline-detail">{html.escape(entry["detail"])}</div>'

        items.append(
            f"""
            <div class="tr-timeline-item">
                <div class="tr-timeline-marker">{marker_html}</div>
                <div class="tr-timeline-content">
                    <div class="tr-timeline-header">
                        <span class="tr-timeline-event">{html.escape(entry["event_type"])}</span>
                        <span class="tr-timeline-time">{html.escape(_format_timestamp(str(entry["created_at"])))}</span>
                    </div>
                    {detail_html}
                </div>
            </div>
            """
        )

    st.markdown(
        flatten_html(f'<div class="tr-timeline">{"".join(items)}</div>'),
        unsafe_allow_html=True,
    )
