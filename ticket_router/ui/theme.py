"""Custom dark, sleek CSS injected once at app startup. Streamlit's own
dark theme (.streamlit/config.toml) gets the base colors right; this file
layers on the glassy cards, gradient accents, and badge/progress styling
that make the app feel like a purpose-built product rather than a default
Streamlit app.
"""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', ui-sans-serif, system-ui, sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 15% 0%, rgba(129, 140, 248, 0.16), transparent 45%),
        radial-gradient(circle at 85% 15%, rgba(192, 132, 252, 0.14), transparent 45%),
        radial-gradient(circle at 50% 100%, rgba(244, 114, 182, 0.08), transparent 55%),
        #0b0f1a;
}

header[data-testid="stHeader"] {
    background: transparent;
}

section.main > div {
    padding-top: 1.5rem;
    max-width: 880px;
}

/* Card containers (st.container(border=True)) */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(20, 26, 43, 0.72);
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 16px;
    backdrop-filter: blur(10px);
}

div[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius: 16px;
}

/* Headings */
h1, h2, h3 {
    color: #f1f5f9 !important;
    font-weight: 700 !important;
}

p, span, label, .stMarkdown {
    color: #cbd5e1;
}

.tr-muted {
    color: #94a3b8;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}

.tr-subtitle {
    color: #94a3b8;
    font-size: 0.92rem;
}

/* Buttons */
div.stButton > button, div.stFormSubmitButton > button {
    border-radius: 10px;
    font-weight: 600;
    transition: all 0.15s ease;
    border: 1px solid rgba(148, 163, 184, 0.18);
}

div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #a855f7);
    border: none;
    box-shadow: 0 4px 18px rgba(99, 102, 241, 0.35);
}

div.stButton > button[kind="primary"]:hover, div.stFormSubmitButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 22px rgba(168, 85, 247, 0.45);
    transform: translateY(-1px);
}

div.stButton > button[kind="secondary"] {
    background: rgba(148, 163, 184, 0.08);
    color: #e2e8f0;
}

div.stButton > button[kind="secondary"]:hover {
    background: rgba(148, 163, 184, 0.16);
    border-color: rgba(148, 163, 184, 0.3);
}

/* Text inputs / textareas / selects */
.stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
    background: rgba(11, 15, 26, 0.6) !important;
    border: 1px solid rgba(148, 163, 184, 0.2) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
}

.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #818cf8 !important;
    box-shadow: 0 0 0 2px rgba(129, 140, 248, 0.25) !important;
}

/* Tabs styled as a segmented control */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(148, 163, 184, 0.08);
    border-radius: 999px;
    padding: 4px;
    width: fit-content;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 999px;
    padding: 6px 18px;
    color: #94a3b8;
    font-weight: 600;
    background: transparent;
}

.stTabs [data-baseweb="tab"] p {
    font-weight: 600;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: #ffffff;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] p {
    color: #4338ca !important;
}

.stTabs [data-baseweb="tab-highlight"] {
    background: transparent;
}

.stTabs [data-baseweb="tab-border"] {
    display: none;
}

/* Progress bar (confidence bar) */
div[data-testid="stProgress"] div[role="progressbar"] > div {
    background: linear-gradient(90deg, #6366f1, #a855f7);
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

.tr-badge-high { background: rgba(248, 113, 113, 0.16); color: #fca5a5; border-color: rgba(248, 113, 113, 0.35); }
.tr-badge-medium { background: rgba(251, 191, 36, 0.16); color: #fcd34d; border-color: rgba(251, 191, 36, 0.35); }
.tr-badge-low { background: rgba(52, 211, 153, 0.16); color: #6ee7b7; border-color: rgba(52, 211, 153, 0.35); }

.tr-accent-high { border-left: 3px solid #f87171; }
.tr-accent-medium { border-left: 3px solid #fbbf24; }
.tr-accent-low { border-left: 3px solid #34d399; }

.tr-field {
    background: rgba(11, 15, 26, 0.55);
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 12px;
    padding: 12px 14px;
    margin-bottom: 10px;
}

.tr-field-value {
    color: #f1f5f9;
    font-weight: 600;
    font-size: 0.95rem;
    margin-top: 2px;
}

.tr-low-confidence {
    background: rgba(251, 191, 36, 0.1);
    border: 1px solid rgba(251, 191, 36, 0.3);
    border-radius: 12px;
    padding: 10px 14px;
    color: #fde68a;
    font-size: 0.85rem;
    margin-bottom: 10px;
}

.tr-stat {
    background: rgba(11, 15, 26, 0.55);
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 12px;
    padding: 14px;
    text-align: center;
}

.tr-stat-value {
    font-size: 1.3rem;
    font-weight: 800;
}

.tr-stat-label {
    color: #94a3b8;
    font-size: 0.78rem;
    margin-top: 2px;
}

.tr-pill {
    display: inline-block;
    background: rgba(52, 211, 153, 0.14);
    color: #6ee7b7;
    border: 1px solid rgba(52, 211, 153, 0.3);
    border-radius: 999px;
    padding: 2px 12px;
    font-size: 0.76rem;
    font-weight: 600;
}

/* Scrollbars */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background-color: rgba(148, 163, 184, 0.35); border-radius: 999px; }

/* Progress dots (demo mode ticket stepper) */
.tr-dot-row { display: flex; gap: 6px; margin-bottom: 14px; }
.tr-dot { height: 6px; flex: 1; border-radius: 999px; background: rgba(148, 163, 184, 0.18); }
.tr-dot-active { background: linear-gradient(135deg, #6366f1, #a855f7); }
.tr-dot-visited { background: rgba(129, 140, 248, 0.45); }
</style>
"""


def inject_custom_theme() -> None:
    import streamlit as st

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
