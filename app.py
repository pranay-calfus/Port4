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

import streamlit as st

from ticket_router.errors import AppError
from ticket_router.models import TicketRequest
from ticket_router.services.ticket_routing_service import route_ticket
from ticket_router.ui.components import (
    render_comparison_section,
    render_dot_row,
    render_result_card,
)
from ticket_router.ui.html import flatten_html
from ticket_router.ui.sample_tickets import load_sample_tickets
from ticket_router.ui.theme import inject_custom_theme

st.set_page_config(page_title="Smart Ticket Router", page_icon="🧭", layout="centered")
inject_custom_theme()

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
        <div style="width:36px; height:36px; border-radius:10px; background:linear-gradient(135deg,#6366f1,#a855f7);
                    display:flex; align-items:center; justify-content:center; font-weight:800; color:white;">ST</div>
        <div>
            <div style="font-weight:700; color:#f1f5f9; font-size:1rem; line-height:1.1;">Smart Ticket Router</div>
            <div style="color:#94a3b8; font-size:0.78rem;">AI-powered support triage &middot; Python + Streamlit + Groq</div>
        </div>
    </div>
    """
    ),
    unsafe_allow_html=True,
)

router_tab, demo_tab = st.tabs(["Router", "Demo Mode"])

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

        col1, col2, _ = st.columns([1, 1, 3])
        route_clicked = col1.button("Route Ticket", type="primary", use_container_width=True)
        clear_clicked = col2.button("Clear", type="secondary", use_container_width=True)

        if clear_clicked:
            st.session_state.ticket_text = ""
            st.session_state.result = None
            st.session_state.error = None
            st.rerun()

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
                    st.session_state.result = (result, elapsed_ms)
                    st.session_state.error = None
                    st.session_state.session_samples.append(elapsed_ms)
                else:
                    st.session_state.error = error
                    st.session_state.result = None

        if st.session_state.error:
            st.error(st.session_state.error)

        if st.session_state.result:
            result, elapsed_ms = st.session_state.result
            render_result_card(result, elapsed_ms)

            payload = {
                "success": True,
                "data": result.model_dump(by_alias=True),
                "processingTime": f"{elapsed_ms:.0f} ms",
            }
            st.markdown(
                '<div class="tr-muted" style="margin-top:10px;">RAW JSON RESPONSE</div>',
                unsafe_allow_html=True,
            )
            st.code(json.dumps(payload, indent=2), language="json")

    st.write("")
    with st.container(border=True):
        render_comparison_section(st.session_state.session_samples)

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

st.markdown(
    '<p style="text-align:center; color:#475569; font-size:0.75rem; margin-top:18px;">'
    "Structured JSON classification via Groq &middot; Pydantic-validated &middot; never returns malformed data</p>",
    unsafe_allow_html=True,
)
