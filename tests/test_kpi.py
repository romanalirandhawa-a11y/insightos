"""Tests for the InsightOS KPI engine (core/kpi.py).

Uses a tiny hand-made DataFrame where every expected answer can be
verified by hand. Run with: pytest tests/test_kpi.py
"""

import pandas as pd

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


def _make_df() -> pd.DataFrame:
    """Build a small cleaned DataFrame with hand-verifiable values.

    Rows:
      1. 2026-01-15 | A | Electronics | North | Sales 100 | Cost 40  | Qty 2 | C1
      2. 2026-01-20 | B | Electronics | South | Sales 200 | Cost 100 | Qty 3 | C2
      3. 2026-02-10 | A | Electronics | North | Sales 150 | Cost 60  | Qty 1 | C1
      4. 2026-02-15 | C | Clothing    | East  | Sales 300 | Cost 200 | Qty 5 | C3

    Profit = Sales - Cost:
      1. 60   2. 100   3. 90   4. 100

    Month (YYYY-MM): rows 1-2 -> 2026-01, rows 3-4 -> 2026-02
    """
    data = {
        "Date": [
            "2026-01-15",
            "2026-01-20",
            "2026-02-10",
            "2026-02-15",
        ],
        "Product": ["A", "B", "A", "C"],
        "Category": ["Electronics", "Electronics", "Electronics", "Clothing"],
        "Region": ["North", "South", "North", "East"],
        "Sales": [100.0, 200.0, 150.0, 300.0],
        "Cost": [40.0, 100.0, 60.0, 200.0],
        "Quantity": [2, 3, 1, 5],
        "Customer": ["C1", "C2", "C1", "C3"],
        "Profit": [60.0, 100.0, 90.0, 100.0],
        "Month": ["2026-01", "2026-01", "2026-02", "2026-02"],
        "Year": [2026, 2026, 2026, 2026],
    }
    return pd.DataFrame(data)


def test_calculate_core_kpis():
    df = _make_df()
    kpis = calculate_core_kpis(df)

    # total_revenue = 100 + 200 + 150 + 300 = 750
    assert kpis["total_revenue"] == 750.0
    # total_profit = 60 + 100 + 90 + 100 = 350
    assert kpis["total_profit"] == 350.0
    # profit_margin_pct = 350 / 750 * 100 = 46.666... -> 46.7
    assert kpis["profit_margin_pct"] == 46.7
    # total_orders = 4 rows
    assert kpis["total_orders"] == 4
    # avg_order_value = 750 / 4 = 187.5
    assert kpis["avg_order_value"] == 187.5
    # total_customers = C1, C2, C3 = 3 unique
    assert kpis["total_customers"] == 3
    # total_quantity = 2 + 3 + 1 + 5 = 11
    assert kpis["total_quantity"] == 11


def test_calculate_growth():
    df = _make_df()
    growth = calculate_growth(df)

    # Monthly: 2026-01 revenue=300 profit=160; 2026-02 revenue=450 profit=190
    assert growth["latest_month"] == "2026-02"
    assert growth["previous_month"] == "2026-01"
    # revenue_growth = (450 - 300) / 300 * 100 = 50.0
    assert growth["revenue_growth_pct"] == 50.0
    # profit_growth = (190 - 160) / 160 * 100 = 18.75 -> 18.8
    assert growth["profit_growth_pct"] == 18.8


def test_calculate_growth_single_month():
    df = _make_df().iloc[:2]  # only 2026-01 rows
    growth = calculate_growth(df)
    assert growth["latest_month"] is None
    assert growth["previous_month"] is None
    assert growth["revenue_growth_pct"] is None
    assert growth["profit_growth_pct"] is None


def test_monthly_trend():
    df = _make_df()
    trend = monthly_trend(df)

    assert list(trend.columns) == ["Month", "Revenue", "Profit", "Orders"]
    assert len(trend) == 2
    assert trend.iloc[0]["Month"] == "2026-01"
    assert trend.iloc[0]["Revenue"] == 300.0
    assert trend.iloc[0]["Profit"] == 160.0
    assert trend.iloc[0]["Orders"] == 2
    assert trend.iloc[1]["Month"] == "2026-02"
    assert trend.iloc[1]["Revenue"] == 450.0
    assert trend.iloc[1]["Profit"] == 190.0
    assert trend.iloc[1]["Orders"] == 2


def test_top_and_worst_products():
    df = _make_df()
    top = top_products(df, n=5)
    worst = worst_products(df, n=5)

    # Product revenues: C=300, A=250, B=200
    assert list(top["Product"]) == ["C", "A", "B"]
    assert list(worst["Product"]) == ["B", "A", "C"]

    # Product C: Revenue=300, Profit=100, Qty=5, Margin=33.3
    c_row = top[top["Product"] == "C"].iloc[0]
    assert c_row["Revenue"] == 300.0
    assert c_row["Profit"] == 100.0
    assert c_row["Quantity"] == 5
    assert c_row["Margin %"] == 33.3


def test_regional_performance():
    df = _make_df()
    regions = regional_performance(df)

    # Region revenues: East=300, North=250, South=200
    assert list(regions["Region"]) == ["East", "North", "South"]

    east = regions[regions["Region"] == "East"].iloc[0]
    assert east["Revenue"] == 300.0
    assert east["Profit"] == 100.0
    assert east["Orders"] == 1
    # East margin = 100/300*100 = 33.3
    assert east["Margin %"] == 33.3
    # East share = 300/750*100 = 40.0
    assert east["Revenue Share %"] == 40.0


def test_category_performance():
    df = _make_df()
    cats = category_performance(df)

    # Category revenues: Electronics=450, Clothing=300
    assert list(cats["Category"]) == ["Electronics", "Clothing"]

    elec = cats[cats["Category"] == "Electronics"].iloc[0]
    assert elec["Revenue"] == 450.0
    assert elec["Profit"] == 250.0
    assert elec["Orders"] == 3
    # Electronics margin = 250/450*100 = 55.6
    assert elec["Margin %"] == 55.6
    # Electronics share = 450/750*100 = 60.0
    assert elec["Revenue Share %"] == 60.0


def test_top_customers():
    df = _make_df()
    customers = top_customers(df, n=5)

    # Customer revenues: C3=300, C1=250, C2=200
    assert list(customers["Customer"]) == ["C3", "C1", "C2"]

    c3 = customers[customers["Customer"] == "C3"].iloc[0]
    assert c3["Revenue"] == 300.0
    assert c3["Profit"] == 100.0
    assert c3["Orders"] == 1
