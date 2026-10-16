"""Download and cache 1-minute candles from Coinbase PUBLIC market data.

No API keys, no account, no auth. Read-only GET requests to:
  1. Coinbase Advanced Trade public market endpoint (preferred)
       GET https://api.coinbase.com/api/v3/brokerage/market/products/{id}/candles
  2. Coinbase Exchange public candles endpoint (fallback)
       GET https://api.exchange.coinbase.com/products/{id}/candles

Candles are cached per pair per UTC day in data/<PAIR>/<YYYY-MM-DD>.csv.gz, so
re-runs only download days that are not already on disk.
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ADV_URL = "https://api.coinbase.com/api/v3/brokerage/market/products/{pid}/candles"
EXC_URL = "https://api.exchange.coinbase.com/products/{pid}/candles"
ADV_MAX = 350   # max candles per request on the Advanced Trade endpoint
EXC_MAX = 300   # max candles per request on the Exchange endpoint
COLS = ["time", "open", "high", "low", "close", "volume"]

_session = requests.Session()
_session.headers["User-Agent"] = "crypto-bot-backtester/1.0"


def _get(url: str, params: dict) -> requests.Response:
    for attempt in range(6):
        r = _session.get(url, params=params, timeout=30)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()
    return r


def _fetch_chunk_adv(pid: str, start: int, end: int) -> list[list]:
    r = _get(ADV_URL.format(pid=pid), {
        "start": str(start), "end": str(end),
        "granularity": "ONE_MINUTE", "limit": str(ADV_MAX)})
    return [[int(c["start"]), float(c["open"]), float(c["high"]), float(c["low"]),
             float(c["close"]), float(c["volume"])] for c in r.json().get("candles", [])]


def _fetch_chunk_exc(pid: str, start: int, end: int) -> list[list]:
    iso = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat()
    r = _get(EXC_URL.format(pid=pid), {"granularity": 60, "start": iso(start), "end": iso(end)})
    # Exchange format: [time, low, high, open, close, volume]
    return [[int(t), float(o), float(h), float(l), float(c), float(v)]
            for t, l, h, o, c, v in r.json()]


def fetch_day(pid: str, day: dt.date) -> pd.DataFrame:
    """All 1-minute candles for one UTC day (1440 rows, gaps filled)."""
    day_start = int(dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone.utc).timestamp())
    day_end = day_start + 86400
    rows: list[list] = []
    try:
        fetch, step = _fetch_chunk_adv, ADV_MAX * 60
        fetch(pid, day_start, day_start + 60)  # probe the preferred endpoint
    except requests.RequestException:
        fetch, step = _fetch_chunk_exc, EXC_MAX * 60
    t = day_start
    while t < day_end:
        end = min(t + step, day_end)
        # Advanced Trade's `end` is inclusive; ask for [t, end - 60] to avoid overlap.
        rows += fetch(pid, t, end - 60)
        t = end
        time.sleep(0.12)  # stay well under the public rate limit
    return _fill_gaps(pd.DataFrame(rows, columns=COLS), day_start, day_end)


def _fill_gaps(df: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    """Coinbase omits minutes with no trades. Insert them as flat, zero-volume bars."""
    grid = pd.Index(range(start, end, 60), name="time")
    df = df.drop_duplicates("time").set_index("time").sort_index().reindex(grid)
    df["close"] = df["close"].ffill()
    for c in ("open", "high", "low"):
        df[c] = df[c].fillna(df["close"])
    df["volume"] = df["volume"].fillna(0.0)
    return df.reset_index()


def load_pair(pid: str, days: int, cache_dir: Path) -> pd.DataFrame:
    """Return `days` full UTC days of 1-minute candles ending yesterday (UTC)."""
    today = dt.datetime.now(dt.timezone.utc).date()
    wanted = [today - dt.timedelta(days=d) for d in range(days, 0, -1)]
    pair_dir = cache_dir / pid
    pair_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for i, day in enumerate(wanted, 1):
        f = pair_dir / f"{day.isoformat()}.csv.gz"
        if f.exists():
            df = pd.read_csv(f)
        else:
            print(f"  {pid} {day} ({i}/{len(wanted)}) downloading...", flush=True)
            df = fetch_day(pid, day)
            df.to_csv(f, index=False)
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out = out.dropna(subset=["close"])  # only possible if a pair had no trades at all yet
    return out.reset_index(drop=True)


def resample(df1m: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """Build N-minute candles from 1-minute candles."""
    if minutes == 1:
        return df1m
    g = df1m.groupby(df1m["time"] // (minutes * 60) * (minutes * 60))
    return pd.DataFrame({
        "time": g["time"].first().index,
        "open": g["open"].first().values,
        "high": g["high"].max().values,
        "low": g["low"].min().values,
        "close": g["close"].last().values,
        "volume": g["volume"].sum().values,
    })


if __name__ == "__main__":
    import yaml
    cfg = yaml.safe_load(open(Path(__file__).with_name("config.yaml")))
    cache = Path(__file__).parent / cfg["data"]["cache_dir"]
    for p in cfg["data"]["pairs"]:
        d = load_pair(p, cfg["data"]["days"], cache)
        print(f"{p}: {len(d)} one-minute candles cached", file=sys.stderr)
