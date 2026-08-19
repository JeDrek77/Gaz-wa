from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from contextlib import closing
from pathlib import Path
from typing import Any

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


def load_sql(
    *,
    query: str | None = None,
    table_name: str | None = None,
    database_url: str | None = None,
    sqlite_path: str | Path | None = None,
    schema: str | None = None,
    params: Mapping[str, Any] | Sequence[Any] | None = None,
) -> pd.DataFrame:
    """Load data from SQL using either a raw query or a table name.

    SQLite works with the standard library. Other databases require a SQLAlchemy URL, for example:
    postgresql+psycopg://user:password@host:5432/database
    mssql+pyodbc://user:password@server/database?driver=ODBC+Driver+18+for+SQL+Server
    """
    if (query is None) == (table_name is None):
        raise ValueError("Podaj dokladnie jedno z: query albo table_name.")

    if (database_url is None) == (sqlite_path is None):
        raise ValueError("Podaj dokladnie jedno z: database_url albo sqlite_path.")

    if sqlite_path is not None:
        return _load_sqlite(
            sqlite_path=sqlite_path,
            query=query,
            table_name=table_name,
            params=params,
        )

    return _load_sqlalchemy(
        database_url=database_url or "",
        query=query,
        table_name=table_name,
        schema=schema,
        params=params,
    )


def _load_sqlite(
    *,
    sqlite_path: str | Path,
    query: str | None,
    table_name: str | None,
    params: Mapping[str, Any] | Sequence[Any] | None,
) -> pd.DataFrame:
    db_path = Path(sqlite_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Nie znaleziono bazy SQLite: {db_path}")

    sql = query or f"SELECT * FROM {_quote_sql_identifier(table_name or '')}"
    with closing(sqlite3.connect(db_path)) as connection:
        return pd.read_sql_query(sql, connection, params=params)


def _load_sqlalchemy(
    *,
    database_url: str,
    query: str | None,
    table_name: str | None,
    schema: str | None,
    params: Mapping[str, Any] | Sequence[Any] | None,
) -> pd.DataFrame:
    try:
        from sqlalchemy import create_engine, text
    except ImportError as exc:
        raise ImportError(
            "Do polaczen SQL innych niz SQLite zainstaluj zaleznosc: sqlalchemy."
        ) from exc

    engine = create_engine(database_url)
    try:
        if query is not None:
            with engine.connect() as connection:
                return pd.read_sql_query(text(query), connection, params=params)
        return pd.read_sql_table(table_name or "", engine, schema=schema)
    finally:
        engine.dispose()


def _quote_sql_identifier(identifier: str) -> str:
    if not identifier:
        raise ValueError("Nazwa tabeli nie moze byc pusta.")
    return '"' + identifier.replace('"', '""') + '"'


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with stable, code-friendly column names."""
    normalized = df.copy()
    normalized.columns = [
        str(col).strip().lower().replace(" ", "_").replace("-", "_") for col in normalized.columns
    ]
    return normalized
