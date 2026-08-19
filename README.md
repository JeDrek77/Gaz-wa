# Gaz-wa

Projekt do analizy i prognozowania zuzycia gazu przez jedna elektrocieplownie.

## Aktualny cel

Ten etap buduje suchy pipeline:

- ladowanie lokalnych danych z CSV/XLSX/Parquet,
- walidacja podstawowego schematu,
- feature engineering dla szeregow czasowych,
- raport EDA z wykresami i tabelami diagnostycznymi.

Nie wrzucaj danych firmowych do repozytorium. Trzymaj je lokalnie w `data/raw/`, ktore jest ignorowane przez git.

## Struktura

```text
data/
  raw/          # prywatne dane z pracy, poza git
  interim/      # dane po wstepnym czyszczeniu
  processed/    # zbiory gotowe do modelowania
  external/     # pogoda, swieta, inne zrodla zewnetrzne
notebooks/
  01_eda.ipynb  # miejsce na eksploracje w Jupyterze
src/gaz_wa/
  cli.py
  config.py
  data_loading.py
  validation.py
  features.py
  eda.py
```

## Start

```powershell
uv sync --extra dev
uv run gaz-wa inspect data/raw/twoj_plik.csv --timestamp-col timestamp --target-col gas_consumption
uv run gaz-wa make-report data/raw/twoj_plik.csv --timestamp-col timestamp --target-col gas_consumption --out-dir reports/eda
```

Jesli plik ma polskie nazwy kolumn, mozesz je podac wprost:

```powershell
uv run gaz-wa make-report data/raw/dane.xlsx --timestamp-col Data --target-col Zuzycie_gazu --sheet-name Arkusz1
```

## Dane z SQL

SQLite:

```powershell
uv run gaz-wa inspect-sql --sqlite-path data/raw/gaz.sqlite --table-name gas_usage --timestamp-col timestamp --target-col gas_consumption
uv run gaz-wa make-report-sql --sqlite-path data/raw/gaz.sqlite --query "SELECT * FROM gas_usage" --timestamp-col timestamp --target-col gas_consumption --out-dir reports/eda_sql
```

Inne bazy przez SQLAlchemy URL:

```powershell
uv run gaz-wa make-features-sql --database-url "postgresql+psycopg://user:password@host:5432/dbname" --query "SELECT * FROM gas_usage" --timestamp-col timestamp --target-col gas_consumption --out-path data/processed/sql_features.parquet
```

Hasel i connection stringow nie commituj do repo. Najlepiej trzymaj je w zmiennych srodowiskowych albo lokalnym `.env`, ktory jest ignorowany przez git.

## Minimalny wymagany schemat

Pipeline wymaga jednej kolumny czasu i jednej kolumny celu:

- `timestamp` albo inna kolumna z data/czasem,
- `gas_consumption` albo inna kolumna ze zuzyciem gazu.

Dodatkowe kolumny, ktore beda bardzo przydatne:

- temperatura zewnetrzna,
- produkcja ciepla,
- produkcja energii elektrycznej,
- status pracy bloku/kotla,
- postoje i awarie,
- prognoza pogody,
- zamowiona moc/cieplo,
- cena gazu lub tryb pracy instalacji.
