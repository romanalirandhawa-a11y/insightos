"""Layout and navigation components for InsightOS.

Sidebar navigation with four pages. Tracks the current page in
st.session_state. No analytics implemented yet.
"""

import streamlit as st

PAGES = [
    "Upload Data",
    "Dashboard",
    "AI Analyst",
    "What-If Simulator",
]


def render_sidebar() -> str:
    """Render the sidebar navigation and return the selected page.

    The current page is tracked in st.session_state["current_page"].

    Returns:
        The name of the currently selected page.
    """
    with st.sidebar:
        st.header("Navigation")
        selection = st.radio("Go to", PAGES, index=0)
        st.session_state.current_page = selection

        st.divider()
        st.caption("InsightOS v1.0 (Phase 2)")

    return st.session_state.current_page
