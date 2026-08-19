from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from gaz_wa.config import DataSchema


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    column: str | None
    message: str


@dataclass(frozen=True)
class ValidationReport:
    rows: int
    columns: int
    issues: list[ValidationIssue]

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)


def validate_raw_frame(df: pd.DataFrame, schema: DataSchema) -> ValidationReport:
    issues: list[ValidationIssue] = []

    if df.empty:
        issues.append(ValidationIssue("error", None, "Dane sa puste."))

    for required_col in (schema.timestamp_col, schema.target_col):
        if required_col not in df.columns:
            issues.append(ValidationIssue("error", required_col, "Brakuje wymaganej kolumny."))

    if schema.timestamp_col in df.columns:
        timestamps = pd.to_datetime(df[schema.timestamp_col], errors="coerce")
        missing_timestamps = int(timestamps.isna().sum())
        if missing_timestamps:
            issues.append(
                ValidationIssue(
                    "error",
                    schema.timestamp_col,
                    f"Nieudane parsowanie dat/czasu dla {missing_timestamps} wierszy.",
                )
            )
        duplicate_timestamps = int(timestamps.duplicated().sum())
        if duplicate_timestamps:
            issues.append(
                ValidationIssue(
                    "warning",
                    schema.timestamp_col,
                    f"Wykryto {duplicate_timestamps} zduplikowanych znacznikow czasu.",
                )
            )
        if not timestamps.dropna().is_monotonic_increasing:
            issues.append(
                ValidationIssue(
                    "warning",
                    schema.timestamp_col,
                    "Znaczniki czasu nie sa posortowane rosnaco.",
                )
            )

    if schema.target_col in df.columns:
        target = pd.to_numeric(df[schema.target_col], errors="coerce")
        missing_target = int(target.isna().sum())
        if missing_target:
            issues.append(
                ValidationIssue(
                    "warning",
                    schema.target_col,
                    f"Kolumna celu ma {missing_target} brakow lub wartosci nienumerycznych.",
                )
            )
        negative_target = int((target < 0).sum())
        if negative_target:
            issues.append(
                ValidationIssue(
                    "warning",
                    schema.target_col,
                    f"Kolumna celu ma {negative_target} wartosci ujemnych.",
                )
            )

    missing_by_col = df.isna().sum()
    for col, missing_count in missing_by_col[missing_by_col > 0].items():
        share = missing_count / max(len(df), 1)
        severity = "warning" if share < 0.3 else "error"
        issues.append(
            ValidationIssue(
                severity,
                str(col),
                f"Braki danych: {missing_count} ({share:.1%}).",
            )
        )

    return ValidationReport(rows=len(df), columns=len(df.columns), issues=issues)


def prepare_time_series(df: pd.DataFrame, schema: DataSchema) -> pd.DataFrame:
    """Parse timestamp and target columns, sort rows, and set a DatetimeIndex."""
    prepared = df.copy()
    prepared[schema.timestamp_col] = pd.to_datetime(prepared[schema.timestamp_col], errors="raise")
    prepared[schema.target_col] = pd.to_numeric(prepared[schema.target_col], errors="coerce")
    prepared = prepared.sort_values(schema.timestamp_col)
    prepared = prepared.set_index(schema.timestamp_col)
    prepared.index.name = "timestamp"
    return prepared
