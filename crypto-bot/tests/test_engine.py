"""Hand-checkable tests for the backtest engine, on made-up candles.

These synthetic candles exist only to verify the arithmetic; they are never
used for the report.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine as E  # noqa: E402
from fetch_data import _fill_gaps, resample  # noqa: E402

FEE, SLIP = 0.006, 0.0005


def run(o, h, l, c, dip=0.01, tp=0.01, sl=0.02, hold=1000, lookback=3, max_pos=1, fee=FEE, slip=SLIP):
    o, h, l, c = map(lambda a: np.asarray(a, float), (o, h, l, c))
    rh = E.rolling_high(h, lookback)
    return E.simulate(o, h, l, c, rh, 0, len(c), 1, dip, tp, sl, hold, 100.0, max_pos, 1000.0, fee, slip)


def test_rolling_high():
    assert E.rolling_high(np.array([1., 3, 2, 1, 0.5]), 2).tolist() == [1, 3, 3, 2, 1]


def test_take_profit_trade_fees_on_both_sides():
    # bar0 high 100; bar1 closes 98.5 (-1.5%) -> signal; bar2 opens 98.5 -> buy; bar3 high hits TP
    o = [100, 99, 98.5, 99.0, 99]
    h = [100, 99, 98.6, 100.0, 99]
    l = [100, 98.5, 98.4, 98.9, 99]
    c = [100, 98.5, 98.5, 99.5, 99]
    st = run(o, h, l, c)
    buy = 98.5 * (1 + SLIP)
    qty = 100 / buy
    tp_px = buy * 1.01
    sell = tp_px * (1 - SLIP)
    gross = qty * sell
    exp_net = gross * (1 - FEE) - 100 * (1 + FEE)
    assert st[E.TRADES] == 1 and st[E.WINS] == (exp_net > 0)
    assert st[E.NET_PNL] == pytest.approx(exp_net)
    assert st[E.FEES] == pytest.approx(100 * FEE + gross * FEE)
    # break-even fee reproduces zero net P&L
    be = E.break_even_fee(st) / 100
    st0 = run(o, h, l, c, fee=be)
    assert st0[E.NET_PNL] == pytest.approx(0, abs=1e-9)


def test_stop_wins_when_bar_touches_both():
    o = [100, 99, 98.5, 98.5]
    h = [100, 99, 98.6, 110]
    l = [100, 98.5, 98.4, 90]
    c = [100, 98.5, 98.5, 100]
    st = run(o, h, l, c, sl=0.02)
    buy = 98.5 * (1 + SLIP)
    exp = (100 / buy) * buy * 0.98 * (1 - SLIP) * (1 - FEE) - 100 * (1 + FEE)
    assert st[E.TRADES] == 1 and st[E.WINS] == 0
    assert st[E.NET_PNL] == pytest.approx(exp)


def test_gap_down_fills_at_open():
    o = [100, 99, 98.5, 90]
    h = [100, 99, 98.6, 91]
    l = [100, 98.5, 98.4, 89]
    c = [100, 98.5, 98.5, 90]
    st = run(o, h, l, c)
    buy = 98.5 * (1 + SLIP)
    exp = (100 / buy) * 90 * (1 - SLIP) * (1 - FEE) - 100 * (1 + FEE)
    assert st[E.NET_PNL] == pytest.approx(exp)


def test_max_hold_exit_and_no_lookahead():
    # Entry happens on the bar AFTER the signal, never on the signal bar.
    o = [100, 99, 98.5, 98.6, 98.7, 98.8]
    h = [100, 99, 98.6, 98.7, 98.8, 98.9]
    l = [100, 98.5, 98.4, 98.5, 98.6, 98.7]
    c = [100, 98.5, 98.6, 98.7, 98.8, 98.8]
    st = run(o, h, l, c, hold=2, tp=0.05, sl=0.05, lookback=10)
    buy = 98.5 * (1 + SLIP)            # bar2 open
    sell = 98.7 * (1 - SLIP)           # bar3 close, held 2 minutes
    first = (100 / buy) * sell * (1 - FEE) - 100 * (1 + FEE)
    assert st[E.TRADES] >= 1
    assert st[E.FEES] > 0
    # with only one open position allowed, first trade P&L is reproducible on a truncated series
    st1 = run(o[:4], h[:4], l[:4], c[:4], hold=2, tp=0.05, sl=0.05, lookback=10)
    assert st1[E.NET_PNL] == pytest.approx(first)


def test_fill_gaps_and_resample():
    import pandas as pd
    df = pd.DataFrame([[0, 1, 2, 0.5, 1.5, 3], [120, 2, 3, 1, 2.5, 1]],
                      columns=["time", "open", "high", "low", "close", "volume"])
    f = _fill_gaps(df, 0, 300)
    assert f["time"].tolist() == [0, 60, 120, 180, 240]
    assert f.loc[1, ["open", "high", "low", "close", "volume"]].tolist() == [1.5, 1.5, 1.5, 1.5, 0]
    r = resample(f, 5)
    assert len(r) == 1 and r.loc[0, "open"] == 1 and r.loc[0, "high"] == 3 and r.loc[0, "low"] == 0.5
    assert r.loc[0, "close"] == 2.5 and r.loc[0, "volume"] == 4
