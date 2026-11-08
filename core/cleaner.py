"""Data cleaning utilities for InsightOS.

Phase 3: implements clean_data() which normalizes raw sales data and
returns a cleaning report. No analytics (KPIs/charts) implemented yet.
"""

import pandas as pd

# Text columns to strip, title-case, and fill missing values with "Unknown".
TEXT_COLUMNS = ["Product", "Category", "Region", "Customer"]

# Columns that must not be missing; rows missing these are dropped.
REQUIRED_NOT_NULL = ["Date", "Sales", "Product"]

# Numeric columns to coerce; rows that cannot be converted are dropped.
NUMERIC_COLUMNS = ["Sales", "Cost", "Quantity"]

# Columns filled with defaults when missing.
FILL_DEFAULTS = {
    "Cost": 0,
    "Quantity": 1,
    "Region": "Unknown",
    "Category": "Unknown",
    "Customer": "Unknown",
}


def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean and normalize a raw sales DataFrame.

    Performs, in order:
      1. Strip spaces and title-case text columns.
      2. Parse Date to datetime; drop unparseable rows.
      3. Coerce Sales/Cost/Quantity to numeric; drop unconvertible rows.
      4. Remove exact duplicate rows.
      5. Drop rows missing Date, Sales, or Product.
      6. Fill missing Cost (0), Quantity (1), Region/Category/Customer
         ("Unknown").
      7. Drop rows with negative Sales or Quantity.
      8. Add helper columns Profit, Month, Year.

    Args:
        df: Raw DataFrame loaded from a CSV/Excel file.

    Returns:
        A tuple of (cleaned_df, report) where report is a dict with
        cleaning counts.
    """
    # Work on a copy so the original df is never mutated.
    cleaned = df.copy()

    report = {
        "rows_before": int(len(cleaned)),
        "rows_after": 0,
        "duplicates_removed": 0,
        "invalid_dates_removed": 0,
        "invalid_numbers_removed": 0,
        "missing_values_filled": 0,
        "negative_removed": 0,
    }

    # 1. Strip spaces and title-case text columns.
    for col in TEXT_COLUMNS:
        if col in cleaned.columns:
            cleaned[col] = (
                cleaned[col].astype(str).str.strip().str.title()
            )

    # 2. Parse Date to datetime; drop rows that cannot be parsed.
    if "Date" in cleaned.columns:
        before_dates = len(cleaned)
        cleaned["Date"] = pd.to_datetime(cleaned["Date"], errors="coerce")
        cleaned = cleaned.dropna(subset=["Date"])
        report["invalid_dates_removed"] = int(before_dates - len(cleaned))

    # 3. Coerce numeric columns; drop rows that cannot be converted.
    if NUMERIC_COLUMNS:
        before_numbers = len(cleaned)
        for col in NUMERIC_COLUMNS:
            if col in cleaned.columns:
                cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
        cleaned = cleaned.dropna(subset=[c for c in NUMERIC_COLUMNS if c in cleaned.columns])
        report["invalid_numbers_removed"] = int(before_numbers - len(cleaned))

    # 4. Remove exact duplicate rows.
    before_dups = len(cleaned)
    cleaned = cleaned.drop_duplicates()
    report["duplicates_removed"] = int(before_dups - len(cleaned))

    # 5. Drop rows missing Date, Sales, or Product.
    before_required = len(cleaned)
    subset = [c for c in REQUIRED_NOT_NULL if c in cleaned.columns]
    cleaned = cleaned.dropna(subset=subset)

    # 6. Fill missing values with defaults; count how many were filled.
    missing_filled = 0
    for col, default in FILL_DEFAULTS.items():
        if col in cleaned.columns:
            missing_filled += int(cleaned[col].isna().sum())
            cleaned[col] = cleaned[col].fillna(default)
    report["missing_values_filled"] = missing_filled

    # 7. Drop rows with negative Sales or Quantity.
    before_negative = len(cleaned)
    mask = pd.Series(True, index=cleaned.index)
    if "Sales" in cleaned.columns:
        mask &= cleaned["Sales"] >= 0
    if "Quantity" in cleaned.columns:
        mask &= cleaned["Quantity"] >= 0
    cleaned = cleaned[mask]
    report["negative_removed"] = int(before_negative - len(cleaned))

    # 8. Add helper columns: Profit, Month (YYYY-MM), Year.
    if "Sales" in cleaned.columns and "Cost" in cleaned.columns:
        cleaned["Profit"] = cleaned["Sales"] - cleaned["Cost"]
    if "Date" in cleaned.columns:
        cleaned["Month"] = cleaned["Date"].dt.strftime("%Y-%m")
        cleaned["Year"] = cleaned["Date"].dt.year

    report["rows_after"] = int(len(cleaned))

    return cleaned, report
