"""InsightOS - AI Business Intelligence Platform.

Phase 1 foundation: app entry point, page configuration, header,
sidebar navigation, and placeholder KPI cards.

No analytics are implemented yet.
"""

import streamlit as st

from ui.layout import render_sidebar


def set_page_config() -> None:
    """Configure the Streamlit page: wide layout, title, and icon."""
    st.set_page_config(
        page_title="InsightOS",
        page_icon="\U0001F4CA",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def render_header() -> None:
    """Render the app header with name and tagline."""
    st.title("\U0001F4CA InsightOS")
    st.caption("Turn raw business data into decisions")
    st.divider()


def render_kpi_cards() -> None:
    """Render four placeholder KPI cards with '--' values."""
    kpis = [
        ("Revenue", "$0.00"),
        ("Profit", "$0.00"),
        ("Orders", "0"),
        ("Growth", "0%"),
    ]
    cols = st.columns(4)
    for col, (label, value) in zip(cols, kpis):
        with col:
            st.metric(label=label, value=value)


def init_session_state() -> None:
    """Initialize session state keys used for navigation tracking."""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Upload Data"


def main() -> None:
    """Run the InsightOS application."""
    set_page_config()
    init_session_state()
    render_header()

    current_page = render_sidebar()

    st.subheader(current_page)

    # Placeholder content shown until data is uploaded.
    render_kpi_cards()
    st.info("Upload your data to begin")


if __name__ == "__main__":
    main()
