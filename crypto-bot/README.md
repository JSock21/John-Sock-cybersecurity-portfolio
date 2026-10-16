# crypto-bot — dip-and-bounce backtester

**Backtest only.** It uses Coinbase's public market data (no API keys, no account,
no auth). There is no live trading, no order placement and no key handling.

## Run it

```bash
cd crypto-bot
pip install -r requirements.txt
python run_backtest.py      # downloads 90 days of 1-min candles (cached in data/), sweeps, writes report.md
python -m pytest -q tests   # engine arithmetic checks on hand-made candles
```

The first run downloads about 2 × 90 × 5 requests (~2–4 minutes). Later runs read
`data/<PAIR>/<day>.csv.gz` and only fetch days that are missing.

## Files

| File | What it does |
|---|---|
| `config.yaml` | Every parameter: pairs, days, strategy defaults, fees, slippage, train/test split, sweep grid |
| `fetch_data.py` | Public candle download (Advanced Trade `/market/products/{id}/candles`, Exchange `/products/{id}/candles` as fallback), daily cache, gap filling, 5-minute resampling |
| `engine.py` | Numba-compiled trade simulator, buy-and-hold baseline, break-even fee math |
| `run_backtest.py` | Grid search on days 1–60, evaluation on held-out days 61–90, `report.md` writer |
| `report.md` | Generated, plain-English results |
| `results/sweep.csv` | Generated, every setting's train and test numbers |
