"""InsightOS - AI Business Intelligence Platform.

Phase 2: data upload. Adds a file uploader, sample-data loading, and
stores the loaded DataFrame in st.session_state["df"]. Other pages
show a warning until data is uploaded.

Cleaning and analytics are intentionally not implemented yet.
"""

import streamlit as st

from core.loader import load_data, load_sample_data, validate_columns
from ui.layout import render_sidebar

REQUIRED_COLUMNS = [
    "Date",
    "Product",
    "Category",
    "Region",
    "Sales",
    "Cost",
    "Quantity",
    "Customer",
]


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


def render_upload_page() -> None:
    """Render the Upload Data page: file uploader + sample data button."""
    st.subheader("Upload Data")
    st.write(
        "Upload your sales data (CSV or Excel) to get started. "
        "Required columns: " + ", ".join(REQUIRED_COLUMNS) + "."
    )

    uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx"])
    use_sample = st.button("Use sample data")

    df = None

    if use_sample:
        try:
            df = load_sample_data()
            st.session_state["df"] = df
            st.success("Sample data loaded successfully.")
        except (FileNotFoundError, ValueError) as exc:
            st.error(str(exc))

    elif uploaded_file is not None:
        try:
            df = load_data(uploaded_file)
            st.session_state["df"] = df
            st.success(f"File '{uploaded_file.name}' loaded successfully.")
        except ValueError as exc:
            st.error(str(exc))

    # Display the loaded dataframe if available in session state.
    if "df" in st.session_state:
        df = st.session_state["df"]
        missing = validate_columns(df)

        if missing:
            st.error(
                "The uploaded data is missing required columns: "
                + ", ".join(missing)
            )
        else:
            rows, cols = df.shape
            st.info(f"Loaded {rows} rows and {cols} columns.")
            st.subheader("Preview (first 10 rows)")
            st.dataframe(df.head(10), use_container_width=True)


def render_guard_page(page_name: str) -> None:
    """Render a 'please upload data first' warning for non-upload pages.

    Args:
        page_name: The name of the current page.
    """
    st.subheader(page_name)
    if "df" not in st.session_state:
        st.warning("Please upload data first.")
    else:
        st.info(
            "Data is loaded. Analytics for this page are coming in a later phase."
        )


def main() -> None:
    """Run the InsightOS application."""
    set_page_config()
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Upload Data"

    render_header()

    current_page = render_sidebar()

    if current_page == "Upload Data":
        render_upload_page()
    else:
        render_guard_page(current_page)


if __name__ == "__main__":
    main()
