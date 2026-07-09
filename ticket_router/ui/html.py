def flatten_html(markup: str) -> str:
    """Strips per-line leading whitespace from an HTML block.

    Markdown treats any line indented 4+ spaces as a code block, and
    Python triple-quoted strings built inside indented code naturally pick
    up that much indentation - without this, st.markdown(html,
    unsafe_allow_html=True) silently renders the raw tags as a code block
    instead of HTML.
    """
    return "\n".join(line.strip() for line in markup.strip().splitlines())
