"""KPI calculation utilities for InsightOS.

Phase 1 stub: no analytics implemented yet.
"""

import pandas as pd


def compute_revenue(df: pd.DataFrame) -> float:
    """Compute total revenue from the DataFrame.

    Args:
        df: Cleaned sales DataFrame.

    Returns:
        Total revenue as a float.
    """
    raise NotImplementedError("kpi.py is a Phase 1 stub")


def compute_profit(df: pd.DataFrame) -> float:
    """Compute total profit from the DataFrame.

    Args:
        df: Cleaned sales DataFrame.

    Returns:
        Total profit as a float.
    """
    raise NotImplementedError("kpi.py is a Phase 1 stub")


def compute_order_count(df: pd.DataFrame) -> int:
    """Compute the number of orders.

    Args:
        df: Cleaned sales DataFrame.

    Returns:
        Number of orders as an integer.
    """
    raise NotImplementedError("kpi.py is a Phase 1 stub")


def compute_growth(df: pd.DataFrame) -> float:
    """Compute period-over-period growth percentage.

    Args:
        df: Cleaned sales DataFrame.

    Returns:
        Growth percentage as a float.
    """
    raise NotImplementedError("kpi.py is a Phase 1 stub")
