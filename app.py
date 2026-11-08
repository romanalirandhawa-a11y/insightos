"""InsightOS - AI Business Intelligence Platform.

Phase 4: KPI engine. After data is loaded and cleaned, the Dashboard
page shows KPI cards and summary tables. The original df stays in
st.session_state["df"] and the cleaned df + report are stored in
st.session_state["df_clean"] and st.session_state["clean_report"].

Charts and AI are intentionally not implemented yet.
"""

import pandas as pd
import streamlit as st

from core.cleaner import clean_data
from core.kpi import (
    calculate_core_kpis,
    calculate_growth,
    category_performance,
    monthly_trend,
    regional_performance,
    top_customers,
    top_products,
    worst_products,
)
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


def _run_cleaning(df: pd.DataFrame) -> None:
    """Run clean_data on a DataFrame and store results in session state.

    Args:
        df: Raw validated DataFrame.
    """
    cleaned_df, report = clean_data(df)
    st.session_state["df_clean"] = cleaned_df
    st.session_state["clean_report"] = report


def render_upload_page() -> None:
    """Render the Upload Data page: uploader, cleaning, and report."""
    st.subheader("Upload Data")
    st.write(
        "Upload your sales data (CSV or Excel) to get started. "
        "Required columns: " + ", ".join(REQUIRED_COLUMNS) + "."
    )

    uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx"])
    use_sample = st.button("Use sample data")

    if use_sample:
        try:
            df = load_sample_data()
            st.session_state["df"] = df
            st.success("Sample data loaded successfully.")
            _run_cleaning(df)
        except (FileNotFoundError, ValueError) as exc:
            st.error(str(exc))

    elif uploaded_file is not None:
        try:
            df = load_data(uploaded_file)
            st.session_state["df"] = df
            st.success(f"File '{uploaded_file.name}' loaded successfully.")
            _run_cleaning(df)
        except ValueError as exc:
            st.error(str(exc))

    # Display the loaded data and cleaning report if available.
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

            # Data Cleaning Report section.
            if "clean_report" in st.session_state:
                report = st.session_state["clean_report"]
                st.subheader("Data Cleaning Report")

                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Rows before", report["rows_before"])
                with m2:
                    st.metric("Rows after", report["rows_after"])
                with m3:
                    st.metric("Duplicates removed", report["duplicates_removed"])
                with m4:
                    st.metric("Invalid dates removed", report["invalid_dates_removed"])

                m5, m6, m7, m8 = st.columns(4)
                with m5:
                    st.metric("Invalid numbers removed", report["invalid_numbers_removed"])
                with m6:
                    st.metric("Missing values filled", report["missing_values_filled"])
                with m7:
                    st.metric("Negative rows removed", report["negative_removed"])
                with m8:
                    st.metric("Final rows", len(st.session_state["df_clean"]))

                with st.expander("View cleaned data preview"):
                    st.dataframe(
                        st.session_state["df_clean"].head(10),
                        use_container_width=True,
                    )


def render_dashboard_page() -> None:
    """Render the Dashboard page with KPI cards and data tables."""
    st.subheader("Dashboard")

    if "df_clean" not in st.session_state:
        st.warning("Please upload data first.")
        return

    df = st.session_state["df_clean"]

    # Calculate KPIs.
    kpis = calculate_core_kpis(df)
    growth = calculate_growth(df)

    # Row 1: 4 core KPI cards (Revenue, Profit, Orders, Growth %).
    st.write("### Key Performance Indicators")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Revenue", f"${kpis['total_revenue']:,.2f}")
    with m2:
        st.metric("Profit", f"${kpis['total_profit']:,.2f}")
    with m3:
        st.metric("Orders", kpis["total_orders"])
    with m4:
        delta = growth["revenue_growth_pct"]
        delta_str = f"{delta:+.1f}%" if delta is not None else None
        st.metric("Growth %", delta_str, delta=delta_str)

    # Row 2: Profit Margin, Avg Order Value, Customers.
    m5, m6, m7 = st.columns(3)
    with m5:
        st.metric("Profit Margin", f"{kpis['profit_margin_pct']:.1f}%")
    with m6:
        st.metric("Avg Order Value", f"${kpis['avg_order_value']:,.2f}")
    with m7:
        st.metric("Customers", kpis["total_customers"])

    st.divider()

    # Tables section.
    st.write("### Top Products")
    st.dataframe(top_products(df), use_container_width=True)

    st.write("### Worst Products")
    st.dataframe(worst_products(df), use_container_width=True)

    st.write("### Regional Performance")
    st.dataframe(regional_performance(df), use_container_width=True)

    st.write("### Category Performance")
    st.dataframe(category_performance(df), use_container_width=True)

    st.write("### Top Customers")
    st.dataframe(top_customers(df), use_container_width=True)

    st.write("### Monthly Trend")
    st.dataframe(monthly_trend(df), use_container_width=True)


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
            "Data is loaded and cleaned. Analytics for this page are "
            "coming in a later phase."
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
    elif current_page == "Dashboard":
        render_dashboard_page()
    else:
        render_guard_page(current_page)


if __name__ == "__main__":
    main()
