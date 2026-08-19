from __future__ import annotations

import holidays
import numpy as np
import pandas as pd

from gaz_wa.config import ReportConfig


def add_time_features(df: pd.DataFrame, *, country: str = "PL") -> pd.DataFrame:
    """Add calendar features expected to matter for heat and gas demand."""
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("DataFrame musi miec DatetimeIndex.")

    featured = df.copy()
    index = featured.index
    years = sorted(set(index.year))
    holiday_calendar = holidays.country_holidays(country, years=years)

    featured["hour"] = index.hour
    featured["day_of_week"] = index.dayofweek
    featured["day_of_month"] = index.day
    featured["day_of_year"] = index.dayofyear
    featured["week_of_year"] = index.isocalendar().week.astype("int64")
    featured["month"] = index.month
    featured["quarter"] = index.quarter
    featured["year"] = index.year
    featured["is_weekend"] = index.dayofweek.isin([5, 6]).astype("int8")
    featured["is_holiday_pl"] = (
        pd.Series(index.date, index=index).isin(holiday_calendar).astype("int8")
    )
    featured["heating_season"] = index.month.isin([1, 2, 3, 4, 10, 11, 12]).astype("int8")

    featured["hour_sin"] = np.sin(2 * np.pi * featured["hour"] / 24)
    featured["hour_cos"] = np.cos(2 * np.pi * featured["hour"] / 24)
    featured["month_sin"] = np.sin(2 * np.pi * featured["month"] / 12)
    featured["month_cos"] = np.cos(2 * np.pi * featured["month"] / 12)
    featured["day_of_week_sin"] = np.sin(2 * np.pi * featured["day_of_week"] / 7)
    featured["day_of_week_cos"] = np.cos(2 * np.pi * featured["day_of_week"] / 7)
    return featured


def add_lag_features(
    df: pd.DataFrame,
    *,
    target_col: str,
    config: ReportConfig | None = None,
) -> pd.DataFrame:
    """Add target lags and rolling statistics for backtesting/modeling."""
    if target_col not in df.columns:
        raise ValueError(f"Brakuje kolumny celu: {target_col}")

    cfg = config or ReportConfig()
    featured = df.copy()
    for lag in cfg.lags:
        featured[f"{target_col}_lag_{lag}"] = featured[target_col].shift(lag)

    for window in cfg.rolling_windows:
        shifted = featured[target_col].shift(1)
        featured[f"{target_col}_roll_mean_{window}"] = shifted.rolling(window).mean()
        featured[f"{target_col}_roll_std_{window}"] = shifted.rolling(window).std()
        featured[f"{target_col}_roll_min_{window}"] = shifted.rolling(window).min()
        featured[f"{target_col}_roll_max_{window}"] = shifted.rolling(window).max()

    return featured


def add_weather_like_features(
    df: pd.DataFrame,
    *,
    temperature_col: str | None = None,
    base_temperature: float = 15.0,
) -> pd.DataFrame:
    """Add heating-degree features if an outside temperature column is available."""
    featured = df.copy()
    if temperature_col is None or temperature_col not in featured.columns:
        return featured

    temperature = pd.to_numeric(featured[temperature_col], errors="coerce")
    featured["heating_degree"] = (base_temperature - temperature).clip(lower=0)
    featured["cooling_degree"] = (temperature - base_temperature).clip(lower=0)
    return featured


def build_feature_frame(
    df: pd.DataFrame,
    *,
    target_col: str,
    temperature_col: str | None = None,
) -> pd.DataFrame:
    featured = add_time_features(df)
    featured = add_weather_like_features(featured, temperature_col=temperature_col)
    featured = add_lag_features(featured, target_col=target_col)
    return featured
