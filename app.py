"""InsightOS - AI Business Intelligence Platform.

Phase 6: AI Analyst. After data is loaded and cleaned, the AI Analyst
page answers business questions using facts from pandas KPI results
(the AI never calculates numbers). The Dashboard page shows KPI cards,
charts, and summary tables using filtered data. The original df stays
in st.session_state["df"] and the cleaned df + report are stored in
st.session_state["df_clean"] and st.session_state["clean_report"].

What-If is intentionally not implemented yet.
"""

import pandas as pd
import streamlit as st

from core.ai_analyst import ask_analyst_stream, build_context, get_provider_info
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
from ui.charts import (
    category_donut_chart,
    regional_chart,
    revenue_profit_trend_chart,
    top_products_chart,
)
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
    """Render the Dashboard page with filters, KPI cards, and charts.

    Filters (Date range, Region, Category) are applied to the cleaned
    data. All KPI cards, charts, and tables use the filtered data.
    """
    st.subheader("Dashboard")

    if "df_clean" not in st.session_state:
        st.warning("Please upload data first.")
        return

    df_full = st.session_state["df_clean"]

    # ---- Sidebar filters ----
    with st.sidebar:
        st.write("### Filters")

        # Date range filter.
        min_date = df_full["Date"].min().date()
        max_date = df_full["Date"].max().date()
        date_range = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        # Region multiselect.
        all_regions = sorted(df_full["Region"].unique().tolist())
        selected_regions = st.multiselect(
            "Region",
            options=all_regions,
            default=all_regions,
        )

        # Category multiselect.
        all_categories = sorted(df_full["Category"].unique().tolist())
        selected_categories = st.multiselect(
            "Category",
            options=all_categories,
            default=all_categories,
        )

    # ---- Apply filters to build the filtered DataFrame ----
    filtered = df_full.copy()

    if date_range and len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        filtered = filtered[
            (filtered["Date"] >= start_date) & (filtered["Date"] <= end_date)
        ]

    if selected_regions:
        filtered = filtered[filtered["Region"].isin(selected_regions)]

    if selected_categories:
        filtered = filtered[filtered["Category"].isin(selected_categories)]

    # Guard: zero rows after filtering.
    if filtered.empty:
        st.warning("No data matches the selected filters. Try adjusting them.")
        return

    # ---- Calculate KPIs on filtered data ----
    kpis = calculate_core_kpis(filtered)
    growth = calculate_growth(filtered)

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
        st.metric("Growth %", delta_str if delta_str else "N/A", delta=delta_str)

    # Row 2: Profit Margin, Avg Order Value, Customers.
    m5, m6, m7 = st.columns(3)
    with m5:
        st.metric("Profit Margin", f"{kpis['profit_margin_pct']:.1f}%")
    with m6:
        st.metric("Avg Order Value", f"${kpis['avg_order_value']:,.2f}")
    with m7:
        st.metric("Customers", kpis["total_customers"])

    st.divider()

    # ---- Trend chart (full width) ----
    st.write("### Revenue & Profit Trend")
    trend_df = monthly_trend(filtered)
    fig_trend = revenue_profit_trend_chart(trend_df)
    st.plotly_chart(fig_trend, use_container_width=True)

    # ---- Two columns: top products chart | regional chart ----
    col_left, col_right = st.columns(2)
    with col_left:
        st.write("### Top Products")
        top_df = top_products(filtered)
        fig_products = top_products_chart(top_df)
        st.plotly_chart(fig_products, use_container_width=True)

    with col_right:
        st.write("### Regional Performance")
        region_df = regional_performance(filtered)
        fig_region = regional_chart(region_df)
        st.plotly_chart(fig_region, use_container_width=True)

    # ---- Category donut next to top customers table ----
    col_cat, col_cust = st.columns(2)
    with col_cat:
        st.write("### Revenue Share by Category")
        cat_df = category_performance(filtered)
        fig_cat = category_donut_chart(cat_df)
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_cust:
        st.write("### Top Customers")
        st.dataframe(top_customers(filtered), use_container_width=True)

    # ---- Detailed tables inside expanders ----
    with st.expander("View detailed tables"):
        st.write("#### Top Products")
        st.dataframe(top_products(filtered), use_container_width=True)

        st.write("#### Worst Products")
        st.dataframe(worst_products(filtered), use_container_width=True)

        st.write("#### Regional Performance")
        st.dataframe(regional_performance(filtered), use_container_width=True)

        st.write("#### Category Performance")
        st.dataframe(category_performance(filtered), use_container_width=True)

        st.write("#### Monthly Trend")
        st.dataframe(trend_df, use_container_width=True)


def render_ai_analyst_page() -> None:
    """Render the AI Analyst page: Q&A over the cleaned data.

    Shows example question buttons plus a chat input. Chat history is
    kept in st.session_state and rendered with st.chat_message.
    Uses the full cleaned data (df_clean), not dashboard filters.
    """
    st.subheader("AI Analyst")

    if "df_clean" not in st.session_state:
        st.warning("Please upload data first.")
        return

    df = st.session_state["df_clean"]

    # Build the factual context once and cache it in session state.
    if "ai_context" not in st.session_state:
        with st.spinner("Analyzing your data..."):
            st.session_state["ai_context"] = build_context(df)
    context = st.session_state["ai_context"]

    # Expander so the user can verify the exact facts sent to the AI.
    with st.expander("Facts sent to AI"):
        st.text(context)

    # Show which provider and model is answering.
    provider_name, model_name = get_provider_info()
    st.caption(f"AI Analyst: {provider_name} • {model_name}")

    # Initialize chat history.
    if "ai_messages" not in st.session_state:
        st.session_state["ai_messages"] = []

    # Example question buttons.
    st.write("### Try these questions")
    example_questions = [
        "Which region needs attention?",
        "Why did profit change last month?",
        "Which products should we focus on?",
        "Give me a summary of business performance",
    ]
    cols = st.columns(2)
    clicked_example = None
    for i, q in enumerate(example_questions):
        with cols[i % 2]:
            if st.button(q, key=f"example_{i}"):
                clicked_example = q

    st.divider()

    # Chat history.
    for msg in st.session_state["ai_messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Determine the question to answer (from button or chat input).
    question = clicked_example
    if prompt := st.chat_input("Ask the AI Analyst about your business data"):
        question = prompt

    if question:
        # Show user message.
        st.session_state["ai_messages"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        # Stream the assistant answer.
        with st.chat_message("assistant"):
            full_answer = st.write_stream(
                ask_analyst_stream(question, context, st.session_state["ai_messages"][:-1])
            )
        st.session_state["ai_messages"].append({"role": "assistant", "content": full_answer})


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
    elif current_page == "AI Analyst":
        render_ai_analyst_page()
    else:
        render_guard_page(current_page)


if __name__ == "__main__":
    main()
