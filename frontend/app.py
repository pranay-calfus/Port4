"""Ticket Triage Support System - single Streamlit entry point, one port,
one landing page.

The landing page offers a Customer login/register tab and an Admin login
tab side by side; after logging in, the app renders the customer chat +
ticket dashboard or the admin queue + metrics dashboard depending on the
logged-in account's role. Everything talks to the backend API exclusively
over HTTP (frontend/api_client.py) - there is no direct DB access here.

The session (JWT) is mirrored into the URL's query params so a browser
refresh doesn't force a re-login - see _restore_session_from_query_params().
"""

import json
import sys
import time
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR))  # for api_client (sibling module)
sys.path.insert(0, str(_THIS_DIR.parent))  # for ticket_router (repo root package)

import api_client as api
import streamlit as st
from api_client import TICKET_STATUSES, ApiError

from ticket_router.models import ASSIGNED_TEAMS, CATEGORIES, PRIORITIES
from ticket_router.ui.charts import (
    render_department_bar_chart,
    render_emotion_bar_chart,
    render_priority_pie_chart,
    render_status_bar_chart,
)
from ticket_router.ui.components import (
    render_comparison_section,
    render_priority_hint,
    render_ticket_ai_card,
    render_ticket_timeline,
)
from ticket_router.ui.theme import inject_custom_theme

APP_NAME = "Ticket Triage Support System"
APP_ICON = "🎟️"

UNASSIGNED_DEPARTMENT = "Unassigned"
DEPARTMENTS = (UNASSIGNED_DEPARTMENT, *ASSIGNED_TEAMS)

st.set_page_config(page_title=APP_NAME, page_icon=APP_ICON, layout="wide")

for key, default in {
    "token": None,
    "identity": None,
    "selected_ticket_id": None,
    "theme_mode": "dark",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

inject_custom_theme(st.session_state.theme_mode)


def _restore_session_from_query_params() -> None:
    """Survives a browser refresh: the JWT lives in the URL's query params
    (set on login, cleared on logout), so a fresh Streamlit session can
    silently re-authenticate instead of showing the login screen again.
    """
    if st.session_state.token:
        return
    token = st.query_params.get("token")
    if not token:
        return
    try:
        identity = api.whoami(token)
    except ApiError:
        if "token" in st.query_params:
            del st.query_params["token"]
        return
    st.session_state.token = token
    st.session_state.identity = identity


def _set_session(token: str, identity: dict) -> None:
    st.session_state.token = token
    st.session_state.identity = identity
    st.query_params["token"] = token


def _logout() -> None:
    st.session_state.token = None
    st.session_state.identity = None
    st.session_state.selected_ticket_id = None
    if "token" in st.query_params:
        del st.query_params["token"]


_restore_session_from_query_params()


# --- Shared header (title, theme toggle, profile) ---------------------------


def _initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _scroll_to_anchor(anchor_id: str) -> None:
    """Scrolls the page down to the element with id=`anchor_id`. Streamlit
    has no native "scroll to element" API and a freshly opened ticket
    detail renders below a (possibly long) ticket list, so without this a
    click on a ticket looks like nothing happened until the user manually
    scrolls down. Runs in an iframe, so it must reach through to
    `window.parent` to touch the real page.
    """
    st.iframe(
        f"""
        <script>
            const el = window.parent.document.getElementById("{anchor_id}");
            if (el) {{ el.scrollIntoView({{behavior: "smooth", block: "start"}}); }}
        </script>
        """,
        height=1,
    )


def _render_header() -> None:
    if st.session_state.token:
        title_col, theme_col, profile_col = st.columns([7, 1, 1])
    else:
        title_col, theme_col = st.columns([8, 1])
        profile_col = None

    with title_col:
        st.markdown(
            '<div style="display:flex; align-items:center; gap:10px; padding-top:4px;">'
            f'<span style="font-size:1.7rem; line-height:1;">{APP_ICON}</span>'
            f'<span style="font-size:1.25rem; font-weight:700;">{APP_NAME}</span>'
            "</div>",
            unsafe_allow_html=True,
        )

    with theme_col:
        is_dark = st.session_state.theme_mode == "dark"
        icon = "☀️" if is_dark else "🌙"
        tooltip = "Switch to light mode" if is_dark else "Switch to dark mode"
        if st.button(icon, key="theme_toggle_button", help=tooltip):
            st.session_state.theme_mode = "light" if is_dark else "dark"
            st.rerun()

    if profile_col is not None:
        with profile_col:
            identity = st.session_state.identity
            with st.popover(_initials(identity["name"]), key="profile_popover"):
                st.markdown(f"**{identity['name']}**")
                st.caption(identity["email"])
                if identity["role"] == "ADMIN":
                    scope = identity["department"] or "All departments (super-admin)"
                    st.caption(f"Scope: {scope}")
                else:
                    st.caption("Customer account")
                st.divider()
                if st.button(
                    "Log Out", key="profile_logout_button", type="primary", width="stretch"
                ):
                    _logout()
                    st.rerun()

    st.write("")


# --- Landing page (logged out) ----------------------------------------------


def _render_landing() -> None:
    customer_tab, admin_tab = st.tabs(["Customer", "Admin"])

    with customer_tab:
        login_tab, register_tab = st.tabs(["Log In", "Register"])

        with login_tab, st.container(border=True):
            email = st.text_input("Email", key="cust_login_email")
            password = st.text_input("Password", type="password", key="cust_login_password")
            if st.button("Log In", type="primary", key="cust_login_submit"):
                try:
                    result = api.login(email, password)
                except ApiError as error:
                    st.error(error.detail)
                else:
                    _set_session(result["access_token"], result["user"])
                    st.rerun()

            with st.expander("Forgot password?"):
                forgot_email = st.text_input("Email", key="forgot_email")
                if st.button("Send reset link", key="forgot_submit"):
                    try:
                        response = api.forgot_password(forgot_email)
                    except ApiError as error:
                        st.error(error.detail)
                    else:
                        st.success(response["message"])

        with register_tab, st.container(border=True):
            name = st.text_input("Name", key="register_name")
            reg_email = st.text_input("Email", key="register_email")
            reg_password = st.text_input(
                "Password", type="password", key="register_password", help="At least 8 characters"
            )
            if st.button("Create Account", type="primary", key="register_submit"):
                try:
                    result = api.register(name, reg_email, reg_password)
                except ApiError as error:
                    st.error(error.detail)
                else:
                    _set_session(result["access_token"], result["user"])
                    st.rerun()

    with admin_tab, st.container(border=True):
        st.caption("Admin accounts are provisioned out-of-band - see backend/create_admin.py.")
        admin_email = st.text_input("Email", key="admin_login_email")
        admin_password = st.text_input("Password", type="password", key="admin_login_password")
        if st.button("Log In", type="primary", key="admin_login_submit"):
            try:
                result = api.admin_login(admin_email, admin_password)
            except ApiError as error:
                st.error(error.detail)
            else:
                _set_session(result["access_token"], result["user"])
                st.rerun()


# --- Customer app -------------------------------------------------------------


def _render_ticket_json(ticket: dict) -> None:
    payload = {
        "success": True,
        "data": {
            "category": ticket.get("ai_category"),
            "priority": ticket["priority"],
            "assignedTeam": ticket["department"],
            "emotion": ticket.get("ai_emotion"),
            "reasoning": ticket.get("ai_summary"),
            "confidence": ticket.get("ai_confidence"),
        },
        "ticketNumber": ticket["ticket_number"],
        "status": ticket["status"],
    }
    st.markdown(
        '<div class="tr-muted" style="margin-top:10px;">RAW JSON RESPONSE</div>',
        unsafe_allow_html=True,
    )
    st.code(json.dumps(payload, indent=2), language="json")


def _render_new_ticket_tab(token: str) -> None:
    """One text box per issue, a "+" to add another - each becomes its own
    ticket, classified independently. This is the only way a customer
    creates a ticket; there is no separate single-issue path.
    """
    st.subheader("Describe your issue(s)")
    st.caption(
        "Paste one or more issues below - each becomes its own ticket, classified "
        "independently and routed to the right team."
    )

    st.session_state.setdefault("bulk_ticket_ids", [0])
    st.session_state.setdefault("bulk_ticket_next_id", 1)
    st.session_state.setdefault("bulk_submitting", False)

    with st.container(border=True):
        for i, box_id in enumerate(st.session_state.bulk_ticket_ids):
            box_col, remove_col = st.columns([6, 1])
            box_col.text_area(
                f"Ticket {i + 1}",
                key=f"bulk_ticket_{box_id}",
                label_visibility="collapsed",
                placeholder=f"Describe issue {i + 1}...",
                disabled=st.session_state.bulk_submitting,
            )
            if (
                len(st.session_state.bulk_ticket_ids) > 1
                and not st.session_state.bulk_submitting
                and remove_col.button(
                    "✕", key=f"remove_bulk_ticket_{box_id}", help="Remove this box"
                )
            ):
                st.session_state.bulk_ticket_ids.remove(box_id)
                st.rerun()

        add_col, submit_col = st.columns([1, 4])
        if add_col.button(
            "➕",
            key="add_bulk_ticket",
            help="Add another ticket box",
            disabled=st.session_state.bulk_submitting,
        ):
            st.session_state.bulk_ticket_ids.append(st.session_state.bulk_ticket_next_id)
            st.session_state.bulk_ticket_next_id += 1
            st.rerun()

        submit_clicked = submit_col.button(
            "Route All Tickets" if not st.session_state.bulk_submitting else "Routing…",
            type="primary",
            key="submit_bulk_tickets",
            disabled=st.session_state.bulk_submitting,
        )
        if submit_clicked and not st.session_state.bulk_submitting:
            messages = [
                st.session_state.get(f"bulk_ticket_{box_id}", "").strip()
                for box_id in st.session_state.bulk_ticket_ids
            ]
            messages = [m for m in messages if m]
            if not messages:
                st.error("Enter at least one ticket description before routing.")
            else:
                # Set the guard and rerun *before* calling the (slow -
                # one AI classification call per ticket) API, so the button
                # is already disabled if the user clicks again while it's
                # in flight - a single click can otherwise fire twice on a
                # slow connection and create duplicate tickets.
                st.session_state.bulk_submitting = True
                st.rerun()

    if st.session_state.bulk_submitting:
        messages = [
            st.session_state.get(f"bulk_ticket_{box_id}", "").strip()
            for box_id in st.session_state.bulk_ticket_ids
        ]
        messages = [m for m in messages if m]
        with st.spinner(f"Routing {len(messages)} ticket{'s' if len(messages) != 1 else ''}…"):
            try:
                tickets = api.bulk_create_tickets(token, messages)
            except ApiError as error:
                st.error(error.detail)
            else:
                st.session_state.bulk_created_tickets = tickets
                next_id = st.session_state.bulk_ticket_next_id
                st.session_state.bulk_ticket_ids = [next_id]
                st.session_state.bulk_ticket_next_id = next_id + 1
        st.session_state.bulk_submitting = False
        st.rerun()

    if st.session_state.get("bulk_created_tickets"):
        tickets = st.session_state.bulk_created_tickets
        st.success(f"Created {len(tickets)} ticket{'s' if len(tickets) != 1 else ''}.")
        # Each ticket gets its own expanded chat window right here (not just
        # in "My Tickets") - _render_ticket_detail already has the AI's
        # initial reply, so the conversation is visibly live immediately,
        # and its reply box/keys are namespaced by ticket_id so multiple
        # tickets never collide.
        for ticket in tickets:
            with st.expander(f"{ticket['ticket_number']} — {ticket['title']}", expanded=True):
                _render_ticket_detail(token, ticket["id"])
                _render_ticket_json(ticket)
        if st.button("Dismiss", key="dismiss_bulk_results"):
            st.session_state.bulk_created_tickets = None
            st.rerun()


def _render_ticket_detail(token: str, ticket_id: int) -> None:
    try:
        detail = api.get_my_ticket(token, ticket_id)
    except ApiError as error:
        st.error(error.detail)
        return

    st.markdown(f'<div id="ticket-detail-{ticket_id}"></div>', unsafe_allow_html=True)
    _scroll_to_anchor(f"ticket-detail-{ticket_id}")

    st.divider()
    with st.container(border=True):
        st.markdown(f"### {detail['ticket_number']} — {detail['title']}")
        st.write(
            f"Status: **{detail['status']}** · Priority: **{detail['priority']}** · "
            f"Department: **{detail['department']}**"
        )
        render_ticket_ai_card(detail)
        if detail.get("ai_priority") and detail["priority"] != detail["ai_priority"]:
            render_priority_hint(detail["ai_priority"], detail["priority"])

        st.markdown("**Conversation**")
        sender_role = {"USER": "user", "ADMIN": "assistant", "AI": "assistant"}
        for message in detail["messages"]:
            with st.chat_message(sender_role[message["sender_type"]]):
                st.caption(message["sender_type"])
                st.write(message["message"])

        st.markdown(
            '<div class="tr-muted" style="margin-top:14px;">🕒 TIMELINE</div>',
            unsafe_allow_html=True,
        )
        render_ticket_timeline(detail["activity"])

        if detail["status"] == "CLOSED":
            st.caption("This ticket is closed. Please open a new ticket for any further issues.")
            return

        reply_text = st.text_area("Reply", key=f"reply_text_{ticket_id}")
        if st.button("Send Reply", key=f"send_reply_{ticket_id}"):
            if reply_text.strip():
                try:
                    api.reply_to_ticket(token, ticket_id, reply_text)
                except ApiError as error:
                    st.error(error.detail)
                else:
                    st.rerun()

        if detail["status"] == "RESOLVED":
            accept_col, reject_col = st.columns(2)
            if accept_col.button("✅ Accept Solution", key=f"accept_{ticket_id}"):
                try:
                    api.accept_solution(token, ticket_id)
                except ApiError as error:
                    st.error(error.detail)
                else:
                    st.rerun()
            if reject_col.button("↩️ Reopen (not resolved)", key=f"reopen_{ticket_id}"):
                try:
                    api.reopen_ticket(token, ticket_id)
                except ApiError as error:
                    st.error(error.detail)
                else:
                    st.rerun()


def _render_tickets_tab(token: str) -> None:
    try:
        tickets = api.list_my_tickets(token)
    except ApiError as error:
        st.error(error.detail)
        return

    with st.container(border=True):
        status_filter = st.selectbox(
            "Filter by status", ["All", *TICKET_STATUSES], key="status_filter"
        )
        filtered = (
            tickets
            if status_filter == "All"
            else [t for t in tickets if t["status"] == status_filter]
        )

        if not filtered:
            st.caption("No tickets match this filter.")
        for ticket in filtered:
            label = (
                f"{ticket['ticket_number']} · {ticket['title']} · "
                f"{ticket['status']} · {ticket['priority']} priority"
            )
            if st.button(label, key=f"open_ticket_{ticket['id']}"):
                st.session_state.selected_ticket_id = ticket["id"]

    if st.session_state.selected_ticket_id is not None:
        _render_ticket_detail(token, st.session_state.selected_ticket_id)


def _render_customer_app() -> None:
    token = st.session_state.token

    new_ticket_tab, tickets_tab = st.tabs(["New Ticket", "My Tickets"])
    with new_ticket_tab:
        _render_new_ticket_tab(token)
    with tickets_tab:
        _render_tickets_tab(token)


# --- Admin app ----------------------------------------------------------------


def _render_stat_row(metrics: dict) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("📥 Open Tickets", metrics["open_tickets"])
    col2.metric("🗂️ Total Tickets", metrics["total_tickets"])
    col3.metric(
        "⏱️ Avg Resolution Time",
        (
            f"{metrics['avg_resolution_hours']:.1f}h"
            if metrics["avg_resolution_hours"] is not None
            else "—"
        ),
    )


def _render_metric_charts(metrics: dict, is_super_admin: bool) -> None:
    mode = st.session_state.theme_mode

    row1_col1, row1_col2 = st.columns(2)
    with row1_col1, st.container(border=True):
        st.markdown('<div class="tr-muted">📊 TICKETS BY STATUS</div>', unsafe_allow_html=True)
        render_status_bar_chart(metrics["tickets_per_status"], mode)
    with row1_col2, st.container(border=True):
        st.markdown('<div class="tr-muted">🎯 TICKETS BY PRIORITY</div>', unsafe_allow_html=True)
        render_priority_pie_chart(metrics["tickets_per_priority"], mode)

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1, st.container(border=True):
        st.markdown('<div class="tr-muted">💬 TICKETS BY EMOTION</div>', unsafe_allow_html=True)
        render_emotion_bar_chart(metrics["tickets_per_emotion"], mode)
    if is_super_admin:
        with row2_col2, st.container(border=True):
            st.markdown(
                '<div class="tr-muted">🏢 TICKETS BY DEPARTMENT</div>', unsafe_allow_html=True
            )
            render_department_bar_chart(metrics["tickets_per_department"], mode)


def _render_metrics(token: str, is_super_admin: bool) -> None:
    try:
        metrics = api.admin_metrics(token)
    except ApiError as error:
        st.error(error.detail)
        return

    _render_stat_row(metrics)
    st.write("")
    _render_metric_charts(metrics, is_super_admin)

    by_department = metrics.get("by_department")
    if is_super_admin and by_department:
        st.write("")
        st.markdown('<div class="tr-muted">👥 BY TEAM</div>', unsafe_allow_html=True)
        team_tabs = st.tabs(list(by_department.keys()))
        for tab, team_metrics in zip(team_tabs, by_department.values(), strict=True):
            with tab:
                _render_stat_row(team_metrics)
                st.write("")
                _render_metric_charts(team_metrics, is_super_admin=False)


def _render_manual_routing_panel(ticket_id: int, detail: dict) -> None:
    """Lets an admin time themselves triaging a ticket the way a human
    agent would, then compares that against the AI's own classification -
    both the actual field-by-field match and the time each approach took.
    """
    start_key = f"manual_start_{ticket_id}"
    result_key = f"manual_result_{ticket_id}"
    st.session_state.setdefault(start_key, None)
    st.session_state.setdefault(result_key, None)

    with st.container(border=True):
        st.markdown(
            '<div class="tr-muted">⏱️ MANUAL ROUTING (FOR COMPARISON)</div>', unsafe_allow_html=True
        )
        st.caption(
            "Time yourself triaging this ticket the way a support agent would - pick a "
            "category, priority, and team - then compare that against the AI above."
        )

        if st.session_state[start_key] is None and st.session_state[result_key] is None:
            if st.button("Start Manual Timer", key=f"start_manual_{ticket_id}"):
                st.session_state[start_key] = time.perf_counter()
                st.rerun()

        if st.session_state[start_key] is not None:
            st.info("Timer running - choose your answer below, then submit.")
            cat_col, pri_col, team_col = st.columns(3)
            manual_category = cat_col.selectbox(
                "Category", CATEGORIES, key=f"manual_category_{ticket_id}"
            )
            manual_priority = pri_col.selectbox(
                "Priority", PRIORITIES, key=f"manual_priority_{ticket_id}"
            )
            manual_team = team_col.selectbox("Team", ASSIGNED_TEAMS, key=f"manual_team_{ticket_id}")
            if st.button("Submit Manual Routing", type="primary", key=f"submit_manual_{ticket_id}"):
                elapsed_seconds = time.perf_counter() - st.session_state[start_key]
                st.session_state[start_key] = None
                st.session_state[result_key] = {
                    "seconds": elapsed_seconds,
                    "category": manual_category,
                    "priority": manual_priority,
                    "team": manual_team,
                }
                st.rerun()

        result = st.session_state[result_key]
        if result is not None:
            st.success(f"Manual routing took {result['seconds']:.1f} seconds.")

            match_cols = st.columns(3)
            comparisons = [
                ("Category", result["category"], detail.get("ai_category")),
                ("Priority", result["priority"], detail.get("ai_priority")),
                ("Team", result["team"], detail.get("department")),
            ]
            for col, (label, yours, ai_value) in zip(match_cols, comparisons, strict=True):
                matched = ai_value is not None and yours == ai_value
                icon = "✅" if matched else "❌"
                col.caption(f"{icon} **{label}** — you: {yours} · AI: {ai_value or '—'}")

            if st.button("Reset Manual Timer", key=f"reset_manual_{ticket_id}"):
                st.session_state[result_key] = None
                st.rerun()

            if detail.get("ai_processing_ms") is not None:
                st.write("")
                render_comparison_section(
                    [detail["ai_processing_ms"]], manual_seconds=result["seconds"]
                )


def _render_admin_ticket_detail(token: str, ticket_id: int) -> None:
    try:
        detail = api.admin_get_ticket(token, ticket_id)
    except ApiError as error:
        st.error(error.detail)
        return

    st.markdown(f'<div id="admin-ticket-detail-{ticket_id}"></div>', unsafe_allow_html=True)
    _scroll_to_anchor(f"admin-ticket-detail-{ticket_id}")

    st.divider()
    with st.container(border=True):
        st.markdown(f"### {detail['ticket_number']} — {detail['title']}")
        st.write(
            f"Requester: **{detail['user']['name']}** ({detail['user']['email']}) · "
            f"Status: **{detail['status']}** · Priority: **{detail['priority']}** · "
            f"Department: **{detail['department']}**"
        )
        render_ticket_ai_card(detail)
        if detail.get("ai_priority") and detail["priority"] != detail["ai_priority"]:
            render_priority_hint(detail["ai_priority"], detail["priority"])

        _render_manual_routing_panel(ticket_id, detail)

        action_col1, action_col2, action_col3 = st.columns(3)
        with action_col1:
            new_status = st.selectbox(
                "Status",
                TICKET_STATUSES,
                index=TICKET_STATUSES.index(detail["status"]),
                key=f"status_{ticket_id}",
            )
            if st.button("Update Status", key=f"update_status_{ticket_id}"):
                try:
                    api.admin_update_status(token, ticket_id, new_status)
                except ApiError as error:
                    st.error(error.detail)
                else:
                    st.rerun()

        with action_col2:
            new_department = st.selectbox(
                "Department",
                DEPARTMENTS,
                index=(
                    DEPARTMENTS.index(detail["department"])
                    if detail["department"] in DEPARTMENTS
                    else 0
                ),
                key=f"department_{ticket_id}",
            )
            new_priority = st.selectbox(
                "Priority",
                PRIORITIES,
                index=(
                    PRIORITIES.index(detail["priority"]) if detail["priority"] in PRIORITIES else 0
                ),
                key=f"priority_{ticket_id}",
            )
            if st.button("Reassign", key=f"reassign_{ticket_id}"):
                try:
                    api.admin_reassign(token, ticket_id, new_department, new_priority)
                except ApiError as error:
                    st.error(error.detail)
                else:
                    st.rerun()

        with action_col3:
            try:
                admins = api.admin_list_admins(token)
            except ApiError:
                admins = []
            if admins:
                admin_labels = {
                    a["id"]: f"{a['name']} ({a['department'] or 'super-admin'})" for a in admins
                }
                assignee_id = st.selectbox(
                    "Assign to",
                    list(admin_labels.keys()),
                    format_func=lambda i: admin_labels[i],
                    index=(
                        list(admin_labels.keys()).index(detail["assigned_admin_id"])
                        if detail["assigned_admin_id"] in admin_labels
                        else 0
                    ),
                    key=f"assign_{ticket_id}",
                )
                if st.button("Assign", key=f"assign_button_{ticket_id}"):
                    try:
                        api.admin_assign(token, ticket_id, assignee_id)
                    except ApiError as error:
                        st.error(error.detail)
                    else:
                        st.rerun()

        st.markdown("**Conversation**")
        sender_role = {"USER": "user", "ADMIN": "assistant", "AI": "assistant"}
        for message in detail["messages"]:
            with st.chat_message(sender_role[message["sender_type"]]):
                st.caption(message["sender_type"])
                st.write(message["message"])

        st.markdown(
            '<div class="tr-muted" style="margin-top:14px;">🕒 TIMELINE</div>',
            unsafe_allow_html=True,
        )
        render_ticket_timeline(detail["activity"])

        if detail["status"] != "CLOSED":
            reply_text = st.text_area("Reply to customer", key=f"admin_reply_{ticket_id}")
            if st.button("Send Reply", key=f"admin_send_reply_{ticket_id}"):
                if reply_text.strip():
                    try:
                        api.admin_reply(token, ticket_id, reply_text)
                    except ApiError as error:
                        st.error(error.detail)
                    else:
                        st.rerun()
        else:
            st.caption("This ticket is closed.")


def _render_admin_queue(token: str) -> None:
    with st.container(border=True):
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
        department = filter_col1.selectbox(
            "Department", ["All", *DEPARTMENTS], key="filter_department"
        )
        priority = filter_col2.selectbox("Priority", ["All", *PRIORITIES], key="filter_priority")
        status_filter = filter_col3.selectbox(
            "Status", ["All", *TICKET_STATUSES], key="filter_status"
        )
        search = filter_col4.text_input("Search", key="filter_search")

        try:
            tickets = api.admin_list_tickets(
                token,
                department=None if department == "All" else department,
                priority=None if priority == "All" else priority,
                status_filter=None if status_filter == "All" else status_filter,
                search=search or None,
            )
        except ApiError as error:
            st.error(error.detail)
            return

        st.caption(f"{len(tickets)} ticket(s)")
        for ticket in tickets:
            label = (
                f"{ticket['ticket_number']} · {ticket['title']} · {ticket['department']} · "
                f"{ticket['priority']} · {ticket['status']}"
            )
            if st.button(label, key=f"open_admin_ticket_{ticket['id']}"):
                st.session_state.selected_ticket_id = ticket["id"]

    if st.session_state.selected_ticket_id is not None:
        _render_admin_ticket_detail(token, st.session_state.selected_ticket_id)


def _render_admin_app() -> None:
    token = st.session_state.token
    is_super_admin = st.session_state.identity["department"] is None

    _render_metrics(token, is_super_admin)
    st.divider()
    _render_admin_queue(token)


# --- Entry point ----------------------------------------------------------


_render_header()

if not st.session_state.token:
    _render_landing()
elif st.session_state.identity["role"] == "USER":
    _render_customer_app()
else:
    _render_admin_app()
