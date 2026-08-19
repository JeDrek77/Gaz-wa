import sqlite3
from pathlib import Path

from gaz_wa.config import DataSchema
from gaz_wa.data_loading import load_sql, load_table
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


def test_load_sql_from_sqlite_query_and_table(tmp_path: Path) -> None:
    db_path = tmp_path / "gas.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE gas_usage (
                timestamp TEXT NOT NULL,
                gas_consumption REAL NOT NULL,
                outside_temperature REAL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO gas_usage
            VALUES ('2026-01-01 00:00:00', 1200.0, 2.1)
            """
        )

    from_table = load_sql(sqlite_path=db_path, table_name="gas_usage")
    from_query = load_sql(
        sqlite_path=db_path,
        query="SELECT * FROM gas_usage WHERE gas_consumption > :min_value",
        params={"min_value": 1000},
    )

    assert len(from_table) == 1
    assert len(from_query) == 1
    assert from_query.loc[0, "gas_consumption"] == 1200.0
