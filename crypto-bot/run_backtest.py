"""Download (or load cached) candles, run the parameter sweep, write report.md.

Usage:  python run_backtest.py
"""
from __future__ import annotations

import datetime as dt
import itertools
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

import engine as E
from fetch_data import load_pair, resample

ROOT = Path(__file__).parent
PARAMS = ["timeframe_min", "dip_pct", "lookback_min", "take_profit_pct", "stop_loss_pct", "max_hold_min"]


def prepare(cfg):
    """{(pair, tf): dict(arrays, train=(a,b), test=(a,b), dates)}"""
    d, sp = cfg["data"], cfg["split"]
    out = {}
    for pair in d["pairs"]:
        print(f"Loading {pair} ...", flush=True)
        m1 = load_pair(pair, d["days"], ROOT / d["cache_dir"])
        t0 = int(m1["time"].iloc[0])
        split_t = t0 + sp["train_days"] * 86400
        for tf in d["timeframes_min"]:
            df = resample(m1, tf)
            k = int(np.searchsorted(df["time"].values, split_t))
            out[(pair, tf)] = {
                "o": df["open"].to_numpy(float), "h": df["high"].to_numpy(float),
                "l": df["low"].to_numpy(float), "c": df["close"].to_numpy(float),
                "train": (0, k), "test": (k, len(df)),
                "times": df["time"].to_numpy(),
            }
    return out


def run_one(arr, rh, win, tf, p, s, costs):
    a, b = win
    return E.simulate(arr["o"], arr["h"], arr["l"], arr["c"], rh, a, b, tf,
                      p["dip_pct"] / 100, p["take_profit_pct"] / 100, p["stop_loss_pct"] / 100,
                      p["max_hold_min"], float(s["position_usd"]), int(s["max_open_positions"]),
                      float(s["starting_balance_usd"]),
                      costs["fee_pct_per_side"] / 100, costs["slippage_pct_per_side"] / 100)


def sweep(cfg, data):
    s, costs, g = cfg["strategy"], cfg["costs"], cfg["sweep"]
    pairs, tfs = cfg["data"]["pairs"], cfg["data"]["timeframes_min"]
    rows = []
    for tf in tfs:
        for N in g["lookback_min"]:
            bars = max(1, round(N / tf))
            rhs = {p: E.rolling_high(data[(p, tf)]["h"], bars) for p in pairs}
            for X, Y, Z, T in itertools.product(g["dip_pct"], g["take_profit_pct"],
                                                g["stop_loss_pct"], g["max_hold_min"]):
                p = dict(timeframe_min=tf, dip_pct=X, lookback_min=N,
                         take_profit_pct=Y, stop_loss_pct=Z, max_hold_min=T)
                row = dict(p)
                for pair in pairs:
                    for w in ("train", "test"):
                        st = run_one(data[(pair, tf)], rhs[pair], data[(pair, tf)][w], tf, p, s, costs)
                        for name, idx in (("trades", E.TRADES), ("wins", E.WINS), ("net", E.NET_PNL),
                                          ("fees", E.FEES), ("dd", E.MAX_DD_PCT), ("notional", E.NOTIONAL),
                                          ("gross", E.PNL_BEFORE_FEES)):
                            row[f"{w}_{pair}_{name}"] = st[idx]
                for w in ("train", "test"):
                    for name in ("trades", "wins", "net", "fees", "notional", "gross"):
                        row[f"{w}_{name}"] = sum(row[f"{w}_{pr}_{name}"] for pr in pairs)
                    row[f"{w}_dd"] = max(row[f"{w}_{pr}_dd"] for pr in pairs)
                rows.append(row)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- report

def money(x):
    return f"-${abs(x):,.2f}" if x < 0 else f"${x:,.2f}"


def pct(x, d=2):
    return f"{x:+.{d}f}%"


def describe(r):
    tf = "1-minute" if r.timeframe_min == 1 else f"{r.timeframe_min}-minute"
    return (f"{tf} candles · buy after a **{r.dip_pct:g}%** drop from the {r.lookback_min:g}-minute high · "
            f"take profit **+{r.take_profit_pct:g}%** · stop loss **-{r.stop_loss_pct:g}%** · "
            f"max hold **{r.max_hold_min:g} min**")


def be_fee(gross, notional):
    return None if notional <= 0 or gross <= 0 else gross / notional * 100


def results_table(df, w, pairs, capital):
    lines = ["| # | Trades | Win rate | Net P&L | Net P&L % | Fees paid | Max drawdown | Break-even fee/side |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for i, r in enumerate(df.itertuples(), 1):
        t, wn = getattr(r, f"{w}_trades"), getattr(r, f"{w}_wins")
        be = be_fee(getattr(r, f"{w}_gross"), getattr(r, f"{w}_notional"))
        lines.append(
            f"| {i} | {t:.0f} | {(wn / t * 100 if t else 0):.0f}% | {money(getattr(r, f'{w}_net'))} | "
            f"{pct(getattr(r, f'{w}_net') / capital * 100)} | {money(getattr(r, f'{w}_fees'))} | "
            f"{getattr(r, f'{w}_dd'):.1f}% | {'never (loses before fees)' if be is None else f'{be:.3f}%'} |")
    return "\n".join(lines)


def pair_breakdown(r, w, pairs, bal):
    out = []
    for pr in pairs:
        t, wn = getattr(r, f"{w}_{pr.replace('-', '_')}_trades"), getattr(r, f"{w}_{pr.replace('-', '_')}_wins")
        net = getattr(r, f"{w}_{pr.replace('-', '_')}_net")
        out.append(f"{pr}: {t:.0f} trades, {(wn / t * 100 if t else 0):.0f}% wins, {money(net)} "
                   f"({pct(net / bal * 100)}), fees {money(getattr(r, f'{w}_{pr.replace('-', '_')}_fees'))}, "
                   f"max drawdown {getattr(r, f'{w}_{pr.replace('-', '_')}_dd'):.1f}%")
    return "; ".join(out)


def write_report(cfg, data, res, elapsed):
    pairs = cfg["data"]["pairs"]
    s, costs, n = cfg["strategy"], cfg["costs"], cfg["sweep"]["top_n"]
    bal = float(s["starting_balance_usd"])
    capital = bal * len(pairs)
    res = res.rename(columns=lambda c: c.replace("-", "_"))

    tstamp = lambda t: dt.datetime.fromtimestamp(int(t), dt.timezone.utc).strftime("%Y-%m-%d")
    a1 = data[(pairs[0], 1)]
    tr0, tr1 = tstamp(a1["times"][0]), tstamp(a1["times"][a1["train"][1] - 1])
    te0, te1 = tstamp(a1["times"][a1["test"][0]]), tstamp(a1["times"][-1])

    # Honest selection: best on days 1-60 only, then look at days 61-90.
    # Settings that (almost) never trade "win" by sitting at $0, so they are not eligible.
    min_t = cfg["sweep"].get("min_trades", 10)
    eligible = res[res.train_trades >= min_t]
    if eligible.empty:
        raise SystemExit(f"No setting made at least {min_t} trades in training; widen the sweep.")
    picked = eligible.sort_values("train_net", ascending=False).head(n)
    # Hindsight: best on the held-out days themselves (optimistic, for reference only).
    hindsight = res[res.test_trades >= min_t].sort_values("test_net", ascending=False).head(n)

    # Buy-and-hold on the held-out window, per pair, full $1,000.
    bh = {}
    for pr in pairs:
        arr = data[(pr, 1)]
        a, b = arr["test"]
        bh[pr] = E.buy_and_hold(arr["o"], arr["c"], a, b, bal,
                                costs["fee_pct_per_side"] / 100, costs["slippage_pct_per_side"] / 100)
    bh_net = sum(v["net_pnl"] for v in bh.values())

    best = picked.iloc[0]
    n_profitable = int((picked["test_net"] > 0).sum())
    share_pos_train = (res["train_net"] > 0).mean() * 100
    share_pos_test = (res["test_net"] > 0).mean() * 100
    share_pos_gross = (res["test_gross"] > 0).mean() * 100
    best_gross_any = res.assign(be=res.test_gross / res.test_notional.where(res.test_notional > 0))
    best_be_any = best_gross_any["be"].max()
    fee = costs["fee_pct_per_side"]
    slip = costs["slippage_pct_per_side"]

    edge = best.test_net > 0 and n_profitable >= (n + 1) // 2
    fees_ate = (picked["test_gross"] > 0).any() and (picked["test_net"] <= 0).all()
    total_fees_best = best.test_fees

    if edge:
        verdict = (
            f"**Verdict: possibly yes, but treat it with suspicion.** The settings chosen using only days 1–60 "
            f"made {money(best.test_net)} ({pct(best.test_net / capital * 100)}) on the 30 held-out days after "
            f"{money(total_fees_best)} of fees, and {n_profitable} of the top {n} were profitable. Buy-and-hold "
            f"made {money(bh_net)} over the same days. One 30-day window is a small sample; this should be "
            f"re-tested on a different period before anyone trusts it.")
    else:
        verdict = (
            f"**Verdict: no — there is no real edge after fees.** The {n} settings that looked best on days 1–60 "
            f"{'all lost money' if n_profitable == 0 else f'mostly failed ({n_profitable} of {n} were profitable)'} "
            f"on the 30 held-out days; the top pick finished at {money(best.test_net)} "
            f"({pct(best.test_net / capital * 100)}) after paying {money(total_fees_best)} in fees, versus "
            f"{money(bh_net)} for simply buying and holding. Only {share_pos_test:.1f}% of all "
            f"{len(res):,} settings tried were profitable on the held-out days. "
            + (f"Before fees, {share_pos_gross:.0f}% of settings were in profit — fees and slippage are what turned "
               f"them into losers. " if share_pos_gross > share_pos_test + 5 else "")
            + f"At Coinbase's entry-level taker rate of {fee:.2f}% per side, each round trip costs about "
            f"{2 * (fee + slip):.1f}% of the trade before the price has to move at all, which is larger than the "
            f"small bounces this strategy tries to capture.")

    L = []
    L += ["# Dip-and-bounce backtest report", "",
          f"_Generated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC · {len(res):,} parameter sets tested "
          f"in {elapsed:.0f}s · paper trading only, no real orders._", "",
          "## The verdict", "", verdict, ""]
    if not edge:
        L += ["### What would the fee have to be to break even?", "",
              f"The last column in the tables below is the **per-side fee rate at which each setting would have "
              f"broken exactly even** on the held-out days, keeping slippage at {slip:.2f}% per side. "
              f"For comparison, the rate used here is **{fee:.2f}%**.", ""]
        bp = be_fee(best.test_gross, best.test_notional)
        top_line = ("loses money even with **zero** fees — no fee level rescues it." if bp is None
                    else f"breaks even at **{bp:.3f}%** per side (the {fee:.2f}% used here is "
                         f"{fee / bp:.1f}× that).")
        L += [f"- Top pick from training: {top_line}",
              f"- Best of all {len(res):,} settings, picked with hindsight on the held-out days: "
              + ("nothing broke even before fees." if not np.isfinite(best_be_any) or best_be_any <= 0
                 else f"breaks even at **{best_be_any:.3f}%** per side."),
              f"- For reference, the same third-party fee guides put Coinbase's lowest taker fee at about 0.05%, "
              f"and only for accounts trading hundreds of millions of dollars a month.", ""]

    L += ["## How the test worked", "",
          f"- **Data:** Coinbase public market data, 1-minute candles for {', '.join(pairs)}, "
          f"{tr0} to {te1} ({cfg['data']['days']} days). 5-minute candles were built from the same data.",
          f"- **Training (days 1–60):** {tr0} to {tr1}. All {len(res):,} settings were run here and ranked by profit.",
          f"- **Held-out test (days 61–90):** {te0} to {te1}. These days were never used to choose settings; "
          f"they show how the chosen settings would have done on new data.",
          f"- **Money:** ${bal:,.0f} paper balance per pair (${capital:,.0f} total), ${s['position_usd']} per trade, "
          f"at most {s['max_open_positions']} open trade per pair.",
          "- **Entry:** when a candle closes X% below the highest price of the last N minutes, buy at the next "
          "candle's opening price.",
          "- **Exit:** take-profit at +Y%, stop-loss at −Z%, or sell at market after T minutes, whichever comes "
          "first. If a candle touches both the stop and the target, we assume the stop was hit (worst case).",
          f"- **Settings tried:** X = {cfg['sweep']['dip_pct']}%, Y = {cfg['sweep']['take_profit_pct']}%, "
          f"Z = {cfg['sweep']['stop_loss_pct']}%, N = {cfg['sweep']['lookback_min']} min, "
          f"T = {cfg['sweep']['max_hold_min']} min, on both 1- and 5-minute candles.", "",
          "## Fees and slippage used", "",
          f"- **Trading fee: {fee:.2f}% on every buy and every sell** — the *taker* rate for Coinbase Advanced "
          f"Trade's lowest volume tier ($0–$10K traded in the last 30 days). Taker on both sides is the worst "
          f"case (market orders); the same tier's maker rate is 0.40%.",
          "- Source: Coinbase Advanced Trade's fee schedule as summarised by 2026 third-party guides "
          "(financer.com Coinbase review; coincodecap.com Coinbase fees guide), which list 0.40% maker / "
          "0.60% taker for the under-$10K tier. Coinbase's own fee page (coinbase.com/advanced-fees) could not "
          "be reached when this tool was built, so **check the live schedule and update `config.yaml` if it "
          "differs.**",
          f"- **Slippage: {slip:.2f}% per side** — buys fill {slip:.2f}% above the candle price, sells "
          f"{slip:.2f}% below.",
          f"- So every round trip costs about **{2 * (fee + slip):.2f}%** of the trade amount before any price move.",
          ""]

    L += [f"## Top {n} settings (picked on days 1–60) — results on the held-out days 61–90", "",
          f"This is the honest test: settings were chosen without seeing these days. Only settings that made "
          f"at least {min_t} trades during training were eligible.", "",
          results_table(picked, "test", pairs, capital), ""]
    for i, r in enumerate(picked.itertuples(), 1):
        L += [f"{i}. {describe(r)}  ",
              f"   Training (days 1–60) result was {money(r.train_net)} over {r.train_trades:.0f} trades.  ",
              f"   Held-out by pair — {pair_breakdown(r, 'test', pairs, bal)}", ""]

    L += ["## Side by side with buy-and-hold (held-out days 61–90)", "",
          "| Approach | Net P&L | Net P&L % | Fees paid | Max drawdown |", "|---|---:|---:|---:|---:|",
          f"| Top pick above (both pairs) | {money(best.test_net)} | {pct(best.test_net / capital * 100)} | "
          f"{money(best.test_fees)} | {best.test_dd:.1f}% |"]
    for pr in pairs:
        v = bh[pr]
        L += [f"| Buy & hold {pr} (${bal:,.0f}) | {money(v['net_pnl'])} | {pct(v['net_pnl'] / bal * 100)} | "
              f"{money(v['fees'])} | {v['max_dd_pct']:.1f}% |"]
    L += [f"| Buy & hold both | {money(bh_net)} | {pct(bh_net / capital * 100)} | "
          f"{money(sum(v['fees'] for v in bh.values()))} | — |", "",
          f"Note: the strategy only ever has ${s['position_usd']} of each ${bal:,.0f} invested, while buy-and-hold "
          f"has all of it in the market, so buy-and-hold's gains *and* losses are naturally much larger.", ""]

    L += [f"## For reference: top {n} with hindsight (picked directly on days 61–90)", "",
          "These are the best settings *after the fact*. Picking settings this way is overfitting: it "
          "flatters the strategy, because nobody could have known these settings in advance.", "",
          results_table(hindsight, "test", pairs, capital), ""]
    for i, r in enumerate(hindsight.itertuples(), 1):
        L += [f"{i}. {describe(r)} (days 1–60: {money(r.train_net)})"]
    L += ["", "## Overfitting check", "",
          f"- Share of all settings that were profitable on training days: **{share_pos_train:.1f}%**; "
          f"on the held-out days: **{share_pos_test:.1f}%**.",
          f"- Share profitable on held-out days if fees were zero (slippage kept): **{share_pos_gross:.1f}%**.",
          f"- The top training pick went from {money(best.train_net)} (training) to {money(best.test_net)} (held-out).",
          "", "## Default settings from config.yaml", ""]
    dflt = res[(res.timeframe_min == 1) & (res.dip_pct == s["dip_pct"]) & (res.lookback_min == s["lookback_min"])
               & (res.take_profit_pct == s["take_profit_pct"]) & (res.stop_loss_pct == s["stop_loss_pct"])
               & (res.max_hold_min == s["max_hold_min"])]
    if len(dflt):
        L += [describe(dflt.iloc[0]), "", results_table(dflt, "test", pairs, capital), ""]
    else:
        L += ["(Default settings are not on the sweep grid, so they were not run.)", ""]
    L += ["## Limits of this test", "",
          "- 1-minute candles don't show the order of prices inside the minute; we assume the worse outcome "
          "when a stop and target are both touched.",
          "- Real fills during sharp drops can be worse than the 0.05% slippage assumed.",
          "- 90 days is one market regime. A strategy can look fine in one period and fail in the next.",
          "- Full per-setting results are in `results/sweep.csv`.", ""]
    (ROOT / "report.md").write_text("\n".join(L))


def main():
    cfg = yaml.safe_load(open(ROOT / "config.yaml"))
    t = time.time()
    data = prepare(cfg)
    print("Running sweep ...", flush=True)
    res = sweep(cfg, data)
    (ROOT / "results").mkdir(exist_ok=True)
    res.to_csv(ROOT / "results" / "sweep.csv", index=False)
    write_report(cfg, data, res, time.time() - t)
    print("Wrote report.md and results/sweep.csv")


if __name__ == "__main__":
    main()
