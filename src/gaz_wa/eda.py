from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def describe_frame(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    numeric = df.select_dtypes(include="number")
    return {
        "preview": df.head(20),
        "dtypes": pd.DataFrame({"column": df.columns, "dtype": df.dtypes.astype(str).values}),
        "missing": (
            df.isna()
            .sum()
            .rename("missing_count")
            .to_frame()
            .assign(missing_share=lambda frame: frame["missing_count"] / max(len(df), 1))
            .sort_values("missing_count", ascending=False)
        ),
        "numeric_summary": numeric.describe().T if not numeric.empty else pd.DataFrame(),
    }


def save_eda_report(
    df: pd.DataFrame,
    *,
    target_col: str,
    out_dir: str | Path,
) -> list[Path]:
    """Save core EDA tables and plots. Returns paths to generated files."""
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    tables = describe_frame(df)
    for name, table in tables.items():
        path = output / f"{name}.csv"
        table.to_csv(path, index=name in {"preview", "dtypes"})
        generated.append(path)

    if target_col not in df.columns:
        return generated

    target = pd.to_numeric(df[target_col], errors="coerce")

    fig, ax = plt.subplots(figsize=(14, 5))
    target.plot(ax=ax, title=f"{target_col}: przebieg w czasie")
    ax.set_xlabel("czas")
    ax.set_ylabel(target_col)
    fig.tight_layout()
    path = output / "target_timeseries.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    generated.append(path)

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.histplot(target.dropna(), kde=True, ax=ax)
    ax.set_title(f"{target_col}: rozklad")
    fig.tight_layout()
    path = output / "target_distribution.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    generated.append(path)

    numeric = df.select_dtypes(include="number")
    if len(numeric.columns) >= 2:
        corr = numeric.corr(numeric_only=True)
        corr.to_csv(output / "correlations.csv")
        generated.append(output / "correlations.csv")

        fig, ax = plt.subplots(figsize=(max(8, len(corr) * 0.6), max(6, len(corr) * 0.5)))
        sns.heatmap(corr, cmap="vlag", center=0, ax=ax)
        ax.set_title("Korelacje zmiennych numerycznych")
        fig.tight_layout()
        path = output / "correlations_heatmap.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        generated.append(path)

    return generated
