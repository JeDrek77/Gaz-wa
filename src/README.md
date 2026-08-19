# Opis kodu w folderze src

Ten folder zawiera kod aplikacji `gaz_wa`, czyli suchy pipeline do wczytywania,
walidowania, opisywania i wzbogacania danych o zuzyciu gazu. Notebooki sluza do
eksploracji, ale logika projektu mieszka tutaj, w zwyklych plikach `.py`.

## Struktura

```text
src/
  gaz_wa/
    __init__.py
    cli.py
    config.py
    data_loading.py
    eda.py
    features.py
    validation.py
```

## Jak plyna dane przez projekt

Typowy przeplyw wyglada tak:

```text
CSV/XLSX/Parquet/SQL
  -> data_loading.py
  -> validation.py
  -> features.py
  -> eda.py albo zapis do data/processed
  -> cli.py jako wygodny interfejs z terminala
```

Najpierw dane sa wczytywane do `pandas.DataFrame`. Potem pipeline sprawdza, czy
istnieje kolumna czasu i kolumna celu, czy daty daja sie sparsowac, czy sa braki,
duplikaty i podejrzane wartosci. Nastepnie dane sa sortowane po czasie i dostaja
`DatetimeIndex`, co jest potrzebne do cech czasowych, lagow i statystyk kroczacych.

## `__init__.py`

Ten plik oznacza `src/gaz_wa` jako pakiet Pythona. Dzieki temu mozna importowac
moduly tak:

```python
from gaz_wa.data_loading import load_table
```

Przechowuje tez numer wersji pakietu:

```python
__version__ = "0.1.0"
```

Na tym etapie nie ma tu logiki biznesowej.

## `config.py`

Ten plik trzyma podstawowa konfiguracje wspolna dla kilku modulow.

Najwazniejsze stale:

- `PROJECT_ROOT` wskazuje katalog glowny projektu.
- `DATA_DIR` wskazuje katalog `data`.
- `REPORTS_DIR` wskazuje katalog `reports`.

Najwazniejsze klasy:

- `DataSchema` opisuje, ktore kolumny sa kluczowe:
  - `timestamp_col`, domyslnie `timestamp`,
  - `target_col`, domyslnie `gas_consumption`,
  - `freq`, czyli przyszla czestotliwosc szeregu, obecnie opcjonalna.
- `ReportConfig` opisuje ustawienia raportow i cech:
  - `rolling_windows=(24, 168)`,
  - `lags=(1, 2, 3, 24, 48, 168)`,
  - `max_categories=20`.

Przy danych godzinowych lag `24` oznacza wartosc sprzed doby, a `168` wartosc
sprzed tygodnia. To bardzo przydatne przy zuzyciu gazu, bo takie dane zwykle maja
silna sezonowosc dobowa i tygodniowa.

## `data_loading.py`

Ten plik odpowiada tylko za wczytywanie danych i lekkie porzadkowanie nazw kolumn.
Nie powinien trenowac modeli ani robic wykresow.

### `load_table()`

Wczytuje dane z plikow:

- `.csv`,
- `.xlsx`,
- `.xls`,
- `.parquet`.

Zwraca `pandas.DataFrame`.

Przyklad:

```python
from gaz_wa.data_loading import load_table

df = load_table("data/raw/dane.csv")
```

Dla Excela mozna wskazac arkusz:

```python
df = load_table("data/raw/dane.xlsx", sheet_name="Arkusz1")
```

### `load_sql()`

Wczytuje dane z SQL. Funkcja wymaga dokladnie jednego zrodla polaczenia:

- `sqlite_path`, jesli to plik SQLite,
- `database_url`, jesli to inna baza przez SQLAlchemy.

Wymaga tez dokladnie jednego sposobu wyboru danych:

- `table_name`, jesli chcesz cala tabele,
- `query`, jesli chcesz wynik zapytania SQL.

Przyklad SQLite:

```python
from gaz_wa.data_loading import load_sql

df = load_sql(
    sqlite_path="data/raw/gaz.sqlite",
    table_name="gas_usage",
)
```

Przyklad SQLite z zapytaniem:

```python
df = load_sql(
    sqlite_path="data/raw/gaz.sqlite",
    query="SELECT * FROM gas_usage WHERE timestamp >= :start_date",
    params={"start_date": "2026-01-01"},
)
```

Przyklad PostgreSQL:

```python
df = load_sql(
    database_url="postgresql+psycopg://user:password@host:5432/dbname",
    query="SELECT * FROM gas_usage",
)
```

Hasel i connection stringow nie nalezy commitowac do repozytorium.

### `normalize_columns()`

Ujednolica nazwy kolumn:

- usuwa spacje z poczatku i konca,
- zamienia litery na male,
- zamienia spacje i myslniki na `_`.

Przyklad:

```text
"Zuzycie gazu" -> "zuzycie_gazu"
"Data-czas" -> "data_czas"
```

## `validation.py`

Ten plik odpowiada za kontrole jakosci danych przed dalsza analiza.

### `ValidationIssue`

Opisuje jeden problem z danymi:

- `severity`: `error` albo `warning`,
- `column`: nazwa kolumny albo `None`,
- `message`: czytelny opis problemu.

### `ValidationReport`

Zbiera wynik walidacji:

- liczbe wierszy,
- liczbe kolumn,
- liste problemow.

Ma tez pomocnicza wlasciwosc `has_errors`, ktora mowi, czy wykryto blad blokujacy
dalszy pipeline.

### `validate_raw_frame()`

Sprawdza surowy `DataFrame`:

- czy dane nie sa puste,
- czy istnieje kolumna czasu,
- czy istnieje kolumna celu,
- czy daty daja sie sparsowac,
- czy sa zduplikowane timestampy,
- czy timestampy sa posortowane,
- czy cel jest numeryczny,
- czy cel ma wartosci ujemne,
- ile jest brakow danych w kazdej kolumnie.

Bledy `error` zatrzymuja pipeline w komendach CLI. Ostrzezenia `warning` sa
drukowane, ale nie blokuja pracy.

### `prepare_time_series()`

Przygotowuje dane do pracy jako szereg czasowy:

- parsuje kolumne czasu do typu datetime,
- zamienia kolumne celu na wartosci numeryczne,
- sortuje dane po czasie,
- ustawia czas jako indeks `DatetimeIndex`.

To jest wazny krok przed feature engineeringiem.

## `features.py`

Ten plik tworzy cechy, ktore pozniej beda uzywane w analizie albo modelach
prognostycznych.

### `add_time_features()`

Dodaje cechy kalendarzowe:

- godzina,
- dzien tygodnia,
- dzien miesiaca,
- dzien roku,
- tydzien roku,
- miesiac,
- kwartal,
- rok,
- weekend,
- swieto w Polsce,
- sezon grzewczy.

Dodaje tez cechy cykliczne `sin/cos`, np. dla godziny i miesiaca. To pomaga
modelom zrozumiec, ze godzina `23` jest blisko godziny `0`, a grudzien jest blisko
stycznia.

### `add_lag_features()`

Dodaje opoznienia kolumny celu, np.:

- `gas_consumption_lag_1`,
- `gas_consumption_lag_24`,
- `gas_consumption_lag_168`.

Dla danych godzinowych oznacza to odpowiednio poprzednia godzine, poprzednia dobe
i poprzedni tydzien.

Dodaje tez statystyki kroczace z przesunieciem o jeden krok:

- srednia kroczaca,
- odchylenie standardowe,
- minimum,
- maksimum.

Przesuniecie o jeden krok jest celowe, bo ogranicza wyciek informacji z przyszlosci
do cech modelu.

### `add_weather_like_features()`

Jesli dostepna jest temperatura zewnetrzna, funkcja dodaje:

- `heating_degree`,
- `cooling_degree`.

Przy domyslnej temperaturze bazowej `15.0`, `heating_degree` rosnie wtedy, gdy na
zewnatrz jest zimniej niz 15 stopni. To bardzo sensowna cecha dla elektrocieplowni,
bo zapotrzebowanie na cieplo i gaz zwykle mocno zalezy od temperatury.

### `build_feature_frame()`

To funkcja spinajaca caly feature engineering:

```text
add_time_features()
  -> add_weather_like_features()
  -> add_lag_features()
```

Najczesciej to wlasnie jej bedziesz uzywal w notebookach i CLI.

## `eda.py`

Ten plik sluzy do podstawowej eksploracji danych i raportow.

### `describe_frame()`

Zwraca slownik tabel diagnostycznych:

- `preview`: pierwsze 20 wierszy,
- `dtypes`: typy kolumn,
- `missing`: liczba i udzial brakow danych,
- `numeric_summary`: statystyki opisowe dla kolumn numerycznych.

### `save_eda_report()`

Zapisuje raport EDA do katalogu, np. `reports/eda`.

Tworzy pliki:

- `preview.csv`,
- `dtypes.csv`,
- `missing.csv`,
- `numeric_summary.csv`,
- `target_timeseries.png`,
- `target_distribution.png`,
- `correlations.csv`,
- `correlations_heatmap.png`.

Dzieki temu mozna szybko zobaczyc, czy dane wygladaja zdrowo, zanim zacznie sie
trenowanie modelu.

## `cli.py`

Ten plik wystawia caly pipeline jako komendy terminalowe przez `typer`.

Glowne komendy dla plikow:

```powershell
py -m uv run gaz-wa inspect data/raw/dane.csv --timestamp-col timestamp --target-col gas_consumption
py -m uv run gaz-wa make-report data/raw/dane.csv --timestamp-col timestamp --target-col gas_consumption --out-dir reports/eda
py -m uv run gaz-wa make-features data/raw/dane.csv --timestamp-col timestamp --target-col gas_consumption --out-path data/processed/features.parquet
```

Glowne komendy dla SQL:

```powershell
py -m uv run gaz-wa inspect-sql --sqlite-path data/raw/gaz.sqlite --table-name gas_usage --timestamp-col timestamp --target-col gas_consumption
py -m uv run gaz-wa make-report-sql --sqlite-path data/raw/gaz.sqlite --query "SELECT * FROM gas_usage" --timestamp-col timestamp --target-col gas_consumption --out-dir reports/eda_sql
py -m uv run gaz-wa make-features-sql --sqlite-path data/raw/gaz.sqlite --table-name gas_usage --timestamp-col timestamp --target-col gas_consumption --out-path data/processed/sql_features.parquet
```

Wewnetrzne funkcje pomocnicze w `cli.py`:

- `_load_and_prepare()` wczytuje plik i buduje `DataSchema`,
- `_prepare_schema_and_columns()` opcjonalnie normalizuje nazwy kolumn,
- `_load_sql_and_prepare()` wczytuje dane z SQL i buduje `DataSchema`.

## Co warto dodac jako nastepne

Najbardziej naturalne kolejne moduly to:

- `models.py` z baseline i pierwszym modelem ML,
- `backtesting.py` z walidacja czasowa,
- `metrics.py` z MAE, RMSE, MAPE/sMAPE i bledem sumy dobowej,
- `weather.py` do pobierania lub laczenia danych pogodowych,
- `schemas.py` z dokladniejszym kontraktem danych wejsciowych.

Na razie `src` jest fundamentem pod eksploracje i przygotowanie danych. Modelowanie
powinno dojsc dopiero po obejrzeniu realnych rozkladow, brakow, sezonowosci i
anomalii w danych.
