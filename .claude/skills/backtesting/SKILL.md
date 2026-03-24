---
name: backtesting
description: Specialized backtesting skill for algorithmic trading strategies on Phemex exchange. Use when user wants to backtest trading strategies, analyze historical data, or fetch market data for testing.
---

# Skill: Backtesting

## Description
You are a specialized backtesting skill for algorithmic trading strategies. You specialize in
backtesting against the Phemex exchange.

## Data Fetching

### Fetch Raw Data
Use `fetch_phemex_data.py` to fetch raw market data:

```bash
# Fetch last 10 days
python fetch_phemex_data.py

# Fetch specific date range
python fetch_phemex_data.py --start-date 2025-07-01 --end-date 2025-07-14
```

### Enhance Data
Use `fetch_and_enhance_data.py` to add technical indicators:

```bash
# Enhance existing CSV
python fetch_and_enhance_data.py --csv backtesting_data/raw_data.csv
```

## Output Format

All output CSV files should be stored in `./backtesting_data/` directory.

### Naming Convention
- Include coin name
- Include date range
- Optional: arbitrary descriptive name

### Required Columns
The output CSV must contain these columns:
- timestamp, open, high, low, close, volume, datetime
- short_macd, short_macd_signal, short_macd_histogram, short_color
- medium_macd, medium_macd_signal, medium_macd_histogram, medium_color
- long_macd, long_macd_signal, long_macd_histogram, long_color
- adx, dmi_positive, dmi_negative, chop, atr, rsi, ema

## Workflow

1. Determine data requirements (coin, date range)
2. Fetch raw data using fetch_phemex_data.py
3. Enhance data with technical indicators
4. Run backtest against strategy
5. Analyze results

## Examples

### Example 1: Full Backtest Workflow
```bash
# Fetch 30 days of FARTCOIN data
python fetch_phemex_data.py --coin FARTCOIN --days 30

# Enhance the data
python fetch_and_enhance_data.py --csv backtesting_data/FARTCOIN_latest.csv

# Run backtest
python preserve_python/backtesting/improved_signal_strategy.py
```

### Example 2: Custom Date Range
```bash
# Fetch specific range
python fetch_phemex_data.py --start-date 2025-06-01 --end-date 2025-07-01
```