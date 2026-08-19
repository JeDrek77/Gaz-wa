from pathlib import Path

from gaz_wa.config import DataSchema
from gaz_wa.data_loading import load_table
from gaz_wa.features import build_feature_frame
from gaz_wa.validation import prepare_time_series, validate_raw_frame

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_sample_data_validates_and_builds_features() -> None:
    schema = DataSchema(timestamp_col="timestamp", target_col="gas_consumption")
    df = load_table(PROJECT_ROOT / "data" / "sample_gas_consumption.csv")

    report = validate_raw_frame(df, schema)
    assert not report.has_errors

    ts = prepare_time_series(df, schema)
    featured = build_feature_frame(
        ts,
        target_col=schema.target_col,
        temperature_col="outside_temperature",
    )

    assert "hour" in featured.columns
    assert "heating_degree" in featured.columns
    assert "gas_consumption_lag_1" in featured.columns
    assert len(featured) == len(df)
