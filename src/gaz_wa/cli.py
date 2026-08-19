from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from gaz_wa.config import DataSchema
from gaz_wa.data_loading import load_table, normalize_columns
from gaz_wa.eda import save_eda_report
from gaz_wa.features import build_feature_frame
from gaz_wa.validation import prepare_time_series, validate_raw_frame

app = typer.Typer(help="Narzędzia do analizy zuzycia gazu.")


def _load_and_prepare(
    data_path: Path,
    timestamp_col: str,
    target_col: str,
    sheet_name: str | None,
    normalize: bool,
):
    df = load_table(data_path, sheet_name=sheet_name)
    if normalize:
        df = normalize_columns(df)
        timestamp_col = timestamp_col.strip().lower().replace(" ", "_").replace("-", "_")
        target_col = target_col.strip().lower().replace(" ", "_").replace("-", "_")
    schema = DataSchema(timestamp_col=timestamp_col, target_col=target_col)
    return df, schema


@app.command()
def inspect(
    data_path: Annotated[Path, typer.Argument(help="Sciezka do pliku CSV/XLSX/Parquet.")],
    timestamp_col: Annotated[str, typer.Option(help="Kolumna z data/czasem.")] = "timestamp",
    target_col: Annotated[str, typer.Option(help="Kolumna ze zuzyciem gazu.")] = "gas_consumption",
    sheet_name: Annotated[str | None, typer.Option(help="Nazwa arkusza dla Excela.")] = None,
    normalize: Annotated[bool, typer.Option(help="Ujednolic nazwy kolumn.")] = False,
) -> None:
    """Load data and print validation diagnostics."""
    df, schema = _load_and_prepare(data_path, timestamp_col, target_col, sheet_name, normalize)
    report = validate_raw_frame(df, schema)

    typer.echo(f"Wiersze: {report.rows}")
    typer.echo(f"Kolumny: {report.columns}")
    if not report.issues:
        typer.echo("Walidacja: brak problemow.")
        return

    typer.echo("Problemy:")
    for issue in report.issues:
        col = f"[{issue.column}] " if issue.column else ""
        typer.echo(f"- {issue.severity.upper()}: {col}{issue.message}")


@app.command()
def make_features(
    data_path: Annotated[Path, typer.Argument(help="Sciezka do pliku CSV/XLSX/Parquet.")],
    out_path: Annotated[Path, typer.Option(help="Gdzie zapisac plik z cechami.")] = Path(
        "data/processed/features.parquet"
    ),
    timestamp_col: Annotated[str, typer.Option(help="Kolumna z data/czasem.")] = "timestamp",
    target_col: Annotated[str, typer.Option(help="Kolumna ze zuzyciem gazu.")] = "gas_consumption",
    temperature_col: Annotated[
        str | None, typer.Option(help="Kolumna temperatury zewnetrznej.")
    ] = None,
    sheet_name: Annotated[str | None, typer.Option(help="Nazwa arkusza dla Excela.")] = None,
    normalize: Annotated[bool, typer.Option(help="Ujednolic nazwy kolumn.")] = False,
) -> None:
    """Build a feature table for modeling and save it as Parquet."""
    df, schema = _load_and_prepare(data_path, timestamp_col, target_col, sheet_name, normalize)
    report = validate_raw_frame(df, schema)
    if report.has_errors:
        for issue in report.issues:
            if issue.severity == "error":
                typer.echo(f"ERROR: {issue.message}")
        raise typer.Exit(code=1)

    ts = prepare_time_series(df, schema)
    featured = build_feature_frame(
        ts,
        target_col=schema.target_col,
        temperature_col=temperature_col,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    featured.to_parquet(out_path)
    typer.echo(f"Zapisano: {out_path}")


@app.command()
def make_report(
    data_path: Annotated[Path, typer.Argument(help="Sciezka do pliku CSV/XLSX/Parquet.")],
    out_dir: Annotated[Path, typer.Option(help="Katalog raportu EDA.")] = Path("reports/eda"),
    timestamp_col: Annotated[str, typer.Option(help="Kolumna z data/czasem.")] = "timestamp",
    target_col: Annotated[str, typer.Option(help="Kolumna ze zuzyciem gazu.")] = "gas_consumption",
    temperature_col: Annotated[
        str | None, typer.Option(help="Kolumna temperatury zewnetrznej.")
    ] = None,
    sheet_name: Annotated[str | None, typer.Option(help="Nazwa arkusza dla Excela.")] = None,
    normalize: Annotated[bool, typer.Option(help="Ujednolic nazwy kolumn.")] = False,
) -> None:
    """Create validation output, features, and EDA artifacts."""
    df, schema = _load_and_prepare(data_path, timestamp_col, target_col, sheet_name, normalize)
    report = validate_raw_frame(df, schema)
    for issue in report.issues:
        col = f"[{issue.column}] " if issue.column else ""
        typer.echo(f"{issue.severity.upper()}: {col}{issue.message}")

    if report.has_errors:
        raise typer.Exit(code=1)

    ts = prepare_time_series(df, schema)
    featured = build_feature_frame(
        ts,
        target_col=schema.target_col,
        temperature_col=temperature_col,
    )
    generated = save_eda_report(featured, target_col=schema.target_col, out_dir=out_dir)
    typer.echo("Wygenerowane pliki:")
    for path in generated:
        typer.echo(f"- {path}")
