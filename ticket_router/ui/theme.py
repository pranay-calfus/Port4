"""Custom CSS injected once per render, in either a dark or light palette.
Streamlit's own theme (.streamlit/config.toml) sets a dark base as a
fallback for the raw Streamlit chrome; this file's CSS is what actually
determines the look for both modes; layers on the glassy cards,
light-contrast buttons/accents, and badge/progress styling that make the
app feel like a purpose-built product rather than a default Streamlit app.

Values are shared between the two palettes via plain string substitution
(not CSS custom properties) since there's no reliable way to toggle a CSS
class on Streamlit's root element from Python - the whole stylesheet is
just regenerated per mode instead.
"""

import streamlit as st

_DARK_PALETTE = {
    "PAGE_BG": "#000000",
    "CARD_BG": "rgba(255, 255, 255, 0.03)",
    "CARD_BORDER": "rgba(248, 250, 252, 0.14)",
    "FIELD_BORDER": "rgba(248, 250, 252, 0.1)",
    "HEADING": "#f8fafc",
    "BODY_TEXT": "#e2e8f0",
    "MUTED_TEXT": "#a1a1aa",
    "FAINT_TEXT": "#64748b",
    "ACCENT": "#f8fafc",
    "ACCENT_HOVER": "#ffffff",
    "ACCENT_TEXT": "#000000",
    "ACCENT_BORDER": "rgba(248, 250, 252, 0.25)",
    "ACCENT_SHADOW": "rgba(248, 250, 252, 0.18)",
    "ACCENT_SHADOW_HOVER": "rgba(248, 250, 252, 0.3)",
    "SECONDARY_BG": "rgba(248, 250, 252, 0.06)",
    "SECONDARY_BG_HOVER": "rgba(248, 250, 252, 0.14)",
    "SECONDARY_TEXT": "#f8fafc",
    "INPUT_BG": "rgba(255, 255, 255, 0.04)",
    "INPUT_BORDER": "rgba(248, 250, 252, 0.2)",
    "INPUT_TEXT": "#f1f5f9",
    "INPUT_FOCUS_BORDER": "#f8fafc",
    "INPUT_FOCUS_SHADOW": "rgba(248, 250, 252, 0.25)",
    "TAB_BG": "rgba(248, 250, 252, 0.06)",
    "TAB_TEXT": "#a1a1aa",
    "TAB_ACTIVE_BG": "#f8fafc",
    "TAB_ACTIVE_TEXT": "#000000",
    "SCROLLBAR": "rgba(248, 250, 252, 0.3)",
    "DIVIDER": "rgba(248, 250, 252, 0.1)",
    "DOT_BG": "rgba(248, 250, 252, 0.14)",
    "DOT_ACTIVE": "#f8fafc",
    "DOT_VISITED": "rgba(248, 250, 252, 0.45)",
    "TIMELINE_DOT": "#f8fafc",
    "TIMELINE_DOT_BORDER": "rgba(0, 0, 0, 0.4)",
    "TIMELINE_LINE": "rgba(248, 250, 252, 0.2)",
    "BADGE_HIGH_BG": "rgba(248, 113, 113, 0.16)",
    "BADGE_HIGH_TEXT": "#fca5a5",
    "BADGE_HIGH_BORDER": "rgba(248, 113, 113, 0.35)",
    "BADGE_MEDIUM_BG": "rgba(251, 191, 36, 0.16)",
    "BADGE_MEDIUM_TEXT": "#fcd34d",
    "BADGE_MEDIUM_BORDER": "rgba(251, 191, 36, 0.35)",
    "BADGE_LOW_BG": "rgba(52, 211, 153, 0.16)",
    "BADGE_LOW_TEXT": "#6ee7b7",
    "BADGE_LOW_BORDER": "rgba(52, 211, 153, 0.35)",
    "ACCENT_HIGH": "#f87171",
    "ACCENT_MEDIUM": "#fbbf24",
    "ACCENT_LOW": "#34d399",
    "PILL_BG": "rgba(248, 250, 252, 0.1)",
    "PILL_TEXT": "#f8fafc",
    "PILL_BORDER": "rgba(248, 250, 252, 0.3)",
    "PILL_PENDING_BG": "rgba(96, 165, 250, 0.14)",
    "PILL_PENDING_TEXT": "#93c5fd",
    "PILL_PENDING_BORDER": "rgba(96, 165, 250, 0.35)",
    "PILL_CLOSED_BG": "rgba(52, 211, 153, 0.12)",
    "PILL_CLOSED_TEXT": "#6ee7b7",
    "PILL_CLOSED_BORDER": "rgba(52, 211, 153, 0.3)",
    "LOW_CONFIDENCE_BG": "rgba(251, 191, 36, 0.1)",
    "LOW_CONFIDENCE_BORDER": "rgba(251, 191, 36, 0.3)",
    "LOW_CONFIDENCE_TEXT": "#fde68a",
}

_LIGHT_PALETTE = {
    "PAGE_BG": "#f7f8fa",
    "CARD_BG": "rgba(15, 23, 42, 0.025)",
    "CARD_BORDER": "rgba(15, 23, 42, 0.1)",
    "FIELD_BORDER": "rgba(15, 23, 42, 0.08)",
    "HEADING": "#0f172a",
    "BODY_TEXT": "#334155",
    "MUTED_TEXT": "#64748b",
    "FAINT_TEXT": "#94a3b8",
    "ACCENT": "#0f172a",
    "ACCENT_HOVER": "#1e293b",
    "ACCENT_TEXT": "#ffffff",
    "ACCENT_BORDER": "rgba(15, 23, 42, 0.25)",
    "ACCENT_SHADOW": "rgba(15, 23, 42, 0.12)",
    "ACCENT_SHADOW_HOVER": "rgba(15, 23, 42, 0.18)",
    "SECONDARY_BG": "rgba(15, 23, 42, 0.05)",
    "SECONDARY_BG_HOVER": "rgba(15, 23, 42, 0.09)",
    "SECONDARY_TEXT": "#0f172a",
    "INPUT_BG": "#ffffff",
    "INPUT_BORDER": "rgba(15, 23, 42, 0.15)",
    "INPUT_TEXT": "#0f172a",
    "INPUT_FOCUS_BORDER": "#0f172a",
    "INPUT_FOCUS_SHADOW": "rgba(15, 23, 42, 0.15)",
    "TAB_BG": "rgba(15, 23, 42, 0.05)",
    "TAB_TEXT": "#64748b",
    "TAB_ACTIVE_BG": "#0f172a",
    "TAB_ACTIVE_TEXT": "#ffffff",
    "SCROLLBAR": "rgba(15, 23, 42, 0.25)",
    "DIVIDER": "rgba(15, 23, 42, 0.1)",
    "DOT_BG": "rgba(15, 23, 42, 0.1)",
    "DOT_ACTIVE": "#0f172a",
    "DOT_VISITED": "rgba(15, 23, 42, 0.4)",
    "TIMELINE_DOT": "#0f172a",
    "TIMELINE_DOT_BORDER": "rgba(255, 255, 255, 0.6)",
    "TIMELINE_LINE": "rgba(15, 23, 42, 0.16)",
    "BADGE_HIGH_BG": "rgba(220, 38, 38, 0.1)",
    "BADGE_HIGH_TEXT": "#b91c1c",
    "BADGE_HIGH_BORDER": "rgba(220, 38, 38, 0.3)",
    "BADGE_MEDIUM_BG": "rgba(217, 119, 6, 0.1)",
    "BADGE_MEDIUM_TEXT": "#92400e",
    "BADGE_MEDIUM_BORDER": "rgba(217, 119, 6, 0.3)",
    "BADGE_LOW_BG": "rgba(5, 150, 105, 0.1)",
    "BADGE_LOW_TEXT": "#047857",
    "BADGE_LOW_BORDER": "rgba(5, 150, 105, 0.3)",
    "ACCENT_HIGH": "#dc2626",
    "ACCENT_MEDIUM": "#d97706",
    "ACCENT_LOW": "#059669",
    "PILL_BG": "rgba(15, 23, 42, 0.08)",
    "PILL_TEXT": "#0f172a",
    "PILL_BORDER": "rgba(15, 23, 42, 0.25)",
    "PILL_PENDING_BG": "rgba(37, 99, 235, 0.1)",
    "PILL_PENDING_TEXT": "#1d4ed8",
    "PILL_PENDING_BORDER": "rgba(37, 99, 235, 0.3)",
    "PILL_CLOSED_BG": "rgba(5, 150, 105, 0.1)",
    "PILL_CLOSED_TEXT": "#047857",
    "PILL_CLOSED_BORDER": "rgba(5, 150, 105, 0.3)",
    "LOW_CONFIDENCE_BG": "rgba(217, 119, 6, 0.08)",
    "LOW_CONFIDENCE_BORDER": "rgba(217, 119, 6, 0.3)",
    "LOW_CONFIDENCE_TEXT": "#92400e",
}

# Template uses __TOKEN__ placeholders (never colliding with CSS syntax)
# rather than str.format()/f-strings, since the stylesheet is full of
# literal { } braces that would otherwise all need escaping.
_CSS_TEMPLATE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', ui-sans-serif, system-ui, sans-serif;
}

.stApp {
    background: __PAGE_BG__;
}

header[data-testid="stHeader"] {
    background: transparent;
}

section.main > div {
    padding-top: 1.5rem;
    max-width: 1000px;
}

/* Card containers (st.container(border=True)) - the one wrapper used
   throughout the app to give a section a subtle card treatment. */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: __CARD_BG__;
    border: 1px solid __CARD_BORDER__;
    border-radius: 16px;
    backdrop-filter: blur(10px);
}

div[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius: 16px;
}

/* Headings */
h1, h2, h3 {
    color: __HEADING__ !important;
    font-weight: 700 !important;
}

p, span, label, .stMarkdown {
    color: __BODY_TEXT__;
}

.tr-muted {
    color: __MUTED_TEXT__;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}

.tr-subtitle {
    color: __MUTED_TEXT__;
    font-size: 0.92rem;
}

/* Buttons - high-contrast against the page background.
   Streamlit has changed its button markup across versions - older
   releases put a `kind="primary"/"secondary"` attribute directly on the
   <button> element; 1.5x+ instead renders `data-testid="stBaseButton-
   primary"/"stBaseButton-secondary"` on a wrapping element and may not set
   `kind` at all. Both selector forms are kept so this survives either. */
div.stButton > button, div.stFormSubmitButton > button,
[data-testid^="stBaseButton-"] {
    border-radius: 10px;
    font-weight: 600;
    transition: all 0.15s ease;
    border: 1px solid __ACCENT_BORDER__;
}

div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: __ACCENT__;
    color: __ACCENT_TEXT__;
    border: none;
    box-shadow: 0 4px 18px __ACCENT_SHADOW__;
}

div.stButton > button[kind="primary"]:hover, div.stFormSubmitButton > button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    background: __ACCENT_HOVER__;
    box-shadow: 0 6px 22px __ACCENT_SHADOW_HOVER__;
    transform: translateY(-1px);
}

div.stButton > button[kind="secondary"], [data-testid="stBaseButton-secondary"] {
    background: __SECONDARY_BG__;
    color: __SECONDARY_TEXT__;
}

div.stButton > button[kind="secondary"]:hover, [data-testid="stBaseButton-secondary"]:hover {
    background: __SECONDARY_BG_HOVER__;
    border-color: __ACCENT_BORDER__;
}

/* Streamlit wraps the button label in its own <p>/<div>, which the global
   `p, span { color: ... }` rule above otherwise overrides (same specificity
   as an ancestor override doesn't win against a direct element rule) -
   washing out the label against the "primary" button's own background. */
div.stButton > button[kind="primary"] p,
div.stButton > button[kind="primary"] span,
div.stButton > button[kind="primary"] div,
div.stFormSubmitButton > button[kind="primary"] p,
div.stFormSubmitButton > button[kind="primary"] span,
div.stFormSubmitButton > button[kind="primary"] div,
[data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-primary"] span,
[data-testid="stBaseButton-primary"] div {
    color: __ACCENT_TEXT__ !important;
}

div.stButton > button[kind="secondary"] p,
div.stButton > button[kind="secondary"] span,
div.stButton > button[kind="secondary"] div,
div.stFormSubmitButton > button[kind="secondary"] p,
div.stFormSubmitButton > button[kind="secondary"] span,
div.stFormSubmitButton > button[kind="secondary"] div,
[data-testid="stBaseButton-secondary"] p,
[data-testid="stBaseButton-secondary"] span,
[data-testid="stBaseButton-secondary"] div {
    color: __SECONDARY_TEXT__ !important;
}

/* Profile avatar button (st.popover) - a small round initials badge
   instead of a normal rectangular button. */
div[class*="st-key-profile_popover"] button {
    border-radius: 999px !important;
    width: 42px;
    height: 42px;
    padding: 0 !important;
    font-weight: 700;
    background: __ACCENT__ !important;
    color: __ACCENT_TEXT__ !important;
    border: none !important;
}

div[class*="st-key-profile_popover"] button p {
    color: __ACCENT_TEXT__ !important;
    font-weight: 700 !important;
}

/* Theme toggle button - understated, not styled like a call-to-action. */
div[class*="st-key-theme_toggle_button"] button {
    border-radius: 999px !important;
    background: __SECONDARY_BG__ !important;
    border: 1px solid __CARD_BORDER__ !important;
}

/* Text inputs / textareas / selects */
.stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
    background: __INPUT_BG__ !important;
    border: 1px solid __INPUT_BORDER__ !important;
    border-radius: 10px !important;
    color: __INPUT_TEXT__ !important;
}

.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: __INPUT_FOCUS_BORDER__ !important;
    box-shadow: 0 0 0 2px __INPUT_FOCUS_SHADOW__ !important;
}

/* Tabs styled as a segmented control */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: __TAB_BG__;
    border-radius: 999px;
    padding: 4px;
    width: fit-content;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 999px;
    padding: 6px 18px;
    color: __TAB_TEXT__;
    font-weight: 600;
    background: transparent;
}

.stTabs [data-baseweb="tab"] p {
    font-weight: 600;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: __TAB_ACTIVE_BG__;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] p {
    color: __TAB_ACTIVE_TEXT__ !important;
}

.stTabs [data-baseweb="tab-highlight"] {
    background: transparent;
}

.stTabs [data-baseweb="tab-border"] {
    display: none;
}

/* Progress bar (confidence bar) */
div[data-testid="stProgress"] div[role="progressbar"] > div {
    background: __ACCENT__;
}

/* Badges */
.tr-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 700;
    border: 1px solid transparent;
}

.tr-badge-high { background: __BADGE_HIGH_BG__; color: __BADGE_HIGH_TEXT__; border-color: __BADGE_HIGH_BORDER__; }
.tr-badge-medium { background: __BADGE_MEDIUM_BG__; color: __BADGE_MEDIUM_TEXT__; border-color: __BADGE_MEDIUM_BORDER__; }
.tr-badge-low { background: __BADGE_LOW_BG__; color: __BADGE_LOW_TEXT__; border-color: __BADGE_LOW_BORDER__; }

.tr-accent-high { border-left: 3px solid __ACCENT_HIGH__; }
.tr-accent-medium { border-left: 3px solid __ACCENT_MEDIUM__; }
.tr-accent-low { border-left: 3px solid __ACCENT_LOW__; }

.tr-field {
    background: __CARD_BG__;
    border: 1px solid __FIELD_BORDER__;
    border-radius: 12px;
    padding: 12px 14px;
    margin-bottom: 10px;
}

.tr-field-value {
    color: __INPUT_TEXT__;
    font-weight: 600;
    font-size: 0.95rem;
    margin-top: 2px;
}

.tr-low-confidence {
    background: __LOW_CONFIDENCE_BG__;
    border: 1px solid __LOW_CONFIDENCE_BORDER__;
    border-radius: 12px;
    padding: 10px 14px;
    color: __LOW_CONFIDENCE_TEXT__;
    font-size: 0.85rem;
    margin-bottom: 10px;
}

.tr-stat {
    background: __CARD_BG__;
    border: 1px solid __FIELD_BORDER__;
    border-radius: 12px;
    padding: 14px;
    text-align: center;
}

.tr-stat-value {
    font-size: 1.3rem;
    font-weight: 800;
    color: __HEADING__;
}

.tr-stat-label {
    color: __MUTED_TEXT__;
    font-size: 0.78rem;
    margin-top: 2px;
}

.tr-pill {
    display: inline-block;
    background: __PILL_BG__;
    color: __PILL_TEXT__;
    border: 1px solid __PILL_BORDER__;
    border-radius: 999px;
    padding: 2px 12px;
    font-size: 0.76rem;
    font-weight: 600;
}

/* Status pills - a deliberately different hue from the priority badges
   above so the two scales never get visually confused. */
.tr-pill-pending {
    display: inline-block;
    background: __PILL_PENDING_BG__;
    color: __PILL_PENDING_TEXT__;
    border: 1px solid __PILL_PENDING_BORDER__;
    border-radius: 999px;
    padding: 2px 12px;
    font-size: 0.76rem;
    font-weight: 600;
}

.tr-pill-closed {
    display: inline-block;
    background: __PILL_CLOSED_BG__;
    color: __PILL_CLOSED_TEXT__;
    border: 1px solid __PILL_CLOSED_BORDER__;
    border-radius: 999px;
    padding: 2px 12px;
    font-size: 0.76rem;
    font-weight: 600;
}

/* Scrollbars */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background-color: __SCROLLBAR__; border-radius: 999px; }

/* Progress dots (sample-ticket / demo-style steppers) */
.tr-dot-row { display: flex; gap: 6px; margin-bottom: 14px; }
.tr-dot { height: 6px; flex: 1; border-radius: 999px; background: __DOT_BG__; }
.tr-dot-active { background: __DOT_ACTIVE__; }
.tr-dot-visited { background: __DOT_VISITED__; }

/* Ticket activity timeline - a connected vertical stepper instead of a
   flat list of captions, so the ticket's stages actually read as stages. */
.tr-timeline {
    margin: 6px 0 4px;
}

.tr-timeline-item {
    display: flex;
    gap: 14px;
}

.tr-timeline-marker {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 14px;
}

.tr-timeline-dot {
    width: 12px;
    height: 12px;
    border-radius: 999px;
    background: __TIMELINE_DOT__;
    border: 2px solid __TIMELINE_DOT_BORDER__;
    flex-shrink: 0;
    margin-top: 3px;
}

.tr-timeline-line {
    width: 2px;
    flex: 1;
    background: __TIMELINE_LINE__;
    margin: 2px 0;
}

.tr-timeline-content {
    flex: 1;
    padding-bottom: 18px;
}

.tr-timeline-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 10px;
    flex-wrap: wrap;
}

.tr-timeline-event {
    font-weight: 700;
    color: __HEADING__;
    font-size: 0.9rem;
}

.tr-timeline-time {
    color: __FAINT_TEXT__;
    font-size: 0.74rem;
    white-space: nowrap;
}

.tr-timeline-detail {
    color: __MUTED_TEXT__;
    font-size: 0.84rem;
    margin-top: 2px;
}

/* Metric tiles (st.metric) - give the admin dashboard's counts the same
   card treatment as .tr-stat instead of floating bare numbers. */
div[data-testid="stMetric"] {
    background: __CARD_BG__;
    border: 1px solid __FIELD_BORDER__;
    border-radius: 12px;
    padding: 14px 16px 10px;
}

div[data-testid="stMetricLabel"] {
    color: __MUTED_TEXT__;
}

/* Stat-tile accents (admin dashboard) - a colored top edge on the Pending/
   Closed counts, reusing the exact same blue/green as the status pills so
   the two read as one consistent language rather than two palettes. */
div[class*="st-key-admin-stat-pending"] div[data-testid="stMetric"],
div[class*="st-key-admin-team-stat-pending"] div[data-testid="stMetric"] {
    border-top: 3px solid __PILL_PENDING_BORDER__;
}

div[class*="st-key-admin-stat-closed"] div[data-testid="stMetric"],
div[class*="st-key-admin-team-stat-closed"] div[data-testid="stMetric"] {
    border-top: 3px solid __PILL_CLOSED_BORDER__;
}

/* Interactive tables (admin "all tickets" overview) */
div[data-testid="stDataFrame"] {
    border: 1px solid __FIELD_BORDER__;
    border-radius: 12px;
    overflow: hidden;
}

/* st.divider() */
hr {
    border-color: __DIVIDER__;
}
</style>
"""


def _build_css(mode: str) -> str:
    palette = _LIGHT_PALETTE if mode == "light" else _DARK_PALETTE
    css = _CSS_TEMPLATE
    for token, value in palette.items():
        css = css.replace(f"__{token}__", value)
    return css


def inject_custom_theme(mode: str = "dark") -> None:
    st.markdown(_build_css(mode), unsafe_allow_html=True)
