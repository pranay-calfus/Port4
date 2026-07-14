"""Smart Support Ticket Router - Streamlit entrypoint.

A single-process Python app: paste a ticket, get back a structured,
always-valid JSON classification (category, priority, assigned team,
one-line reasoning, confidence) in seconds. See ticket_router/ for the
reusable routing service and README.md / docs/AI-Concepts.md for the full
write-up of the approach.
"""

import html
import json
import time
from datetime import datetime

import streamlit as st

from ticket_router import db
from ticket_router.config import config
from ticket_router.errors import AppError
from ticket_router.logger import logger
from ticket_router.models import ASSIGNED_TEAMS, CATEGORIES, PRIORITIES, TicketRequest
from ticket_router.services.agent_service import chat_with_department
from ticket_router.services.ticket_routing_service import route_ticket
from ticket_router.ui.components import (
    render_comparison_section,
    render_dot_row,
    render_priority_hint,
    render_result_card,
)
from ticket_router.ui.html import flatten_html
from ticket_router.ui.sample_tickets import load_sample_tickets
from ticket_router.ui.theme import inject_custom_theme

st.set_page_config(page_title="Smart Ticket Router", page_icon="🧭", layout="centered")
inject_custom_theme()


db.init_db()


@st.cache_resource
def _log_db_ready_once() -> None:
    """Logs the resolved path/row counts exactly once per server process
    (st.cache_resource caches across every session and rerun) so the server
    log makes it obvious at startup whether an existing database was found
    or a fresh one was created - the first thing to check if data ever
    appears to have reset.

    This is deliberately separate from db.init_db() above, which must run
    on every single rerun (cheap, idempotent CREATE TABLE IF NOT EXISTS): if
    init_db() were cached too, the tables would only ever be (re)created
    once - if the database file is ever deleted or replaced while the
    server keeps running, every write after that would crash with
    "no such table" instead of self-healing on the next rerun.
    """
    logger.info(
        "Ticket database ready",
        {
            "path": config.TICKET_DB_PATH,
            "teams": len(db.list_teams()),
            "tickets": len(db.list_all_tickets()),
        },
    )


_log_db_ready_once()

if "ticket_text" not in st.session_state:
    st.session_state.ticket_text = ""
if "result" not in st.session_state:
    st.session_state.result = None
if "error" not in st.session_state:
    st.session_state.error = None
if "session_samples" not in st.session_state:
    st.session_state.session_samples = []
if "demo_index" not in st.session_state:
    st.session_state.demo_index = 0
if "demo_history" not in st.session_state:
    st.session_state.demo_history = {}
if "manual_start_time" not in st.session_state:
    st.session_state.manual_start_time = None
if "manual_time_seconds" not in st.session_state:
    st.session_state.manual_time_seconds = None
if "manual_answer" not in st.session_state:
    st.session_state.manual_answer = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "chat_team" not in st.session_state:
    st.session_state.chat_team = None
if "routed_ticket_text" not in st.session_state:
    st.session_state.routed_ticket_text = None
if "ticket_id" not in st.session_state:
    st.session_state.ticket_id = None
if "final_priority" not in st.session_state:
    st.session_state.final_priority = None
if "user_priority" not in st.session_state:
    st.session_state.user_priority = "Medium"
if "admin_unlocked" not in st.session_state:
    st.session_state.admin_unlocked = False

_ADMIN_PRIORITY_CLASS = {"High": "high", "Medium": "medium", "Low": "low"}


def _clear_ticket() -> None:
    """on_click callback for the "Clear" button. Callbacks run before the
    script body re-executes, so it's safe to assign to
    st.session_state.ticket_text here - unlike assigning to it later in the
    script, after the st.text_area(key="ticket_text") widget has already
    been instantiated for this run, which Streamlit rejects.
    """
    st.session_state.ticket_text = ""
    st.session_state.result = None
    st.session_state.error = None
    st.session_state.manual_start_time = None
    st.session_state.manual_time_seconds = None
    st.session_state.manual_answer = None
    st.session_state.chat_history = []
    st.session_state.chat_team = None
    st.session_state.routed_ticket_text = None
    st.session_state.ticket_id = None
    st.session_state.final_priority = None
    st.session_state.user_priority = "Medium"


def _format_timestamp(value: str) -> str:
    """Renders a stored ISO timestamp (e.g. "2026-07-14T09:07:36.644976+00:00")
    as something readable in the admin dashboard instead of raw ISO-8601.
    """
    return datetime.fromisoformat(value).strftime("%b %d, %Y · %I:%M %p UTC")


def _admin_table_rows(tickets: list[dict]) -> list[dict]:
    """Builds the row dicts for one of the admin dashboard's Open/Closed
    dataframes. Status isn't a column here - each table is already scoped
    to one status, so repeating it on every row would be noise.
    """
    return [
        {
            "ID": t["id"],
            "Message": t["message"][:80] + ("…" if len(t["message"]) > 80 else ""),
            "Category": t["category"],
            "Team": t["assigned_team"],
            "Priority": t["final_priority"],
            "Created": _format_timestamp(t["created_at"]),
        }
        for t in tickets
    ]


@st.dialog("Close this ticket?")
def _confirm_close_ticket(ticket_id: int, message_preview: str) -> None:
    """A closing action is one-way from the customer's perspective (it can
    be reopened, but that's an admin correcting a mistake, not the normal
    flow) so it gets a confirmation step; reopening doesn't.
    """
    st.write("Are you sure you want to mark this ticket as closed?")
    st.caption(message_preview)
    cancel_col, confirm_col = st.columns(2)
    if cancel_col.button("Cancel", key=f"cancel_close_{ticket_id}", width="stretch"):
        st.rerun()
    if confirm_col.button(
        "Mark Closed", key=f"confirm_close_{ticket_id}", type="primary", width="stretch"
    ):
        db.set_status(ticket_id, "Closed")
        st.rerun()


@st.dialog("Delete this ticket?")
def _confirm_delete_ticket(ticket_id: int, message_preview: str) -> None:
    """Deletion is permanent (unlike closing, which can be undone via
    Reopen), so this is only ever offered for already-closed tickets and
    always gated behind its own confirmation step.
    """
    st.write("This permanently deletes the ticket. This cannot be undone.")
    st.caption(message_preview)
    cancel_col, confirm_col = st.columns(2)
    if cancel_col.button("Cancel", key=f"cancel_delete_{ticket_id}", width="stretch"):
        st.rerun()
    if confirm_col.button(
        "Delete", key=f"confirm_delete_{ticket_id}", type="primary", width="stretch"
    ):
        db.delete_ticket(ticket_id)
        st.rerun()


def _render_admin_ticket_card(ticket: dict, teams: list[str]) -> None:
    """Renders one ticket in the admin dashboard: the accent-striped info
    card (same `.tr-accent-*`/badge/pill language used by the Router tab's
    result card), a team-reassignment form, and close/reopen/delete
    actions. Priority is display-only here - it's the submitting user's
    call (set in the Router tab), not something the admin edits.
    """
    accent = _ADMIN_PRIORITY_CLASS.get(ticket["final_priority"], "medium")
    message_preview = html.escape(ticket["message"][:200])
    reasoning = html.escape(ticket["reasoning"])
    status_pill_class = "tr-pill-pending" if ticket["status"] == "Pending" else "tr-pill-closed"

    priority_hint_html = ""
    if ticket["final_priority"] != ticket["ai_priority"]:
        priority_hint_html = (
            f'<div style="color:#94a3b8; font-size:0.78rem; margin-top:4px;">'
            f'AI suggested {html.escape(ticket["ai_priority"])}</div>'
        )

    st.write("")
    with st.container(border=True):
        st.markdown(
            flatten_html(
                f"""
            <div class="tr-accent-{accent}" style="padding-left:14px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:18px;">
                    <div style="flex:1;">
                        <div class="tr-muted">Ticket #{ticket["id"]} &middot; {html.escape(ticket["category"])}</div>
                        <div class="tr-field-value" style="font-weight:400; color:#cbd5e1; margin-top:6px;">{message_preview}</div>
                        <div style="color:#64748b; font-size:0.82rem; margin-top:8px;">{reasoning}</div>
                    </div>
                    <div style="text-align:right; white-space:nowrap;">
                        <span class="tr-badge tr-badge-{accent}">{ticket["final_priority"]}</span>
                        {priority_hint_html}
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:8px; color:#64748b; font-size:0.78rem;
                            border-top:1px solid rgba(248,250,252,0.08); margin-top:14px; padding-top:12px;">
                    <span class="{status_pill_class}">{ticket["status"]}</span>
                    <span>{_format_timestamp(ticket["created_at"])}</span>
                </div>
            </div>
            """
            ),
            unsafe_allow_html=True,
        )

        st.write("")
        with st.form(key=f"reassign_form_{ticket['id']}"):
            team_col, save_col = st.columns([3, 1], gap="small")
            new_team = team_col.selectbox(
                "Team",
                teams,
                index=teams.index(ticket["assigned_team"]),
                key=f"team_{ticket['id']}",
            )
            reassign_clicked = save_col.form_submit_button("Reassign", width="stretch")
        if reassign_clicked and new_team != ticket["assigned_team"]:
            db.reassign_team(ticket["id"], new_team)
            st.rerun()

        if ticket["status"] == "Pending":
            if st.button("Mark Closed", key=f"status_{ticket['id']}", width="stretch"):
                _confirm_close_ticket(ticket["id"], ticket["message"][:200])
        else:
            reopen_col, delete_col = st.columns(2, gap="small")
            if reopen_col.button("Reopen", key=f"status_{ticket['id']}", width="stretch"):
                db.set_status(ticket["id"], "Pending")
                st.rerun()
            if delete_col.button("Delete", key=f"delete_{ticket['id']}", width="stretch"):
                _confirm_delete_ticket(ticket["id"], ticket["message"][:200])


def classify(message: str) -> tuple[object | None, str | None, float]:
    """Runs the shared routing service and times it. Returns
    (result, error_message, elapsed_ms) - exactly one of result/error is set.
    """
    start = time.perf_counter()
    try:
        result = route_ticket(message)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return result, None, elapsed_ms
    except AppError as error:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return None, error.message, elapsed_ms
    except Exception as error:  # noqa: BLE001 - last-resort guard, UI must never crash
        elapsed_ms = (time.perf_counter() - start) * 1000
        return None, f"Unexpected error: {error}", elapsed_ms


st.markdown(
    flatten_html(
        """
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
        <div style="width:36px; height:36px; border-radius:10px; background:##f6f5f7;
                    display:flex; align-items:center; justify-content:center; font-weight:800; color:white;">ST</div>
        <div>
            <div style="font-weight:700; color:#f1f5f9; font-size:1rem; line-height:1.1;">Smart Ticket Router</div>
            <div style="color:#94a3b8; font-size:0.78rem;">AI-powered support triage &middot;</div>
        </div>
    </div>
    """
    ),
    unsafe_allow_html=True,
)

router_tab, chat_tab, demo_tab, admin_tab = st.tabs(["Router", "Chat", "Demo Mode", "Admin"])

with router_tab:
    with st.container(border=True):
        st.markdown(
            '<p class="tr-subtitle">Paste a customer message and get an instant category, priority, '
            "and team assignment - backed by a structured, always-valid JSON response.</p>",
            unsafe_allow_html=True,
        )

        sample_tickets = load_sample_tickets()
        example_labels = ["Load an example ticket…"] + [
            f"[{t['categoryLabel']}] {t['title']}" for t in sample_tickets
        ]

        def _apply_selected_example() -> None:
            # Runs only when the selection actually changes (on_change), so
            # it never clobbers text the user has since typed/edited.
            choice = st.session_state.example_choice
            if choice != example_labels[0]:
                idx = example_labels.index(choice) - 1
                st.session_state.ticket_text = sample_tickets[idx]["message"]

        st.selectbox(
            "Try an example",
            example_labels,
            key="example_choice",
            on_change=_apply_selected_example,
            label_visibility="collapsed",
        )

        message = st.text_area(
            "Ticket message",
            key="ticket_text",
            height=150,
            max_chars=8000,
            placeholder='Paste a customer support message here… e.g. "This is RIDICULOUS, '
            "nothing works and I've been waiting 3 days!!!\"",
            label_visibility="collapsed",
        )

        priority_col, _ = st.columns([1, 3])
        priority_col.selectbox(
            "Priority",
            PRIORITIES,
            key="user_priority",
            help="Your call on urgency. The AI will suggest its own priority after routing - "
            "if the two disagree, you'll see a hint, but your choice here is what's saved.",
        )

        col1, col2, _ = st.columns([1, 1, 3])
        route_clicked = col1.button("Route Ticket", type="primary", use_container_width=True)
        col2.button("Clear", type="secondary", use_container_width=True, on_click=_clear_ticket)

        if route_clicked:
            try:
                TicketRequest(message=message)
            except Exception:
                st.session_state.error = "Please enter a ticket message before routing."
                st.session_state.result = None
            else:
                with st.spinner("Routing ticket…"):
                    result, error, elapsed_ms = classify(message)
                if result:
                    chosen_priority = st.session_state.user_priority
                    st.session_state.result = (result, elapsed_ms)
                    st.session_state.error = None
                    st.session_state.session_samples.append(elapsed_ms)
                    st.session_state.routed_ticket_text = message
                    st.session_state.chat_history = []
                    st.session_state.chat_team = None
                    st.session_state.final_priority = chosen_priority
                    st.session_state.ticket_id = db.add_ticket(
                        message=message,
                        category=result.category,
                        ai_priority=result.priority,
                        final_priority=chosen_priority,
                        assigned_team=result.assigned_team,
                        reasoning=result.reasoning,
                        confidence=result.confidence,
                        model_used=result.model_used,
                    )
                else:
                    st.session_state.error = error
                    st.session_state.result = None

        if st.session_state.error:
            st.error(st.session_state.error)

        if st.session_state.result:
            result, elapsed_ms = st.session_state.result
            render_result_card(result, elapsed_ms)

            final_priority = st.session_state.final_priority
            if final_priority and final_priority != result.priority:
                render_priority_hint(result.priority, final_priority)

            payload = {
                "success": True,
                "data": result.model_dump(by_alias=True),
                "modelUsed": result.model_used,
                "finalPriority": final_priority,
                "processingTime": f"{elapsed_ms:.0f} ms",
            }
            st.markdown(
                '<div class="tr-muted" style="margin-top:10px;">RAW JSON RESPONSE</div>',
                unsafe_allow_html=True,
            )
            st.code(json.dumps(payload, indent=2), language="json")

    st.write("")
    with st.container(border=True):
        st.markdown(
            '<div class="tr-muted">MANUAL ROUTING (for comparison)</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Time yourself triaging this ticket the way a support agent would - pick a "
            "category, priority, and team - then compare that against the AI below."
        )

        if (
            st.session_state.manual_start_time is None
            and st.session_state.manual_time_seconds is None
        ):
            if st.button("Start Manual Timer", use_container_width=False):
                st.session_state.manual_start_time = time.perf_counter()
                st.rerun()

        if st.session_state.manual_start_time is not None:
            st.info("Timer running - choose your answer below, then submit.")
            m_col1, m_col2, m_col3 = st.columns(3)
            manual_category = m_col1.selectbox("Category", CATEGORIES, key="manual_category")
            manual_priority = m_col2.selectbox("Priority", PRIORITIES, key="manual_priority")
            manual_team = m_col3.selectbox("Team", ASSIGNED_TEAMS, key="manual_team")
            if st.button("Submit Manual Routing", type="primary"):
                st.session_state.manual_time_seconds = (
                    time.perf_counter() - st.session_state.manual_start_time
                )
                st.session_state.manual_start_time = None
                st.session_state.manual_answer = {
                    "category": manual_category,
                    "priority": manual_priority,
                    "assignedTeam": manual_team,
                }
                st.rerun()

        if st.session_state.manual_time_seconds is not None:
            st.success(
                f"Manual routing took {st.session_state.manual_time_seconds:.1f} seconds. "
                "Route the same ticket with AI above to compare."
            )
            if st.button("Reset manual timer"):
                st.session_state.manual_start_time = None
                st.session_state.manual_time_seconds = None
                st.session_state.manual_answer = None
                st.rerun()

    st.write("")
    with st.container(border=True):
        render_comparison_section(
            st.session_state.session_samples,
            manual_seconds=st.session_state.manual_time_seconds,
        )

with chat_tab:
    with st.container(border=True):
        if not st.session_state.result:
            st.markdown(
                '<div class="tr-muted">CHAT WITH THE ASSIGNED TEAM</div>',
                unsafe_allow_html=True,
            )
            st.caption("Route a ticket in the Router tab first to chat with its assigned team.")
        else:
            result, _ = st.session_state.result
            st.markdown(
                f'<div class="tr-muted">CHAT WITH {result.assigned_team.upper()}</div>',
                unsafe_allow_html=True,
            )
            # st.caption(
            #     "Grounded in that team's own skills.md persona. The conversation starts "
            #     "with the ticket you just routed."
            # )

            if st.session_state.chat_team != result.assigned_team:
                st.session_state.chat_history = []
                st.session_state.chat_team = result.assigned_team

            # First time this team's chat is opened for the current ticket,
            # auto-send the routed ticket text as the opening message so the
            # agent already has context, instead of an empty chat.
            if not st.session_state.chat_history:
                ticket_message = st.session_state.routed_ticket_text
                st.session_state.chat_history.append(("user", ticket_message))
                with st.spinner("Thinking…"):
                    try:
                        reply = chat_with_department(result.assigned_team, [], ticket_message)
                    except AppError as error:
                        reply = f"⚠️ {error.message}"
                st.session_state.chat_history.append(("assistant", reply))

            for role, content in st.session_state.chat_history:
                with st.chat_message(role):
                    st.write(content)

            chat_input = st.chat_input(f"Message the {result.assigned_team}…")
            if chat_input:
                prior_history = list(st.session_state.chat_history)
                st.session_state.chat_history.append(("user", chat_input))
                with st.chat_message("user"):
                    st.write(chat_input)
                with st.chat_message("assistant"):
                    with st.spinner("Thinking…"):
                        try:
                            reply = chat_with_department(
                                result.assigned_team, prior_history, chat_input
                            )
                        except AppError as error:
                            reply = f"⚠️ {error.message}"
                    st.write(reply)
                st.session_state.chat_history.append(("assistant", reply))

with demo_tab:
    with st.container(border=True):
        sample_tickets = load_sample_tickets()
        total = len(sample_tickets)

        header_col1, header_col2 = st.columns([3, 1])
        header_col1.markdown(
            f'<div style="font-weight:700; color:#f1f5f9; font-size:1.1rem;">Demo Mode</div>'
            f'<p class="tr-subtitle">Step through all {total} sample tickets.</p>',
            unsafe_allow_html=True,
        )
        classified = len(st.session_state.demo_history)
        header_col2.markdown(
            f'<div style="text-align:right; margin-top:10px;"><span class="tr-pill">{classified} / {total} classified</span></div>',
            unsafe_allow_html=True,
        )

        render_dot_row(
            total, st.session_state.demo_index, set(st.session_state.demo_history.keys())
        )

        current = sample_tickets[st.session_state.demo_index]
        current_message = html.escape(current["message"])
        st.markdown(
            flatten_html(
                f"""
            <div class="tr-field">
                <div class="tr-muted">Ticket {st.session_state.demo_index + 1} of {total} &middot; {current["categoryLabel"]}</div>
                <div class="tr-field-value" style="font-weight:400; color:#cbd5e1;">{current_message}</div>
            </div>
            """
            ),
            unsafe_allow_html=True,
        )

        nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 2])
        prev_clicked = nav_col1.button("Previous", use_container_width=True)
        next_clicked = nav_col2.button("Next", type="primary", use_container_width=True)
        run_all_clicked = nav_col3.button("Run Full Demo (all 20)", use_container_width=True)

        if prev_clicked:
            st.session_state.demo_index = (st.session_state.demo_index - 1) % total
            st.rerun()
        if next_clicked:
            st.session_state.demo_index = (st.session_state.demo_index + 1) % total
            st.rerun()

        if run_all_clicked:
            progress = st.progress(0.0)
            status = st.empty()
            for i, ticket in enumerate(sample_tickets):
                status.markdown(f"Classifying ticket {i + 1}/{total}: *{ticket['title']}*")
                result, error, elapsed_ms = classify(ticket["message"])
                if result:
                    st.session_state.demo_history[i] = (result, elapsed_ms)
                    st.session_state.session_samples.append(elapsed_ms)
                progress.progress((i + 1) / total)
            status.markdown("Done - all 20 tickets classified.")
            st.session_state.demo_index = 0
            st.rerun()

        entry = st.session_state.demo_history.get(st.session_state.demo_index)
        if entry:
            result, elapsed_ms = entry
            render_result_card(result, elapsed_ms)
        else:
            classify_col, _ = st.columns([1, 3])
            if classify_col.button("Classify this ticket", type="primary"):
                with st.spinner("Routing ticket…"):
                    result, error, elapsed_ms = classify(current["message"])
                if result:
                    st.session_state.demo_history[st.session_state.demo_index] = (
                        result,
                        elapsed_ms,
                    )
                    st.session_state.session_samples.append(elapsed_ms)
                    st.rerun()
                else:
                    st.error(error)

with admin_tab:
    with st.container(border=True):
        st.markdown(
            '<div class="tr-muted">ADMIN DASHBOARD</div>'
            '<p class="tr-subtitle">Filter tickets by team, review priority, and manually '
            "re-route.</p>",
            unsafe_allow_html=True,
        )

        if not config.ADMIN_PASSWORD:
            st.error(
                "ADMIN_PASSWORD is not set. Set it in your .env file to enable the admin "
                "dashboard."
            )
        elif not st.session_state.admin_unlocked:
            admin_password = st.text_input("Password", type="password", key="admin_password")
            if st.button("Unlock", type="primary", key="admin_unlock"):
                if admin_password == config.ADMIN_PASSWORD:
                    st.session_state.admin_unlocked = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        else:
            teams = db.list_teams() or list(ASSIGNED_TEAMS)
            all_tickets = db.list_all_tickets()
            open_all = [t for t in all_tickets if t["status"] == "Pending"]
            closed_all = [t for t in all_tickets if t["status"] == "Closed"]

            st.markdown(
                '<div class="tr-muted" style="margin-top:6px;">ALL TICKETS</div>',
                unsafe_allow_html=True,
            )
            total_col, pending_col, closed_col = st.columns(3, gap="medium")
            with total_col.container(key="admin-stat-total"):
                st.metric("Total", len(all_tickets))
            with pending_col.container(key="admin-stat-pending"):
                st.metric("Pending", len(open_all))
            with closed_col.container(key="admin-stat-closed"):
                st.metric("Closed", len(closed_all))

            st.write("")
            if not all_tickets:
                st.caption("No tickets routed yet - route one from the Router tab first.")
            else:
                st.markdown(
                    '<div class="tr-muted" style="margin-top:4px;">OPEN TICKETS</div>',
                    unsafe_allow_html=True,
                )
                if not open_all:
                    st.caption("No open tickets.")
                else:
                    st.dataframe(_admin_table_rows(open_all), width="stretch", hide_index=True)

                st.write("")
                st.markdown('<div class="tr-muted">CLOSED TICKETS</div>', unsafe_allow_html=True)
                if not closed_all:
                    st.caption("No closed tickets yet.")
                else:
                    st.dataframe(_admin_table_rows(closed_all), width="stretch", hide_index=True)

                st.caption(f"{len(teams)} teams · {len(all_tickets)} tickets tracked")

    if config.ADMIN_PASSWORD and st.session_state.admin_unlocked:
        st.write("")
        st.markdown('<div class="tr-muted">FILTER BY TEAM</div>', unsafe_allow_html=True)
        team_pending_counts = db.pending_counts_by_team()
        admin_team = st.selectbox(
            "Team",
            teams,
            key="admin_team_filter",
            format_func=lambda t: (
                f"🔵 {t} ({team_pending_counts[t]} pending)"
                if team_pending_counts.get(t)
                else f"{t} (0 pending)"
            ),
        )

        team_counts = db.count_by_status(admin_team)
        team_count_col1, team_count_col2 = st.columns(2, gap="medium")
        with team_count_col1.container(key="admin-team-stat-pending"):
            st.metric("Pending", team_counts["Pending"])
        with team_count_col2.container(key="admin-team-stat-closed"):
            st.metric("Closed", team_counts["Closed"])

        team_tickets = db.list_tickets_for_team(admin_team)
        open_team_tickets = [t for t in team_tickets if t["status"] == "Pending"]
        closed_team_tickets = [t for t in team_tickets if t["status"] == "Closed"]

        st.markdown(
            f'<div class="tr-muted" style="margin-top:18px;">'
            f"OPEN ({len(open_team_tickets)}) FOR {html.escape(admin_team.upper())}</div>",
            unsafe_allow_html=True,
        )
        if not open_team_tickets:
            st.caption("No open tickets assigned to this team.")
        else:
            for ticket in open_team_tickets:
                _render_admin_ticket_card(ticket, teams)

        st.write("")
        st.markdown(
            f'<div class="tr-muted" style="margin-top:10px;">'
            f"CLOSED ({len(closed_team_tickets)}) FOR {html.escape(admin_team.upper())}</div>",
            unsafe_allow_html=True,
        )
        if not closed_team_tickets:
            st.caption("No closed tickets for this team.")
        else:
            for ticket in closed_team_tickets:
                _render_admin_ticket_card(ticket, teams)

# st.markdown(
#     '<p style="text-align:center; color:#475569; font-size:0.75rem; margin-top:18px;">'
#     "Structured JSON classification via OpenAI &middot; Pydantic-validated &middot; never returns malformed data</p>",
#     unsafe_allow_html=True,
# )
