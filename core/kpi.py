"""KPI calculation engine for InsightOS.

Phase 4: implements all KPI calculations using pandas on the cleaned
DataFrame. No AI, no hardcoded numbers.
"""

import pandas as pd


def _safe_divide(numerator: float, denominator: float) -> float:
    """Divide safely, returning 0.0 if denominator is zero or NaN."""
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return float(numerator) / float(denominator)


def calculate_core_kpis(df: pd.DataFrame) -> dict:
    """Calculate core KPIs from the cleaned DataFrame.

    Args:
        df: Cleaned sales DataFrame with columns Date, Product, Category,
            Region, Sales, Cost, Quantity, Customer, Profit, Month, Year.

    Returns:
        dict with: total_revenue, total_profit, profit_margin_pct,
        total_orders, avg_order_value, total_customers, total_quantity.
    """
    total_revenue = float(df["Sales"].sum())
    total_profit = float(df["Profit"].sum())
    profit_margin_pct = _safe_divide(total_profit, total_revenue) * 100
    total_orders = int(len(df))
    avg_order_value = _safe_divide(total_revenue, total_orders)
    total_customers = int(df["Customer"].nunique())
    total_quantity = int(df["Quantity"].sum())

    return {
        "total_revenue": round(total_revenue, 2),
        "total_profit": round(total_profit, 2),
        "profit_margin_pct": round(profit_margin_pct, 1),
        "total_orders": total_orders,
        "avg_order_value": round(avg_order_value, 2),
        "total_customers": total_customers,
        "total_quantity": total_quantity,
    }


def calculate_growth(df: pd.DataFrame) -> dict:
    """Calculate month-over-month revenue and profit growth.

    Compares the latest month to the previous month using the Month
    column (YYYY-MM string) which sorts correctly as text.

    Args:
        df: Cleaned sales DataFrame with Month column.

    Returns:
        dict with latest_month, previous_month, revenue_growth_pct,
        profit_growth_pct. Values are None if fewer than 2 months exist.
    """
    monthly = (
        df.groupby("Month")
        .agg(revenue=("Sales", "sum"), profit=("Profit", "sum"))
        .reset_index()
        .sort_values("Month")
    )

    if len(monthly) < 2:
        return {
            "latest_month": None,
            "previous_month": None,
            "revenue_growth_pct": None,
            "profit_growth_pct": None,
        }

    latest = monthly.iloc[-1]
    previous = monthly.iloc[-2]

    revenue_growth_pct = _safe_divide(
        latest["revenue"] - previous["revenue"], previous["revenue"]
    ) * 100
    profit_growth_pct = _safe_divide(
        latest["profit"] - previous["profit"], previous["profit"]
    ) * 100

    return {
        "latest_month": str(latest["Month"]),
        "previous_month": str(previous["Month"]),
        "revenue_growth_pct": round(revenue_growth_pct, 1),
        "profit_growth_pct": round(profit_growth_pct, 1),
    }


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Return monthly trend of revenue, profit, and orders.

    Args:
        df: Cleaned sales DataFrame.

    Returns:
        DataFrame with columns Month, Revenue, Profit, Orders, sorted
        by Month.
    """
    trend = (
        df.groupby("Month")
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"), Orders=("Sales", "size"))
        .reset_index()
        .sort_values("Month")
    )
    trend["Revenue"] = trend["Revenue"].round(2)
    trend["Profit"] = trend["Profit"].round(2)
    trend["Orders"] = trend["Orders"].astype(int)
    return trend


def _product_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Group by Product and compute Revenue, Profit, Quantity, Margin %."""
    grouped = (
        df.groupby("Product")
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"), Quantity=("Quantity", "sum"))
        .reset_index()
    )
    grouped["Margin %"] = grouped.apply(
        lambda r: round(_safe_divide(r["Profit"], r["Revenue"]) * 100, 1), axis=1
    )
    grouped["Revenue"] = grouped["Revenue"].round(2)
    grouped["Profit"] = grouped["Profit"].round(2)
    grouped["Quantity"] = grouped["Quantity"].astype(int)
    return grouped[["Product", "Revenue", "Profit", "Quantity", "Margin %"]]


def top_products(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Return top N products by revenue.

    Args:
        df: Cleaned sales DataFrame.
        n: Number of products to return.

    Returns:
        DataFrame with Product, Revenue, Profit, Quantity, Margin %.
    """
    return _product_summary(df).sort_values("Revenue", ascending=False).head(n)


def worst_products(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Return bottom N products by revenue.

    Args:
        df: Cleaned sales DataFrame.
        n: Number of products to return.

    Returns:
        DataFrame with Product, Revenue, Profit, Quantity, Margin %.
    """
    return _product_summary(df).sort_values("Revenue", ascending=True).head(n)


def regional_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Return performance aggregated by Region.

    Args:
        df: Cleaned sales DataFrame.

    Returns:
        DataFrame with Region, Revenue, Profit, Margin %, Orders,
        Revenue Share %, sorted by Revenue descending.
    """
    total_revenue = float(df["Sales"].sum())
    grouped = (
        df.groupby("Region")
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"), Orders=("Sales", "size"))
        .reset_index()
    )
    grouped["Margin %"] = grouped.apply(
        lambda r: round(_safe_divide(r["Profit"], r["Revenue"]) * 100, 1), axis=1
    )
    grouped["Revenue Share %"] = grouped["Revenue"].apply(
        lambda r: round(_safe_divide(r, total_revenue) * 100, 1)
    )
    grouped["Revenue"] = grouped["Revenue"].round(2)
    grouped["Profit"] = grouped["Profit"].round(2)
    grouped["Orders"] = grouped["Orders"].astype(int)
    return grouped.sort_values("Revenue", ascending=False)[
        ["Region", "Revenue", "Profit", "Margin %", "Orders", "Revenue Share %"]
    ]


def category_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Return performance aggregated by Category.

    Args:
        df: Cleaned sales DataFrame.

    Returns:
        DataFrame with Category, Revenue, Profit, Margin %, Orders,
        Revenue Share %, sorted by Revenue descending.
    """
    total_revenue = float(df["Sales"].sum())
    grouped = (
        df.groupby("Category")
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"), Orders=("Sales", "size"))
        .reset_index()
    )
    grouped["Margin %"] = grouped.apply(
        lambda r: round(_safe_divide(r["Profit"], r["Revenue"]) * 100, 1), axis=1
    )
    grouped["Revenue Share %"] = grouped["Revenue"].apply(
        lambda r: round(_safe_divide(r, total_revenue) * 100, 1)
    )
    grouped["Revenue"] = grouped["Revenue"].round(2)
    grouped["Profit"] = grouped["Profit"].round(2)
    grouped["Orders"] = grouped["Orders"].astype(int)
    return grouped.sort_values("Revenue", ascending=False)[
        ["Category", "Revenue", "Profit", "Margin %", "Orders", "Revenue Share %"]
    ]


def top_customers(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Return top N customers by revenue.

    Args:
        df: Cleaned sales DataFrame.
        n: Number of customers to return.

    Returns:
        DataFrame with Customer, Revenue, Profit, Orders.
    """
    grouped = (
        df.groupby("Customer")
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"), Orders=("Sales", "size"))
        .reset_index()
    )
    grouped["Revenue"] = grouped["Revenue"].round(2)
    grouped["Profit"] = grouped["Profit"].round(2)
    grouped["Orders"] = grouped["Orders"].astype(int)
    return grouped.sort_values("Revenue", ascending=False).head(n)[
        ["Customer", "Revenue", "Profit", "Orders"]
    ]
