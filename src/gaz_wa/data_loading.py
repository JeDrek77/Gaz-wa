from __future__ import annotations

from pathlib import Path

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".parquet", ".xlsx", ".xls"}


def load_table(
    path: str | Path,
    *,
    sheet_name: str | int | None = None,
    encoding: str | None = None,
    sep: str | None = None,
) -> pd.DataFrame:
    """Load tabular data from CSV, Excel, or Parquet."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Nie znaleziono pliku: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Nieobslugiwany format {suffix!r}. Obslugiwane: {supported}")

    if suffix == ".csv":
        read_csv_kwargs: dict[str, str] = {}
        if encoding is not None:
            read_csv_kwargs["encoding"] = encoding
        if sep is not None:
            read_csv_kwargs["sep"] = sep
        return pd.read_csv(file_path, **read_csv_kwargs)

    if suffix == ".parquet":
        return pd.read_parquet(file_path)

    return pd.read_excel(file_path, sheet_name=sheet_name or 0)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with stable, code-friendly column names."""
    normalized = df.copy()
    normalized.columns = [
        str(col).strip().lower().replace(" ", "_").replace("-", "_") for col in normalized.columns
    ]
    return normalized
