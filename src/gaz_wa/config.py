from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"


@dataclass(frozen=True)
class DataSchema:
    timestamp_col: str = "timestamp"
    target_col: str = "gas_consumption"
    freq: str | None = None


@dataclass(frozen=True)
class ReportConfig:
    max_categories: int = 20
    rolling_windows: tuple[int, ...] = (24, 168)
    lags: tuple[int, ...] = (1, 2, 3, 24, 48, 168)
