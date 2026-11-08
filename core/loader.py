"""Data loading utilities for InsightOS.

Phase 2: implements CSV/Excel loading and column validation.
Cleaning and analytics are intentionally not implemented yet.
"""

import os

import pandas as pd

# Columns required by the InsightOS platform.
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


def load_data(uploaded_file) -> pd.DataFrame:
    """Read an uploaded CSV or Excel file into a pandas DataFrame.

    Args:
        uploaded_file: Uploaded file object from st.file_uploader.

    Returns:
        A pandas DataFrame containing the file contents.

    Raises:
        ValueError: If the file is empty, has an unsupported format,
            or cannot be parsed.
    """
    if uploaded_file is None:
        raise ValueError("No file was uploaded.")

    file_name = getattr(uploaded_file, "name", "")
    extension = os.path.splitext(file_name)[1].lower()

    try:
        if extension == ".csv":
            df = pd.read_csv(uploaded_file)
        elif extension in (".xlsx", ".xls"):
            df = pd.read_excel(uploaded_file)
        else:
            raise ValueError(
                "Unsupported file format. Please upload a .csv or .xlsx file."
            )
    except ValueError:
        # Re-raise ValueError messages we created above.
        raise
    except Exception as exc:  # noqa: BLE001 - surface parse errors clearly
        raise ValueError(
            f"Could not read the file '{file_name}'. "
            f"Please make sure it is a valid CSV or Excel file. "
            f"Error: {exc}"
        ) from exc

    if df.empty:
        raise ValueError("The uploaded file is empty. Please upload a file with data.")

    return df


def load_sample_data(path: str = "data/sample_sales.csv") -> pd.DataFrame:
    """Load the bundled sample sales dataset.

    Args:
        path: Path to the sample CSV file.

    Returns:
        A pandas DataFrame containing the sample data.

    Raises:
        FileNotFoundError: If the sample file does not exist.
        ValueError: If the sample file is empty or cannot be parsed.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Sample data file not found: {path}")

    try:
        df = pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001 - surface parse errors clearly
        raise ValueError(
            f"Could not read the sample data file '{path}'. Error: {exc}"
        ) from exc

    if df.empty:
        raise ValueError("The sample data file is empty.")

    return df


def validate_columns(df: pd.DataFrame) -> list[str]:
    """Check that the DataFrame contains all required columns.

    Args:
        df: DataFrame to validate.

    Returns:
        A list of missing column names (empty if all required columns exist).
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    return missing
