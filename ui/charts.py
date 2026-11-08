"""Charting utilities for InsightOS.

Phase 5: Plotly charts that draw figures from KPI output DataFrames.
No calculations are performed here - charts only visualize what they
receive. Uses a dark-friendly theme to match the app.
"""

import plotly.graph_objects as go
import plotly.express as px

# App's primary purple, used as the accent color across charts.
PRIMARY_COLOR = "#7C3AED"

# Common dark-friendly layout overrides applied to every figure.
DARK_LAYOUT = {
    "template": "plotly_dark",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "font": dict(color="#FAFAFA"),
    "legend": dict(bgcolor="rgba(0,0,0,0)"),
    "margin": dict(l=40, r=20, t=40, b=40),
}


def _apply_dark_layout(fig: go.Figure) -> go.Figure:
    """Apply the app's dark theme to a Plotly figure."""
    fig.update_layout(**DARK_LAYOUT)
    return fig


def revenue_profit_trend_chart(trend_df) -> go.Figure:
    """Line chart of Revenue and Profit by Month with markers.

    Args:
        trend_df: Output of core.kpi.monthly_trend() with columns
            Month, Revenue, Profit, Orders.

    Returns:
        A plotly Figure.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=trend_df["Month"],
            y=trend_df["Revenue"],
            mode="lines+markers",
            name="Revenue",
            line=dict(color=PRIMARY_COLOR, width=3),
            marker=dict(size=8),
            hovertemplate="Month: %{x}<br>Revenue: $%{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=trend_df["Month"],
            y=trend_df["Profit"],
            mode="lines+markers",
            name="Profit",
            line=dict(color="#22C55E", width=3),
            marker=dict(size=8),
            hovertemplate="Month: %{x}<br>Profit: $%{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Revenue & Profit Trend by Month",
        xaxis_title="Month",
        yaxis_title="Amount ($)",
        yaxis=dict(tickformat="$,.0f"),
    )
    return _apply_dark_layout(fig)


def top_products_chart(products_df) -> go.Figure:
    """Horizontal bar chart of top products by Revenue.

    Args:
        products_df: Output of core.kpi.top_products() with columns
            Product, Revenue, Profit, Quantity, Margin %.

    Returns:
        A plotly Figure.
    """
    # Reverse so the highest revenue appears at the top.
    df = products_df.iloc[::-1]

    fig = go.Figure(
        go.Bar(
            x=df["Revenue"],
            y=df["Product"],
            orientation="h",
            marker_color=PRIMARY_COLOR,
            hovertemplate="Product: %{y}<br>Revenue: $%{x:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Top Products by Revenue",
        xaxis_title="Revenue ($)",
        yaxis_title="Product",
        xaxis=dict(tickformat="$,.0f"),
    )
    return _apply_dark_layout(fig)


def regional_chart(region_df) -> go.Figure:
    """Grouped bar chart of Revenue and Profit by Region.

    Args:
        region_df: Output of core.kpi.regional_performance() with columns
            Region, Revenue, Profit, ...

    Returns:
        A plotly Figure.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=region_df["Region"],
            y=region_df["Revenue"],
            name="Revenue",
            marker_color=PRIMARY_COLOR,
            hovertemplate="Region: %{x}<br>Revenue: $%{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=region_df["Region"],
            y=region_df["Profit"],
            name="Profit",
            marker_color="#22C55E",
            hovertemplate="Region: %{x}<br>Profit: $%{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Revenue & Profit by Region",
        xaxis_title="Region",
        yaxis_title="Amount ($)",
        barmode="group",
        yaxis=dict(tickformat="$,.0f"),
    )
    return _apply_dark_layout(fig)


def category_donut_chart(category_df) -> go.Figure:
    """Donut chart of Revenue share by Category.

    Args:
        category_df: Output of core.kpi.category_performance() with
            columns Category, Revenue, ...

    Returns:
        A plotly Figure.
    """
    fig = go.Figure(
        go.Pie(
            labels=category_df["Category"],
            values=category_df["Revenue"],
            hole=0.5,
            marker=dict(colors=[PRIMARY_COLOR, "#22C55E", "#F59E0B", "#EF4444", "#3B82F6"]),
            textinfo="label+percent",
            hovertemplate="Category: %{label}<br>Revenue: $%{value:,.2f}<br>Share: %{percent}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Revenue Share by Category",
        showlegend=False,
    )
    return _apply_dark_layout(fig)
