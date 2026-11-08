"""AI analyst utilities for InsightOS.

Phase 1 stub: no analytics implemented yet.
"""

import pandas as pd


def generate_insights(df: pd.DataFrame) -> list[str]:
    """Generate AI-powered insights from the DataFrame.

    Args:
        df: Cleaned sales DataFrame.

    Returns:
        A list of insight strings.
    """
    raise NotImplementedError("ai_analyst.py is a Phase 1 stub")


def answer_question(question: str, df: pd.DataFrame) -> str:
    """Answer a natural-language question about the data.

    Args:
        question: User's question about the business data.
        df: Cleaned sales DataFrame.

    Returns:
        A text answer to the question.
    """
    raise NotImplementedError("ai_analyst.py is a Phase 1 stub")
