"""Charting utilities for InsightOS.

Plotly charts that draw figures from KPI output DataFrames.
No calculations are performed here - charts only visualize what they
receive. Uses a rich multi-color SaaS palette with area fills,
rounded bars, and colored hover labels.
"""

import plotly.graph_objects as go

# Rich multi-color SaaS palette.
INDIGO = "#6366F1"
CYAN = "#22D3EE"
VIOLET = "#A855F7"
GREEN = "#22C55E"
AMBER = "#F59E0B"
PINK = "#EC4899"
TEAL = "#14B8A6"
RED = "#EF4444"

# Palette for multi-series charts.
SERIES_COLORS = [INDIGO, CYAN, VIOLET, GREEN, AMBER, PINK, TEAL]

# Clean dark-friendly layout shared by every figure.
DARK_LAYOUT = {
    "template": "plotly_dark",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "font": dict(family="Inter, system-ui, sans-serif", color="#F8FAFC", size=12),
    "legend": dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    "margin": dict(l=40, r=20, t=50, b=40),
}


def _apply_clean_layout(fig: go.Figure, title: str) -> go.Figure:
    """Apply the clean dark theme to a Plotly figure.

    Removes clutter (extra gridlines), keeps hover values, and uses
    consistent spacing and fonts. The title is applied separately so it
    is never passed twice to update_layout.
    """
    fig.update_layout(**DARK_LAYOUT)
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#F8FAFC"), x=0.02, xanchor="left")
    )
    fig.update_xaxes(
        showgrid=False,
        showline=False,
        zeroline=False,
        tickfont=dict(size=11, color="#94A3B8"),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.06)",
        showline=False,
        zeroline=False,
        tickfont=dict(size=11, color="#94A3B8"),
        tickformat="$,.0f",
    )
    return fig


def revenue_profit_trend_chart(trend_df) -> go.Figure:
    """Line chart of Revenue and Profit by Month with area fill under Revenue.

    Args:
        trend_df: Output of core.kpi.monthly_trend() with columns
            Month, Revenue, Profit, Orders.

    Returns:
        A plotly Figure.
    """
    fig = go.Figure()

    # Profit line (behind) - cyan with markers only, no fill.
    fig.add_trace(
        go.Scatter(
            x=trend_df["Month"],
            y=trend_df["Profit"],
            mode="lines+markers",
            name="Profit",
            line=dict(color=CYAN, width=3),
            marker=dict(size=6),
            hovertemplate="Month: %{x}<br>Profit: $%{y:,.2f}<extra></extra>",
        )
    )

    # Revenue line (front) - indigo with gradient area fill.
    fig.add_trace(
        go.Scatter(
            x=trend_df["Month"],
            y=trend_df["Revenue"],
            mode="lines+markers",
            name="Revenue",
            line=dict(color=INDIGO, width=4),
            marker=dict(size=7),
            fill="tozeroy",
            fillcolor="rgba(99, 102, 241, 0.25)",
            hovertemplate="Month: %{x}<br>Revenue: $%{y:,.2f}<extra></extra>",
        )
    )

    return _apply_clean_layout(fig, "Revenue and Profit Trend by Month")


def top_products_chart(products_df) -> go.Figure:
    """Horizontal bar chart of top products by Revenue with rounded bars.

    Args:
        products_df: Output of core.kpi.top_products() with columns
            Product, Revenue, Profit, Quantity, Margin %.

    Returns:
        A plotly Figure.
    """
    # Reverse so the highest revenue appears at the top.
    df = products_df.iloc[::-1]

    # Multi-color bars cycling through the palette.
    bar_colors = [SERIES_COLORS[i % len(SERIES_COLORS)] for i in range(len(df))]

    fig = go.Figure(
        go.Bar(
            x=df["Revenue"],
            y=df["Product"],
            orientation="h",
            marker=dict(
                color=bar_colors,
                line=dict(width=0),
            ),
            hovertemplate="Product: %{y}<br>Revenue: $%{x:,.2f}<extra></extra>",
        )
    )

    return _apply_clean_layout(fig, "Top Products by Revenue")


def regional_chart(region_df) -> go.Figure:
    """Grouped bar chart of Revenue and Profit by Region with rich colors.

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
            marker_color=INDIGO,
            hovertemplate="Region: %{x}<br>Revenue: $%{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=region_df["Region"],
            y=region_df["Profit"],
            name="Profit",
            marker_color=GREEN,
            hovertemplate="Region: %{x}<br>Profit: $%{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(barmode="group")

    return _apply_clean_layout(fig, "Revenue and Profit by Region")


def category_donut_chart(category_df) -> go.Figure:
    """Donut chart of Revenue share by Category with rich multi-color palette.

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
            marker=dict(colors=SERIES_COLORS, line=dict(color="#0B0F1A", width=2)),
            textinfo="label+percent",
            hovertemplate="Category: %{label}<br>Revenue: $%{value:,.2f}<br>Share: %{percent}<extra></extra>",
        )
    )

    fig.update_layout(
        showlegend=False,
    )
    return _apply_clean_layout(fig, "Revenue Share by Category")


def scenario_bar_chart(current: dict, scenario: dict) -> go.Figure:
    """Grouped bar chart comparing Current vs Scenario.

    Args:
        current: dict with Revenue, Cost, Profit keys (from simulate_scenario).
        scenario: dict with Revenue, Cost, Profit keys (from simulate_scenario).

    Returns:
        A plotly Figure.
    """
    metrics = ["Revenue", "Cost", "Profit"]
    current_vals = [current["Revenue"], current["Cost"], current["Profit"]]
    scenario_vals = [scenario["Revenue"], scenario["Cost"], scenario["Profit"]]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=metrics,
            y=current_vals,
            name="Current",
            marker_color=INDIGO,
            hovertemplate="Current %{x}: $%{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=metrics,
            y=scenario_vals,
            name="Scenario",
            marker_color=AMBER,
            hovertemplate="Scenario %{x}: $%{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(barmode="group")

    return _apply_clean_layout(fig, "Current vs Scenario")
