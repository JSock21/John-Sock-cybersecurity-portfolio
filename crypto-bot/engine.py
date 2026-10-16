"""Dip-and-bounce backtest engine (paper only).

Rules, evaluated on each candle:
  * Signal: the candle CLOSES at least X% below the highest high of the last N
    minutes (including this candle). The buy fills at the NEXT candle's open,
    so the backtest never uses information it would not have had.
  * Exits, checked on every candle from the entry candle onward:
      - stop-loss  at entry * (1 - Z%)
      - take-profit at entry * (1 + Y%)
      - if both could have been hit in the same candle, we assume the
        STOP was hit first (worst case);
      - if the candle opens beyond a level (a gap), the fill is at the open;
      - otherwise force-exit at the close once T minutes have passed.
  * Costs on EVERY buy and EVERY sell:
      - slippage: buy fills slip% higher, sell fills slip% lower;
      - fee: fee% of the dollar value traded (taker rate, both sides).
  * Fixed $ per trade, up to `max_pos` open at once, never more than the cash
    on hand. Open trades at the end of the window are closed at the last close.
"""
from __future__ import annotations

import numpy as np
from numba import njit

# indices into the stats vector returned by simulate()
TRADES, WINS, NET_PNL, FEES, MAX_DD_PCT, NOTIONAL, PNL_BEFORE_FEES, END_EQUITY, MAX_DD_USD = range(9)
N_STATS = 9


def rolling_high(high: np.ndarray, bars: int) -> np.ndarray:
    """Highest high over the last `bars` candles, including the current one."""
    from numpy.lib.stride_tricks import sliding_window_view
    out = np.empty_like(high)
    bars = max(1, min(bars, len(high)))
    out[bars - 1:] = sliding_window_view(high, bars).max(axis=1)
    if bars > 1:
        out[:bars - 1] = np.maximum.accumulate(high[:bars - 1])
    return out


@njit(cache=True)
def simulate(o, h, l, c, rh, start, end, bar_min,
             dip, tp, sl, hold_min, size, max_pos, cash0, fee, slip):
    """Run one backtest over candles [start, end). Percentages are fractions."""
    qty = np.zeros(max_pos)
    entry_px = np.zeros(max_pos)      # fill price incl. slippage
    entry_bar = np.zeros(max_pos, np.int64)
    entry_cost = np.zeros(max_pos)    # $ spent incl. buy fee
    stop_lv = np.zeros(max_pos)
    tp_lv = np.zeros(max_pos)
    open_ = np.zeros(max_pos, np.bool_)

    cash = cash0
    trades = 0
    wins = 0
    fees = 0.0
    notional = 0.0
    peak = cash0
    max_dd = 0.0
    max_dd_usd = 0.0
    pending = False   # signal fired on previous close -> buy at this open

    for i in range(start, end):
        # 1) execute a buy decided on the previous candle's close
        if pending:
            pending = False
            for k in range(max_pos):
                if not open_[k]:
                    px = o[i] * (1.0 + slip)
                    cost = size * (1.0 + fee)
                    if cash >= cost:
                        cash -= cost
                        f = size * fee
                        fees += f
                        notional += size
                        qty[k] = size / px
                        entry_px[k] = px
                        entry_bar[k] = i
                        entry_cost[k] = cost
                        # exit levels are relative to the actual fill price
                        stop_lv[k] = px * (1.0 - sl)
                        tp_lv[k] = px * (1.0 + tp)
                        open_[k] = True
                    break

        # 2) exits for every open position
        for k in range(max_pos):
            if not open_[k]:
                continue
            raw = -1.0
            if l[i] <= stop_lv[k]:
                raw = min(o[i], stop_lv[k]) if i > entry_bar[k] else stop_lv[k]
            elif h[i] >= tp_lv[k]:
                raw = max(o[i], tp_lv[k]) if i > entry_bar[k] else tp_lv[k]
            elif (i - entry_bar[k] + 1) * bar_min >= hold_min or i == end - 1:
                raw = c[i]
            if raw > 0.0:
                px = raw * (1.0 - slip)
                gross = qty[k] * px
                f = gross * fee
                fees += f
                notional += gross
                proceeds = gross - f
                cash += proceeds
                trades += 1
                if proceeds > entry_cost[k]:
                    wins += 1
                open_[k] = False

        # 3) mark-to-market equity and drawdown
        eq = cash
        for k in range(max_pos):
            if open_[k]:
                eq += qty[k] * c[i]
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak
        if dd > max_dd:
            max_dd = dd
        if peak - eq > max_dd_usd:
            max_dd_usd = peak - eq

        # 4) new signal on this close (acted on at next open)
        if i < end - 2 and c[i] <= rh[i] * (1.0 - dip):
            for k in range(max_pos):
                if not open_[k]:
                    pending = True
                    break

    out = np.zeros(N_STATS)
    out[TRADES] = trades
    out[WINS] = wins
    out[NET_PNL] = cash - cash0
    out[FEES] = fees
    out[MAX_DD_PCT] = max_dd * 100.0
    out[NOTIONAL] = notional
    out[PNL_BEFORE_FEES] = cash - cash0 + fees
    out[END_EQUITY] = cash
    out[MAX_DD_USD] = max_dd_usd
    return out


def buy_and_hold(o, c, start, end, cash0, fee, slip):
    """Put the whole balance in at the first open, sell at the last close."""
    px_in = o[start] * (1 + slip)
    spend = cash0 / (1 + fee)
    qty = spend / px_in
    gross = qty * c[end - 1] * (1 - slip)
    proceeds = gross * (1 - fee)
    equity = (cash0 - spend * (1 + fee)) + qty * np.asarray(c[start:end])
    peak = np.maximum.accumulate(equity)
    return {
        "net_pnl": proceeds - cash0,
        "fees": spend * fee + gross * fee,
        "max_dd_pct": float(((peak - equity) / peak).max() * 100),
    }


def break_even_fee(stats) -> float | None:
    """Per-side fee rate (as a %) at which this exact trade list nets $0.

    Trades don't depend on the fee rate (only the cash check does, which never
    binds at $100 trades on a $1,000 balance with one position), so
    net = pnl_before_fees - fee * notional  =>  fee* = pnl_before_fees / notional.
    Returns None when the strategy loses money even with zero fees.
    """
    if stats[NOTIONAL] <= 0 or stats[PNL_BEFORE_FEES] <= 0:
        return None
    return stats[PNL_BEFORE_FEES] / stats[NOTIONAL] * 100.0
