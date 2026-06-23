# Trading Backtester — Base Architecture

The engine. Strategies plug into this; they are not part of the base.

## Data flow

```
<any>.parquet  ──parsers.h──►  vector<Candle>  ──►  Backtester  ──►  evaluate(strategy)
```

The file is **not** hardcoded — it's the single required command-line argument:

```
./backtester AAPL.parquet     # any parquet with the required columns
./backtester                  # error: usage: backtester <file.parquet>
```

Any parquet works as long as it has date/open/high/low/close/volume columns.

## 1. Data layer — `parsers.h`

- **`Candle`** — one bar of market data: `date`, OHLC, `adj_close`, `volume`, `label`,
  plus a `map` of `{"o","c","h","l","v"}` (+`"ac"` if adj_close present) for easy lookup by name.
- **`parquet_to_candles(file)`** — loads a `.parquet` into `vector<Candle>`.
  - Required columns: date, open, high, low, close, volume → missing any aborts the load (returns empty).
  - Optional columns: adj_close, label → missing just default to `-1` / `""`.
  - Type-flexible: `extract_double` / `extract_date` / `extract_label` handle int/float/double/string/dictionary.
- **`print_columns(file)`** — prints every column name + type in the file's schema (inspection only).
- **`parseCSV(file)`** — fallback loader from CSV (8 cols: date,open,high,low,close,adj_close,volume,label).

## 2. Strategy interface — the contract

```cpp
using Strategy = std::function<double(const std::vector<Candle>&, int day)>;
```

A strategy answers one question: **"what position today?"**
- return `+1` = full long, `-1` = full short, `0` = flat
- fractional (e.g. `0.5`) = sizing / partial position

It knows nothing about money, fees, or scoring. Pure decision.

## 3. Scoring engine — `Backtester::evaluate(name, strategy, fee)`

The ONE shared scorer. Written once, reused by every strategy. All "account" logic lives here:

- **Compounding** — runs a real balance: `equity *= (1 + pos * ret)` each day.
- **Trading costs** — pays `fee` per unit of turnover whenever the position changes
  (`equity *= 1 - fee * |pos - prev_pos|`). A full long→short flip costs 2×.
- **Reports** two numbers:
  - **P&L** — `(equity - 1) * 100%` — did it make money? (the real ruler)
  - **Directional accuracy** — % of days the side matched the move (sanity check only; ~50% = coin flip).

Default `fee = 0.001` (0.1%). Override per call to test cost sensitivity.

## 4. Shared helpers

- **`sma(tl, type, window, day)`** — simple moving average of a price field over a window. Reusable by any strategy.

## Build

Single-file via `cpp-run` (the VS Code button). It greps the source for `<arrow`
to auto-link `-larrow -lparquet`, so keep `#include <arrow/api.h>` in the file.

## Design principle

**Decision (strategy) is separated from evaluation (scorer).**
Add a new metric (Sharpe, drawdown) or cost model → edit `evaluate()` once, every strategy gets it free.
Add a new strategy → write one function returning a position, plug it into `main` with one line. No copy-paste.
