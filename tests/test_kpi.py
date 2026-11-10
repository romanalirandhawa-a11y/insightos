"""Tests for the InsightOS KPI engine (core/kpi.py).

Uses a tiny hand-made DataFrame where every expected answer can be
verified by hand. Run with: pytest tests/test_kpi.py
"""

import os
import pandas as pd

from core.ai_analyst import build_context, compute_rankings, _fmt_change
from core.kpi import (
    calculate_core_kpis,
    calculate_growth,
    category_performance,
    driver_analysis,
    monthly_trend,
    regional_performance,
    simulate_scenario,
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


def _make_driver_df() -> pd.DataFrame:
    """Build a small two-month DataFrame for driver_analysis testing.

    Month 2026-01:
      A | North | Sales 100 | Profit 40
      B | South | Sales 200 | Profit 100
      C | East  | Sales 150 | Profit 60

    Month 2026-02:
      A | North | Sales 120 | Profit 50   (profit change +10)
      B | South | Sales 150 | Profit 60   (profit change -40)
      C | East  | Sales 180 | Profit 90   (profit change +30)
      D | West  | Sales 100 | Profit 40   (NEW, excluded from comparison)

    Totals: Jan Sales=450 Profit=200; Feb Sales=450 Profit=200.
    """
    data = {
        "Date": [
            "2026-01-10", "2026-01-15", "2026-01-20",
            "2026-02-10", "2026-02-15", "2026-02-20", "2026-02-25",
        ],
        "Product": ["A", "B", "C", "A", "B", "C", "D"],
        "Category": ["Electronics"] * 7,
        "Region": ["North", "South", "East", "North", "South", "East", "West"],
        "Sales": [100.0, 200.0, 150.0, 120.0, 150.0, 180.0, 100.0],
        "Cost": [60.0, 100.0, 90.0, 70.0, 90.0, 90.0, 60.0],
        "Quantity": [2, 3, 1, 2, 2, 3, 1],
        "Customer": ["C1", "C2", "C3", "C1", "C2", "C3", "C4"],
        "Profit": [40.0, 100.0, 60.0, 50.0, 60.0, 90.0, 40.0],
        "Month": ["2026-01", "2026-01", "2026-01",
                  "2026-02", "2026-02", "2026-02", "2026-02"],
        "Year": [2026] * 7,
    }
    return pd.DataFrame(data)


def test_driver_analysis_profit():
    df = _make_driver_df()
    result = driver_analysis(df, metric="Profit")

    assert result["latest_month"] == "2026-02"
    assert result["previous_month"] == "2026-01"
    # Total profit: Jan=200 (A40+B100+C60), Feb=240 (A50+B60+C90+D40)
    # D is new in Feb, so it counts toward the total change (+40).
    assert result["total_change_abs"] == 40.0
    assert result["total_change_pct"] == 20.0

    # Product profit changes: A=+10, B=-40, C=+30, D=+40 (new product)
    pos = dict(result["top_positive_products"])
    neg = dict(result["top_negative_products"])
    assert pos["D"] == 40.0   # new product in Feb, previously 0
    assert pos["C"] == 30.0
    assert pos["A"] == 10.0
    assert neg["B"] == -40.0

    # Region profit changes: North=+10, South=-40, East=+30, West=+40 (new region)
    pos_r = dict(result["top_positive_regions"])
    neg_r = dict(result["top_negative_regions"])
    assert pos_r["West"] == 40.0   # new region in Feb, previously 0
    assert pos_r["East"] == 30.0
    assert pos_r["North"] == 10.0
    assert neg_r["South"] == -40.0


def test_driver_analysis_new_entity_would_have_been_dropped():
    """Regression test: a product/region present in only one month must
    still be counted (treated as 0 in the missing month), not dropped.

    The old buggy implementation used a Product+Region pivot and dropped
    rows missing either month, which made South's change reflect only
    Laptop (-204.04) instead of the true +611.66.
    """
    df = _make_driver_df()
    result = driver_analysis(df, metric="Profit")

    # D (new product in Feb) contributes +40 to product changes.
    pos = dict(result["top_positive_products"])
    assert pos["D"] == 40.0

    # West (new region in Feb) contributes +40 to region changes.
    pos_r = dict(result["top_positive_regions"])
    assert pos_r["West"] == 40.0


def test_driver_analysis_sales():
    df = _make_driver_df()
    result = driver_analysis(df, metric="Sales")

    # Total sales: Jan=450, Feb=550 -> change +100, pct 22.2
    assert result["total_change_abs"] == 100.0
    assert result["total_change_pct"] == 22.2

    # Product sales changes: A=+20, B=-50, C=+30
    pos = dict(result["top_positive_products"])
    neg = dict(result["top_negative_products"])
    assert pos["C"] == 30.0
    assert pos["A"] == 20.0
    assert neg["B"] == -50.0


def test_driver_analysis_single_month():
    df = _make_driver_df().iloc[:3]  # only 2026-01 rows
    result = driver_analysis(df, metric="Profit")

    assert result["latest_month"] is None
    assert result["previous_month"] is None
    assert result["total_change_abs"] is None
    assert result["total_change_pct"] is None
    assert result["top_positive_products"] is None
    assert result["top_negative_products"] is None
    assert result["top_positive_regions"] is None
    assert result["top_negative_regions"] is None


def _make_ranking_df() -> pd.DataFrame:
    """Build a small DataFrame for compute_rankings testing.

    Regions:
      North: Revenue 1000, Profit 400  (margin 40.0%)
      South: Revenue 500,  Profit 100  (margin 20.0%)
      East:  Revenue 2000, Profit 500  (margin 25.0%)
      West:  Revenue 1500, Profit 600  (margin 40.0%)

    Products:
      A: Revenue 800, Profit 200   (margin 25.0%)
      B: Revenue 300, Profit 150   (margin 50.0%)
      C: Revenue 1200, Profit 100  (margin 8.3%)

    Categories:
      Elec: Revenue 1000, Profit 300  (margin 30.0%)
      Cloth: Revenue 400, Profit 50   (margin 12.5%)
    """
    data = {
        "Date": [
            "2026-01-10", "2026-01-11", "2026-01-12",
            "2026-01-13", "2026-01-14", "2026-01-15",
            "2026-01-16", "2026-01-17", "2026-01-18",
            "2026-01-19", "2026-01-20", "2026-01-21",
        ],
        "Product": ["A", "B", "C", "A", "B", "C",
                    "A", "B", "C", "A", "B", "C"],
        "Category": ["Elec", "Cloth", "Elec"] * 4,
        "Region": ["North", "South", "East", "West"] * 3,
        "Sales": [800.0, 300.0, 1200.0, 1000.0, 500.0, 2000.0,
                  800.0, 300.0, 1200.0, 1000.0, 500.0, 2000.0],
        "Cost": [600.0, 150.0, 1100.0, 700.0, 400.0, 1500.0,
                 600.0, 150.0, 1100.0, 700.0, 400.0, 1500.0],
        "Quantity": [2, 3, 1, 4, 2, 5, 2, 3, 1, 4, 2, 5],
        "Customer": ["C1"] * 12,
        "Profit": [200.0, 150.0, 100.0, 300.0, 100.0, 500.0,
                   200.0, 150.0, 100.0, 300.0, 100.0, 500.0],
        "Month": ["2026-01"] * 12,
        "Year": [2026] * 12,
    }
    return pd.DataFrame(data)


def test_compute_rankings_regions():
    df = _make_ranking_df()
    rankings = compute_rankings(df)
    regions = rankings["regions"]

    # Revenue: South & West tie at 3300 (highest), North & East tie at 2500 (lowest)
    rev_sorted = regions.sort_values("Revenue", ascending=False)
    assert rev_sorted.iloc[0]["Revenue"] == 3300.0
    assert rev_sorted.iloc[-1]["Revenue"] == 2500.0
    assert set(rev_sorted.iloc[0:2]["Region"]) == {"South", "West"}
    assert set(rev_sorted.iloc[2:4]["Region"]) == {"North", "East"}

    # Profit: South & West tie at 950 (highest), North & East tie at 400 (lowest)
    prof_sorted = regions.sort_values("Profit", ascending=False)
    assert prof_sorted.iloc[0]["Profit"] == 950.0
    assert prof_sorted.iloc[-1]["Profit"] == 400.0

    # Margin: South & West at 28.8% (highest), North & East at 16.0% (lowest)
    mar_sorted = regions.sort_values("Margin %", ascending=False)
    assert mar_sorted.iloc[0]["Margin %"] == 28.8
    assert mar_sorted.iloc[-1]["Margin %"] == 16.0


def test_compute_rankings_products():
    df = _make_ranking_df()
    rankings = compute_rankings(df)
    products = rankings["products"]

    # Product C: highest revenue (6400) and highest profit (1200)
    hi_rev = products.sort_values("Revenue", ascending=False).iloc[0]
    assert hi_rev["Product"] == "C"
    assert hi_rev["Revenue"] == 6400.0
    hi_prof = products.sort_values("Profit", ascending=False).iloc[0]
    assert hi_prof["Product"] == "C"
    assert hi_prof["Profit"] == 1200.0

    # Product B: lowest revenue (1600) and lowest profit (500)
    lo_rev = products.sort_values("Revenue", ascending=True).iloc[0]
    assert lo_rev["Product"] == "B"
    assert lo_rev["Revenue"] == 1600.0
    lo_prof = products.sort_values("Profit", ascending=True).iloc[0]
    assert lo_prof["Product"] == "B"
    assert lo_prof["Profit"] == 500.0

    # Product B: highest margin (31.2%), Product C: lowest margin (18.8%)
    hi_margin = products.sort_values("Margin %", ascending=False).iloc[0]
    assert hi_margin["Product"] == "B"
    assert hi_margin["Margin %"] == 31.2
    lo_margin = products.sort_values("Margin %", ascending=True).iloc[0]
    assert lo_margin["Product"] == "C"
    assert lo_margin["Margin %"] == 18.8


def test_compute_rankings_categories():
    df = _make_ranking_df()
    rankings = compute_rankings(df)
    categories = rankings["categories"]

    # Category Elec: highest revenue (10000) and highest profit (2200)
    hi_rev = categories.sort_values("Revenue", ascending=False).iloc[0]
    assert hi_rev["Category"] == "Elec"
    assert hi_rev["Revenue"] == 10000.0
    hi_prof = categories.sort_values("Profit", ascending=False).iloc[0]
    assert hi_prof["Category"] == "Elec"
    assert hi_prof["Profit"] == 2200.0

    # Category Cloth: lowest revenue (1600) and lowest profit (500)
    lo_rev = categories.sort_values("Revenue", ascending=True).iloc[0]
    assert lo_rev["Category"] == "Cloth"
    assert lo_rev["Revenue"] == 1600.0
    lo_prof = categories.sort_values("Profit", ascending=True).iloc[0]
    assert lo_prof["Category"] == "Cloth"
    assert lo_prof["Profit"] == 500.0

    # Category Cloth: highest margin (31.2%), Elec: lowest margin (22.0%)
    hi_margin = categories.sort_values("Margin %", ascending=False).iloc[0]
    assert hi_margin["Category"] == "Cloth"
    assert hi_margin["Margin %"] == 31.2
    lo_margin = categories.sort_values("Margin %", ascending=True).iloc[0]
    assert lo_margin["Category"] == "Elec"
    assert lo_margin["Margin %"] == 22.0


def test_fmt_change_signs():
    from core.ai_analyst import _fmt_change
    assert _fmt_change(611.66) == "+$611.66"
    assert _fmt_change(-571.42) == "-$571.42"
    assert _fmt_change(0.0) == "+$0.00"


def test_driver_decline_sorted_biggest_first():
    """Regression test: decline lists must be sorted from the most
    negative change to the least negative. The first item must be the
    biggest decline.
    """
    data = {
        "Date": [
            "2026-01-10", "2026-01-15", "2026-01-20",
            "2026-02-10", "2026-02-15", "2026-02-20",
        ],
        "Product": ["Lamp", "Fiction", "Yoga Mat",
                    "Lamp", "Fiction", "Yoga Mat"],
        "Category": ["Home", "Books", "Sports",
                     "Home", "Books", "Sports"],
        "Region": ["North", "South", "East",
                   "North", "South", "East"],
        "Sales": [5000.0, 4000.0, 3000.0,
                  2000.0, 3000.0, 2500.0],
        "Cost": [2000.0, 1500.0, 1000.0,
                 1900.0, 1100.0, 900.0],
        "Quantity": [10, 8, 6, 4, 6, 5],
        "Customer": ["C1", "C2", "C3", "C1", "C2", "C3"],
        "Profit": [3000.0, 2500.0, 2000.0,
                   100.0, 1900.0, 1600.0],
        "Month": ["2026-01", "2026-01", "2026-01",
                  "2026-02", "2026-02", "2026-02"],
        "Year": [2026] * 6,
    }
    df = pd.DataFrame(data)

    ctx = build_context(df)

    # Profit changes: Lamp -2900 (biggest), Fiction -600, Yoga Mat -400
    lines = ctx.split("\n")
    in_profit_decline = False
    decline_items = []
    for line in lines:
        if "Products with profit decline:" in line:
            in_profit_decline = True
            continue
        if in_profit_decline:
            if line.strip().startswith("Product "):
                # Extract product name and change
                decline_items.append(line.strip())
            elif line.strip() == "" or line.strip().startswith("Top positive"):
                in_profit_decline = False

    # First item should be Lamp with -$2,900.00
    assert len(decline_items) >= 1, f"Expected decline items, got: {decline_items}"
    assert "Lamp" in decline_items[0], f"First decline should be Lamp, got: {decline_items[0]}"
    assert "-$2,900.00" in decline_items[0], f"Lamp change should be -$2,900.00, got: {decline_items[0]}"
    # Second should be Fiction (-$600.00), third Yoga Mat (-$400.00)
    assert "Fiction" in decline_items[1]
    assert "-$600.00" in decline_items[1]
    assert "Yoga Mat" in decline_items[2]
    assert "-$400.00" in decline_items[2]

    # Check RANKINGS section has biggest profit decline product
    assert "Biggest profit decline product: Lamp (-$2,900.00)" in ctx

    # Sales changes: Lamp -3000 (biggest), Fiction -1000, Yoga Mat -500
    in_sales_decline = False
    sales_decline_items = []
    for line in lines:
        if "Products with sales decline:" in line:
            in_sales_decline = True
            continue
        if in_sales_decline:
            if line.strip().startswith("Product "):
                sales_decline_items.append(line.strip())
            elif line.strip() == "" or line.strip().startswith("Top positive"):
                in_sales_decline = False

    assert len(sales_decline_items) >= 1
    assert "Lamp" in sales_decline_items[0]
    assert "-$3,000.00" in sales_decline_items[0]
    assert "Biggest sales decline product: Lamp (-$3,000.00)" in ctx


# ---- Provider selection tests (no real API calls) ----

import os as _os


def _save_env():
    return dict(_os.environ)


def _restore_env(saved):
    _os.environ.clear()
    _os.environ.update(saved)


def _set_env(**kwargs):
    for k, v in kwargs.items():
        if v is None:
            _os.environ.pop(k, None)
        else:
            _os.environ[k] = v


def test_get_provider_default():
    saved = _save_env()
    try:
        _set_env(AI_PROVIDER=None)
        from core.ai_analyst import _get_provider
        assert _get_provider() == "openrouter"
    finally:
        _restore_env(saved)


def test_get_provider_gemini():
    saved = _save_env()
    try:
        _set_env(AI_PROVIDER="gemini")
        from core.ai_analyst import _get_provider
        assert _get_provider() == "gemini"
    finally:
        _restore_env(saved)


def test_get_client_openrouter_missing_key():
    saved = _save_env()
    try:
        _set_env(AI_PROVIDER="openrouter", OPENROUTER_API_KEY=None)
        from core.ai_analyst import _get_client_and_model
        client, model = _get_client_and_model("openrouter")
        assert client is None
        assert model is None
    finally:
        _restore_env(saved)


def test_get_client_gemini_missing_key():
    saved = _save_env()
    try:
        _set_env(AI_PROVIDER="gemini", GEMINI_API_KEY=None)
        from core.ai_analyst import _get_client_and_model
        client, model = _get_client_and_model("gemini")
        assert client is None
        assert model is None
    finally:
        _restore_env(saved)


def test_get_client_gemini_missing_model():
    saved = _save_env()
    try:
        _set_env(
            AI_PROVIDER="gemini",
            GEMINI_API_KEY="fake-key",
            GEMINI_MODEL=None,
        )
        from core.ai_analyst import _get_client_and_model
        client, model = _get_client_and_model("gemini")
        # Missing model falls back to default, client is still created.
        assert client is not None
        assert model == "gemini-1.5-flash"
    finally:
        _restore_env(saved)


def test_get_client_openrouter_returns_client_model():
    saved = _save_env()
    try:
        _set_env(
            AI_PROVIDER="openrouter",
            OPENROUTER_API_KEY="sk-or-test123",
            OPENROUTER_MODEL="openrouter/free",
        )
        from core.ai_analyst import _get_client_and_model
        client, model = _get_client_and_model("openrouter")
        assert client is not None
        assert model == "openrouter/free"
    finally:
        _restore_env(saved)


def test_get_client_gemini_returns_client_model():
    saved = _save_env()
    try:
        _set_env(
            AI_PROVIDER="gemini",
            GEMINI_API_KEY="fake-gemini-key",
            GEMINI_MODEL="gemini-1.5-flash",
        )
        from core.ai_analyst import _get_client_and_model
        client, model = _get_client_and_model("gemini")
        assert client is not None
        assert model == "gemini-1.5-flash"
    finally:
        _restore_env(saved)


def test_other_provider():
    saved = _save_env()
    try:
        from core.ai_analyst import _other_provider
        assert _other_provider("openrouter") == "gemini"
        assert _other_provider("gemini") == "openrouter"
    finally:
        _restore_env(saved)


def test_friendly_error_rate_limit():
    saved = _save_env()
    try:
        from core.ai_analyst import _friendly_error
        msg = _friendly_error(Exception("429 rate limit exceeded"), "openrouter")
        assert "rate-limited" in msg
        assert "OPENROUTER_API_KEY" not in msg
        assert "sk-or-" not in msg
    finally:
        _restore_env(saved)


def test_friendly_error_auth():
    saved = _save_env()
    try:
        from core.ai_analyst import _friendly_error
        msg = _friendly_error(Exception("401 Unauthorized"), "gemini")
        assert "Authentication failed" in msg
        assert "GEMINI_API_KEY" in msg
        assert "fake" not in msg
    finally:
        _restore_env(saved)


# ---- Answer quality tests (no real API calls) ----


def test_strip_reasoning_think_block():
    saved = _save_env()
    try:
        from core.ai_analyst import _strip_reasoning
        open_t = chr(60) + "think" + chr(62)
        close_t = chr(60) + "/" + "think" + chr(62)
        raw = f"\n{open_t}1. Analyze the Request: ...{close_t}\n\nThe answer is 42."
        result = _strip_reasoning(raw)
        assert "Analyze the Request" not in result
        assert "The answer is 42" in result

    finally:
        _restore_env(saved)


def test_strip_reasoning_think_block_multiline():
    saved = _save_env()
    try:
        from core.ai_analyst import _strip_reasoning
        open_t = chr(60) + "think" + chr(62)
        close_t = chr(60) + "/" + "think" + chr(62)
        raw = f"\n{open_t}some reasoning over multiple lines{close_t}\n\nfinal answer here"
        result = _strip_reasoning(raw)
        assert "some reasoning" not in result
        assert "final answer here" in result
    finally:
        _restore_env(saved)


def test_strip_reasoning_no_think_block():
    saved = _save_env()
    try:
        from core.ai_analyst import _strip_reasoning
        raw = "The answer is 42. Recommendation: do X."
        result = _strip_reasoning(raw)
        assert result == "The answer is 42. Recommendation: do X."
    finally:
        _restore_env(saved)


def test_call_provider_cut_off_detection():
    """Test that finish_reason == 'length' is detected as cut off."""
    saved = _save_env()
    try:
        _set_env(
            AI_PROVIDER="openrouter",
            OPENROUTER_API_KEY="sk-or-test123",
            OPENROUTER_MODEL="openrouter/free",
        )
        from core.ai_analyst import _call_provider, _get_client_and_model
        from openai import OpenAI

        client, model = _get_client_and_model("openrouter")

        # Build a fake response object
        class FakeMessage:
            content = "The answer is partial"

        class FakeChoice:
            finish_reason = "length"
            message = FakeMessage()

        class FakeResponse:
            choices = [FakeChoice()]

        # Monkeypatch client.chat.completions.create
        original_create = client.chat.completions.create

        def fake_create(**kwargs):
            return FakeResponse()

        client.chat.completions.create = fake_create
        try:
            answer, finish_reason, is_cut_off = _call_provider(
                client, model, [{"role": "user", "content": "hi"}], "openrouter"
            )
            assert is_cut_off is True
            assert finish_reason == "length"
            assert answer == "The answer is partial"
        finally:
            client.chat.completions.create = original_create
    finally:
        _restore_env(saved)


def test_empty_answer_is_blank():
    saved = _save_env()
    try:
        from core.ai_analyst import _is_blank
        assert _is_blank("") is True
        assert _is_blank("   ") is True
        assert _is_blank(None) is True
        assert _is_blank("hello") is False
    finally:
        _restore_env(saved)


# ---- ask_analyst_stream end-to-end tests with fake clients ----


def _make_fake_chunk_objects(chunks):
    """Build fake stream response chunks from a list of (text, finish_reason)."""

    class FakeDelta:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content, finish_reason):
            self.delta = FakeDelta(content)
            self.finish_reason = finish_reason

    class FakeResponse:
        def __init__(self, chunks):
            self._chunks = chunks
            self._index = 0

        def __iter__(self):
            return self

        def __next__(self):
            if self._index >= len(self._chunks):
                raise StopIteration
            content, finish_reason = self._chunks[self._index]
            self._index += 1
            fake = object.__new__(FakeResponse)
            fake.choices = [FakeChoice(content, finish_reason)]
            return fake

    return FakeResponse(chunks)


def test_ask_analyst_stream_end_to_end():
    """Test ask_analyst_stream end-to-end with a fake client, no real API call."""
    saved = _save_env()
    try:
        _set_env(
            AI_PROVIDER="openrouter",
            OPENROUTER_API_KEY="sk-or-test123",
            OPENROUTER_MODEL="openrouter/free",
        )
        from core.ai_analyst import ask_analyst_stream

        import types

        client = types.SimpleNamespace()
        client.chat = types.SimpleNamespace()
        client.chat.completions = types.SimpleNamespace()

        def fake_create(**kwargs):
            return _make_fake_chunk_objects(
                [("Hello ", None), ("world", None), ("!", "stop")]
            )

        client.chat.completions.create = fake_create

        import core.ai_analyst as aa

        orig_get_client_and_model = aa._get_client_and_model
        aa._get_client_and_model = lambda provider: (client, "openrouter/free")
        try:
            result = list(ask_analyst_stream("test question", "test context"))
            assert "".join(result) == "Hello world!"
        finally:
            aa._get_client_and_model = orig_get_client_and_model
    finally:
        _restore_env(saved)


def test_ask_analyst_stream_fallback_to_secondary():
    """Test ask_analyst_stream falls back to secondary when primary errors."""
    saved = _save_env()
    try:
        _set_env(
            AI_PROVIDER="openrouter",
            OPENROUTER_API_KEY="sk-or-test123",
            OPENROUTER_MODEL="openrouter/free",
            GEMINI_API_KEY="fake-gemini-key",
            GEMINI_MODEL="gemini-1.5-flash",
        )
        from core.ai_analyst import ask_analyst_stream
        import core.ai_analyst as aa
        import types

        orig_get_client_and_model = aa._get_client_and_model

        def fake_get_client_and_model(provider):
            client = types.SimpleNamespace()
            client.chat = types.SimpleNamespace()
            client.chat.completions = types.SimpleNamespace()

            if provider == "openrouter":
                def fake_create_error(**kwargs):
                    raise Exception("401 Unauthorized")
                client.chat.completions.create = fake_create_error
            else:
                def fake_create_secondary(**kwargs):
                    return _make_fake_chunk_objects(
                        [("Fallback ", None), ("answer", "stop")]
                    )
                client.chat.completions.create = fake_create_secondary

            return client, provider + "/model"

        aa._get_client_and_model = fake_get_client_and_model
        try:
            result = list(ask_analyst_stream("test question", "test context"))
            assert "".join(result) == "Fallback answer"
        finally:
            aa._get_client_and_model = orig_get_client_and_model
    finally:
        _restore_env(saved)


# ---- simulate_scenario tests ----


def _make_sim_df() -> pd.DataFrame:
    """Small DataFrame where revenue=1000, cost=600, profit=400."""
    data = {
        "Date": ["2026-01-10", "2026-01-15", "2026-01-20"],
        "Product": ["A", "B", "C"],
        "Category": ["Elec", "Elec", "Cloth"],
        "Region": ["North", "South", "East"],
        "Sales": [400.0, 350.0, 250.0],
        "Cost": [200.0, 250.0, 150.0],
        "Quantity": [4, 7, 5],
        "Customer": ["C1", "C2", "C3"],
        "Profit": [200.0, 100.0, 100.0],
        "Month": ["2026-01"] * 3,
        "Year": [2026] * 3,
    }
    return pd.DataFrame(data)


def test_simulate_scenario_no_change():
    """All zeros: scenario equals current."""
    df = _make_sim_df()
    result = simulate_scenario(df)

    assert result["current_revenue"] == 1000.0
    assert result["current_cost"] == 600.0
    assert result["current_profit"] == 400.0
    assert result["current_margin_pct"] == 40.0

    assert result["scenario_revenue"] == 1000.0
    assert result["scenario_cost"] == 600.0
    assert result["scenario_profit"] == 400.0
    assert result["scenario_margin_pct"] == 40.0

    assert result["revenue_change"] == 0.0
    assert result["profit_change"] == 0.0
    assert result["margin_change_points"] == 0.0


def test_simulate_scenario_price_increase():
    """Price +10%: revenue 1000 -> 1100, cost unchanged, profit 400 -> 500."""
    df = _make_sim_df()
    result = simulate_scenario(df, price_change_pct=10)

    assert result["scenario_revenue"] == 1100.0
    assert result["scenario_cost"] == 600.0
    assert result["scenario_profit"] == 500.0
    assert result["scenario_margin_pct"] == 45.5  # 500/1100*100

    assert result["revenue_change"] == 100.0
    assert result["profit_change"] == 100.0
    assert result["revenue_change_pct"] == 10.0


def test_simulate_scenario_volume_increase():
    """Volume +20%: revenue 1000*1.2=1200, cost 600*1.2=720, profit 480."""
    df = _make_sim_df()
    result = simulate_scenario(df, volume_change_pct=20)

    assert result["scenario_revenue"] == 1200.0
    assert result["scenario_cost"] == 720.0
    assert result["scenario_profit"] == 480.0
    assert result["scenario_margin_pct"] == 40.0  # 480/1200*100

    assert result["revenue_change"] == 200.0
    assert result["profit_change"] == 80.0


def test_simulate_scenario_cost_increase():
    """Cost +8%: cost 600 -> 648, revenue unchanged, profit 400 -> 352."""
    df = _make_sim_df()
    result = simulate_scenario(df, cost_change_pct=8)

    assert result["scenario_revenue"] == 1000.0
    assert result["scenario_cost"] == 648.0
    assert result["scenario_profit"] == 352.0

    assert result["profit_change"] == -48.0


def test_simulate_scenario_combined():
    """Price +10% and volume +10%: revenue 1000*1.1*1.1=1210."""
    df = _make_sim_df()
    result = simulate_scenario(df, price_change_pct=10, volume_change_pct=10)

    assert result["scenario_revenue"] == 1210.0


def test_simulate_scenario_invalid_input():
    """Values at or below -100 raise ValueError."""
    df = _make_sim_df()

    try:
        simulate_scenario(df, price_change_pct=-100)
        assert False, "Expected ValueError"
    except ValueError:
        pass

    try:
        simulate_scenario(df, volume_change_pct=-101)
        assert False, "Expected ValueError"
    except ValueError:
        pass

    try:
        simulate_scenario(df, cost_change_pct=-150)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_simulate_scenario_zero_current_revenue():
    """Zero current revenue: margin pct changes are 0 (safe divide)."""
    df = _make_sim_df()
    df_empty = df.iloc[0:0]
    result = simulate_scenario(df_empty, price_change_pct=10)

    assert result["current_revenue"] == 0.0
    assert result["current_margin_pct"] == 0.0
    assert result["scenario_margin_pct"] == 0.0
    assert result["margin_change_pct"] == 0.0


# ---- What-If callback tests ----


def test_set_wi_scenario_price_up():
    saved_state = {}
    import app as app_module

    # Monkeypatch st.session_state with a fake dict.
    import streamlit as st

    original_session_state = st.session_state
    st.session_state = saved_state
    try:
        app_module._set_wi_scenario(5, 0, 0)
        assert saved_state["wi_price"] == 5
        assert saved_state["wi_volume"] == 0
        assert saved_state["wi_cost"] == 0
    finally:
        st.session_state = original_session_state


def test_set_wi_scenario_sales_down():
    saved_state = {}
    import app as app_module

    import streamlit as st

    original_session_state = st.session_state
    st.session_state = saved_state
    try:
        app_module._set_wi_scenario(0, -10, 0)
        assert saved_state["wi_price"] == 0
        assert saved_state["wi_volume"] == -10
        assert saved_state["wi_cost"] == 0
    finally:
        st.session_state = original_session_state


def test_set_wi_scenario_cost_up():
    saved_state = {}
    import app as app_module

    import streamlit as st

    original_session_state = st.session_state
    st.session_state = saved_state
    try:
        app_module._set_wi_scenario(0, 0, 8)
        assert saved_state["wi_price"] == 0
        assert saved_state["wi_volume"] == 0
        assert saved_state["wi_cost"] == 8
    finally:
        st.session_state = original_session_state


def test_set_wi_scenario_reset():
    saved_state = {"wi_price": 25, "wi_volume": -30, "wi_cost": 15}
    import app as app_module

    import streamlit as st

    original_session_state = st.session_state
    st.session_state = saved_state
    try:
        app_module._set_wi_scenario(0, 0, 0)
        assert saved_state["wi_price"] == 0
        assert saved_state["wi_volume"] == 0
        assert saved_state["wi_cost"] == 0
    finally:
        st.session_state = original_session_state


# ---- ai_is_configured tests ----


def test_ai_is_configured_openrouter_key():
    saved = _save_env()
    try:
        _set_env(AI_PROVIDER="openrouter", OPENROUTER_API_KEY="sk-or-test123", GEMINI_API_KEY=None)
        from core.ai_analyst import ai_is_configured
        assert ai_is_configured() is True
    finally:
        _restore_env(saved)


def test_ai_is_configured_gemini_key():
    saved = _save_env()
    try:
        _set_env(AI_PROVIDER="gemini", OPENROUTER_API_KEY=None, GEMINI_API_KEY="fake-gemini-key")
        from core.ai_analyst import ai_is_configured
        assert ai_is_configured() is True
    finally:
        _restore_env(saved)


def test_ai_is_configured_both_keys():
    saved = _save_env()
    try:
        _set_env(AI_PROVIDER="openrouter", OPENROUTER_API_KEY="sk-or-test123", GEMINI_API_KEY="fake-gemini-key")
        from core.ai_analyst import ai_is_configured
        assert ai_is_configured() is True
    finally:
        _restore_env(saved)


def test_ai_is_configured_no_keys():
    saved = _save_env()
    try:
        _set_env(AI_PROVIDER="openrouter", OPENROUTER_API_KEY=None, GEMINI_API_KEY=None)
        from core.ai_analyst import ai_is_configured
        assert ai_is_configured() is False
    finally:
        _restore_env(saved)


def test_ai_is_configured_empty_keys():
    saved = _save_env()
    try:
        _set_env(AI_PROVIDER="openrouter", OPENROUTER_API_KEY="", GEMINI_API_KEY="   ")
        from core.ai_analyst import ai_is_configured
        assert ai_is_configured() is False
    finally:
        _restore_env(saved)


# ---- Chart function tests ----


def _make_trend_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Month": ["2026-01", "2026-02", "2026-03"],
        "Sales": [1000.0, 1100.0, 1200.0],
        "Profit": [200.0, 250.0, 300.0],
        "Orders": [10, 11, 12],
    })


def _make_products_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Product": ["A", "B", "C"],
        "Sales": [500.0, 300.0, 200.0],
        "Profit": [100.0, 90.0, 50.0],
        "Quantity": [10, 5, 4],
        "Margin %": [20.0, 30.0, 25.0],
    })


def _make_region_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Region": ["North", "South", "East"],
        "Sales": [500.0, 300.0, 200.0],
        "Profit": [100.0, 90.0, 50.0],
        "Margin %": [20.0, 30.0, 25.0],
        "Orders": [10, 5, 4],
        "Revenue Share %": [50.0, 30.0, 20.0],
    })


def _make_category_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Category": ["Electronics", "Clothing", "Home"],
        "Sales": [500.0, 300.0, 200.0],
        "Profit": [100.0, 90.0, 50.0],
        "Margin %": [20.0, 30.0, 25.0],
        "Orders": [10, 5, 4],
        "Revenue Share %": [50.0, 30.0, 20.0],
    })


def test_revenue_profit_trend_chart_returns_figure():
    from core.kpi import monthly_trend
    from ui.charts import revenue_profit_trend_chart
    df = _make_trend_df()
    trend = monthly_trend(df)
    fig = revenue_profit_trend_chart(trend)
    from plotly.graph_objects import Figure
    assert isinstance(fig, Figure)


def test_top_products_chart_returns_figure():
    from core.kpi import top_products
    from ui.charts import top_products_chart
    df = _make_products_df()
    products = top_products(df)
    fig = top_products_chart(products)
    from plotly.graph_objects import Figure
    assert isinstance(fig, Figure)


def test_regional_chart_returns_figure():
    from core.kpi import regional_performance
    from ui.charts import regional_chart
    df = _make_region_df()
    regions = regional_performance(df)
    fig = regional_chart(regions)
    from plotly.graph_objects import Figure
    assert isinstance(fig, Figure)


def test_category_donut_chart_returns_figure():
    from core.kpi import category_performance
    from ui.charts import category_donut_chart
    df = _make_category_df()
    cats = category_performance(df)
    fig = category_donut_chart(cats)
    from plotly.graph_objects import Figure
    assert isinstance(fig, Figure)


def test_scenario_bar_chart_returns_figure():
    from ui.charts import scenario_bar_chart
    current = {"Revenue": 1000.0, "Cost": 600.0, "Profit": 400.0}
    scenario = {"Revenue": 1100.0, "Cost": 660.0, "Profit": 440.0}
    fig = scenario_bar_chart(current, scenario)
    from plotly.graph_objects import Figure
    assert isinstance(fig, Figure)


# ---- AI Analyst page rendering test (AppTest) ----


def test_ai_analyst_page_renders_with_data():
    """AppTest: AI Analyst page renders without exception when data is loaded.

    Asserts that either a chat input or a demo-disabled info box is present,
    and that no exception occurs during rendering.
    """
    from streamlit.testing.v1 import AppTest
    from core.loader import load_sample_data
    from core.cleaner import clean_data

    df_raw = load_sample_data()
    df_clean, _ = clean_data(df_raw)

    at = AppTest.from_file("../app.py")
    at.session_state["df_clean"] = df_clean
    at.session_state["current_page"] = "AI Analyst"

    at.run(timeout=60)

    # AppTest.exception returns an ElementList; empty means no exceptions
    assert len(at.exception) == 0, f"AppTest exceptions: {at.exception}"

    # Either chat input (configured) or info box (not configured) should be present
    has_chat_input = len(at.chat_input) >= 1
    has_info_box = len(at.info) >= 1
    assert has_chat_input or has_info_box, (
        "AI Analyst page rendered neither chat input nor info box"
    )


# ---- AI Analyst fake-client tests (no real API calls) ----


class _FakeDelta:
    def __init__(self, content: str = ""):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str = "", finish_reason: str | None = None):
        self.delta = _FakeDelta(content)
        self.finish_reason = finish_reason


class _FakeChunk:
    def __init__(self, content: str = "", finish_reason: str | None = None):
        self.choices = [_FakeChoice(content, finish_reason)]


class _FakeMessage:
    def __init__(self, content: str = ""):
        self.content = content


class _FakeResponseChoice:
    def __init__(self, content: str = "", finish_reason: str | None = None):
        self.message = _FakeMessage(content)
        self.finish_reason = finish_reason


class _FakeResponse:
    def __init__(self, content: str = "", finish_reason: str | None = None):
        self.choices = [_FakeResponseChoice(content, finish_reason)]


class _FakeStream:
    """Fake stream that yields chunks then stops."""

    def __init__(self, chunks: list[tuple[str, str | None]]):
        self._chunks = chunks
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._chunks):
            raise StopIteration
        content, finish_reason = self._chunks[self._index]
        self._index += 1
        return _FakeChunk(content, finish_reason)


class _FakeClient:
    """Fake OpenAI client for testing without real API calls."""

    def __init__(self, chunks: list[tuple[str, str | None]], should_fail: bool = False):
        self._chunks = chunks
        self._should_fail = should_fail
        self.call_count = 0
        self._chunk_index = 0

    class _Completions:
        def __init__(self, parent):
            self._parent = parent

        def create(self, **kwargs):
            self._parent.call_count += 1
            if self._parent._should_fail:
                raise Exception("401 Unauthorized")
            stream = kwargs.get("stream", False)
            if stream:
                return _FakeStream(list(self._parent._chunks))
            # Non-streaming: use first chunk as full response
            if self._parent._chunk_index >= len(self._parent._chunks):
                return _FakeResponse("", "stop")
            content, finish_reason = self._parent._chunks[self._parent._chunk_index]
            self._parent._chunk_index += 1
            return _FakeResponse(content, finish_reason)

    def __init__(self, chunks, should_fail=False):
        self._chunks = list(chunks)
        self._should_fail = should_fail
        self.call_count = 0
        self._chunk_index = 0
        self.chat = type("chat", (), {})()
        self.chat.completions = self._Completions(self)


def _monkeypatch_client(chunks, should_fail=False):
    """Monkeypatch _get_client_and_model to return a fake client."""
    import core.ai_analyst as ai_mod

    client = _FakeClient(chunks, should_fail)

    def fake_get_client_and_model(provider):
        return client, "test-model"

    orig = ai_mod._get_client_and_model
    ai_mod._get_client_and_model = fake_get_client_and_model
    return ai_mod, orig, client


def test_history_strips_cut_off_note():
    """Cut-off notes in assistant history are stripped before sending to model."""
    import core.ai_analyst as ai_mod

    saved_env = dict(os.environ)
    try:
        os.environ["AI_PROVIDER"] = "openrouter"
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test123"
        os.environ["OPENROUTER_MODEL"] = "openrouter/free"

        ai_mod, orig, client = _monkeypatch_client(
            [("The answer is 42 (answer was cut off, try again)", "stop")]
        )
        try:
            # Build messages with history containing a cut-off note
            history = [
                {"role": "user", "content": "CONTEXT:\nsome context\n\nQUESTION: old q"},
                {"role": "assistant", "content": "old answer (answer was cut off, try again)"},
            ]
            messages = ai_mod._build_messages("new question", "ctx", history)

            # The cut-off note should be stripped from the assistant message
            assistant_msgs = [m for m in messages if m["role"] == "assistant"]
            assert len(assistant_msgs) == 1
            assert "(answer was cut off, try again)" not in assistant_msgs[0]["content"]
            assert assistant_msgs[0]["content"] == "old answer"
        finally:
            ai_mod._get_client_and_model = orig
            os.environ.clear()
            os.environ.update(saved_env)
    finally:
        os.environ.clear()
        os.environ.update(saved_env)


def test_history_keeps_only_last_4_turns():
    """Only the last 4 turns are sent to the model."""
    import core.ai_analyst as ai_mod

    saved_env = dict(os.environ)
    try:
        os.environ["AI_PROVIDER"] = "openrouter"
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test123"
        os.environ["OPENROUTER_MODEL"] = "openrouter/free"

        ai_mod, orig, _ = _monkeypatch_client([("answer", "stop")])
        try:
            # 6 turns = 12 messages (6 user + 6 assistant). Only last 4 turns = 8 messages.
            history = []
            for i in range(6):
                history.append({"role": "user", "content": f"user {i}"})
                history.append({"role": "assistant", "content": f"assistant {i}"})
            messages = ai_mod._build_messages("new question", "ctx", history)

            # system + context/user + last 8 history messages
            user_msgs = [m for m in messages if m["role"] == "user"]
            # Last 4 turns = 4 user messages (from turns 2,3,4,5) + the new question = 5
            assert len(user_msgs) == 5, f"Expected 5 user messages, got {len(user_msgs)}"
            assert user_msgs[-1]["content"].startswith("CONTEXT:")
            assert user_msgs[0]["content"] == "user 2"
        finally:
            ai_mod._get_client_and_model = orig
            os.environ.clear()
            os.environ.update(saved_env)
    finally:
        os.environ.clear()
        os.environ.update(saved_env)


def test_question_not_duplicated_in_history():
    """The current question appears only once in messages sent to model."""
    import core.ai_analyst as ai_mod

    saved_env = dict(os.environ)
    try:
        os.environ["AI_PROVIDER"] = "openrouter"
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test123"
        os.environ["OPENROUTER_MODEL"] = "openrouter/free"

        ai_mod, orig, _ = _monkeypatch_client([("answer", "stop")])
        try:
            history = [
                {"role": "user", "content": "CONTEXT:\nctx\n\nQUESTION: old q"},
                {"role": "assistant", "content": "old answer"},
            ]
            messages = ai_mod._build_messages("What is revenue?", "ctx", history)

            # Count occurrences of the question text
            question_text = "What is revenue?"
            count = sum(1 for m in messages if question_text in m.get("content", ""))
            assert count == 1, f"Question appears {count} times, expected 1"
        finally:
            ai_mod._get_client_and_model = orig
            os.environ.clear()
            os.environ.update(saved_env)
    finally:
        os.environ.clear()
        os.environ.update(saved_env)


def test_retry_on_empty_answer_then_success():
    """Primary provider retried once on empty answer, then succeeds."""
    import core.ai_analyst as ai_mod

    saved_env = dict(os.environ)
    try:
        os.environ["AI_PROVIDER"] = "openrouter"
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test123"
        os.environ["OPENROUTER_MODEL"] = "openrouter/free"

        # First call returns empty, second returns answer
        client = _FakeClient([("", "stop"), ("The answer is 42", "stop")])

        def fake_get_client_and_model(provider):
            return client, "test-model"

        orig = ai_mod._get_client_and_model
        ai_mod._get_client_and_model = fake_get_client_and_model
        try:
            answer, prov = ai_mod._try_providers("test question", "ctx", None)
            assert answer == "The answer is 42"
            assert client.call_count == 2  # Called twice (retry)
        finally:
            ai_mod._get_client_and_model = orig
            os.environ.clear()
            os.environ.update(saved_env)
    finally:
        os.environ.clear()
        os.environ.update(saved_env)


def test_retry_on_empty_then_secondary():
    """Primary returns empty twice, secondary succeeds."""
    import core.ai_analyst as ai_mod

    saved_env = dict(os.environ)
    try:
        os.environ["AI_PROVIDER"] = "openrouter"
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test123"
        os.environ["OPENROUTER_MODEL"] = "openrouter/free"
        os.environ["GEMINI_API_KEY"] = "fake-gemini-key"
        os.environ["GEMINI_MODEL"] = "gemini-1.5-flash"

        # Primary returns empty twice
        primary_client = _FakeClient([("", "stop"), ("", "stop")])
        # Secondary succeeds
        secondary_client = _FakeClient([("Secondary answer", "stop")])

        call_order = []

        def fake_get_client_and_model(provider):
            call_order.append(provider)
            if provider == "openrouter":
                return primary_client, "openrouter/free"
            return secondary_client, "gemini-1.5-flash"

        orig = ai_mod._get_client_and_model
        ai_mod._get_client_and_model = fake_get_client_and_model
        try:
            answer, prov = ai_mod._try_providers("test question", "ctx", None)
            assert answer == "Secondary answer"
            assert prov == "gemini"
            assert primary_client.call_count == 2  # Primary tried twice
            assert secondary_client.call_count == 1  # Secondary tried once
        finally:
            ai_mod._get_client_and_model = orig
            os.environ.clear()
            os.environ.update(saved_env)
    finally:
        os.environ.clear()
        os.environ.update(saved_env)


def test_cut_off_note_not_appended_to_answer():
    """Cut-off note is NOT appended to the final answer text."""
    import core.ai_analyst as ai_mod

    saved_env = dict(os.environ)
    try:
        os.environ["AI_PROVIDER"] = "openrouter"
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test123"
        os.environ["OPENROUTER_MODEL"] = "openrouter/free"

        # finish_reason == "length" but answer text doesn't get cut-off note appended
        client = _FakeClient([("The answer is complete", "length")])

        def fake_get_client_and_model(provider):
            return client, "test-model"

        orig = ai_mod._get_client_and_model
        ai_mod._get_client_and_model = fake_get_client_and_model
        try:
            answer, prov = ai_mod._try_providers("test question", "ctx", None)
            assert answer == "The answer is complete"
            assert "(answer was cut off, try again)" not in answer
        finally:
            ai_mod._get_client_and_model = orig
            os.environ.clear()
            os.environ.update(saved_env)
    finally:
        os.environ.clear()
        os.environ.update(saved_env)


