"""Data loading utilities for InsightOS.

Phase 1 stub: no analytics implemented yet.
"""

import pandas as pd


def load_csv(file) -> pd.DataFrame:
    """Load a CSV file uploaded by the user into a DataFrame.

    Args:
        file: Uploaded file object from st.file_uploader.

    Returns:
        A pandas DataFrame containing the file contents.
    """
    raise NotImplementedError("loader.py is a Phase 1 stub")


def load_sample_data(path: str = "data/sample_sales.csv") -> pd.DataFrame:
    """Load the bundled sample sales dataset.

    Args:
        path: Path to the sample CSV file.

    Returns:
        A pandas DataFrame containing the sample data.
    """
    raise NotImplementedError("loader.py is a Phase 1 stub")
