# Dip-and-bounce backtest report

_Generated 2026-10-16 04:53 UTC · 17,640 parameter sets tested in 263s · paper trading only, no real orders._

## The verdict

**Verdict: no — there is no real edge after fees.** The 5 settings that looked best on days 1–60 all lost money on the 30 held-out days; the top pick finished at -$3.15 (-0.16%) after paying $4.81 in fees, versus $77.19 for simply buying and holding. Only 1.1% of all 17,640 settings tried were profitable on the held-out days. Before fees, 18% of settings were in profit — fees and slippage are what turned them into losers. At Coinbase's entry-level taker rate of 0.60% per side, each round trip costs about 1.3% of the trade before the price has to move at all, which is larger than the small bounces this strategy tries to capture.

### What would the fee have to be to break even?

The last column in the tables below is the **per-side fee rate at which each setting would have broken exactly even** on the held-out days, keeping slippage at 0.05% per side. For comparison, the rate used here is **0.60%**.

- Top pick from training: breaks even at **0.208%** per side (the 0.60% used here is 2.9× that).
- Best of all 17,640 settings, picked with hindsight on the held-out days: breaks even at **0.019%** per side.
- For reference, the same third-party fee guides put Coinbase's lowest taker fee at about 0.05%, and only for accounts trading hundreds of millions of dollars a month.

## How the test worked

- **Data:** Coinbase public market data, 1-minute candles for BTC-USD, ETH-USD, 2026-07-18 to 2026-10-15 (90 days). 5-minute candles were built from the same data.
- **Training (days 1–60):** 2026-07-18 to 2026-09-15. All 17,640 settings were run here and ranked by profit.
- **Held-out test (days 61–90):** 2026-09-16 to 2026-10-15. These days were never used to choose settings; they show how the chosen settings would have done on new data.
- **Money:** $1,000 paper balance per pair ($2,000 total), $100 per trade, at most 1 open trade per pair.
- **Entry:** when a candle closes X% below the highest price of the last N minutes, buy at the next candle's opening price.
- **Exit:** take-profit at +Y%, stop-loss at −Z%, or sell at market after T minutes, whichever comes first. If a candle touches both the stop and the target, we assume the stop was hit (worst case).
- **Settings tried:** X = [0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]%, Y = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]%, Z = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]%, N = [15, 30, 60, 120, 240] min, T = [30, 60, 120, 240, 480, 1440] min, on both 1- and 5-minute candles.

## Fees and slippage used

- **Trading fee: 0.60% on every buy and every sell** — the *taker* rate for Coinbase Advanced Trade's lowest volume tier ($0–$10K traded in the last 30 days). Taker on both sides is the worst case (market orders); the same tier's maker rate is 0.40%.
- Source: Coinbase Advanced Trade's fee schedule as summarised by 2026 third-party guides (financer.com Coinbase review; coincodecap.com Coinbase fees guide), which list 0.40% maker / 0.60% taker for the under-$10K tier. Coinbase's own fee page (coinbase.com/advanced-fees) could not be reached when this tool was built, so **check the live schedule and update `config.yaml` if it differs.**
- **Slippage: 0.05% per side** — buys fill 0.05% above the candle price, sells 0.05% below.
- So every round trip costs about **1.30%** of the trade amount before any price move.

## Top 5 settings (picked on days 1–60) — results on the held-out days 61–90

This is the honest test: settings were chosen without seeing these days. Only settings that made at least 10 trades during training were eligible.

| # | Trades | Win rate | Net P&L | Net P&L % | Fees paid | Max drawdown | Break-even fee/side |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4 | 25% | -$3.15 | -0.16% | $4.81 | 0.9% | 0.208% |
| 2 | 4 | 25% | -$1.86 | -0.09% | $4.82 | 0.8% | 0.369% |
| 3 | 8 | 12% | -$13.59 | -0.68% | $9.58 | 1.3% | never (loses before fees) |
| 4 | 4 | 25% | -$4.78 | -0.24% | $4.80 | 0.5% | 0.003% |
| 5 | 5 | 40% | -$3.15 | -0.16% | $6.02 | 0.8% | 0.285% |

1. 1-minute candles · buy after a **2%** drop from the 15-minute high · take profit **+4%** · stop loss **-3%** · max hold **1440 min**  
   Training (days 1–60) result was -$4.54 over 12 trades.  
   Held-out by pair — BTC-USD: 0 trades, 0% wins, $0.00 (+0.00%), fees $0.00, max drawdown 0.0%; ETH-USD: 4 trades, 25% wins, -$3.15 (-0.31%), fees $4.81, max drawdown 0.9%

2. 1-minute candles · buy after a **2%** drop from the 15-minute high · take profit **+4%** · stop loss **-5%** · max hold **1440 min**  
   Training (days 1–60) result was -$4.62 over 12 trades.  
   Held-out by pair — BTC-USD: 0 trades, 0% wins, $0.00 (+0.00%), fees $0.00, max drawdown 0.0%; ETH-USD: 4 trades, 25% wins, -$1.86 (-0.19%), fees $4.82, max drawdown 0.8%

3. 5-minute candles · buy after a **1.5%** drop from the 15-minute high · take profit **+4%** · stop loss **-5%** · max hold **1440 min**  
   Training (days 1–60) result was -$6.59 over 16 trades.  
   Held-out by pair — BTC-USD: 3 trades, 0% wins, -$5.29 (-0.53%), fees $3.59, max drawdown 0.5%; ETH-USD: 5 trades, 20% wins, -$8.30 (-0.83%), fees $5.99, max drawdown 1.3%

4. 1-minute candles · buy after a **3%** drop from the 60-minute high · take profit **+1.5%** · stop loss **-1%** · max hold **60 min**  
   Training (days 1–60) result was -$6.86 over 10 trades.  
   Held-out by pair — BTC-USD: 0 trades, 0% wins, $0.00 (+0.00%), fees $0.00, max drawdown 0.0%; ETH-USD: 4 trades, 25% wins, -$4.78 (-0.48%), fees $4.80, max drawdown 0.5%

5. 1-minute candles · buy after a **3%** drop from the 120-minute high · take profit **+4%** · stop loss **-3%** · max hold **1440 min**  
   Training (days 1–60) result was -$6.97 over 11 trades.  
   Held-out by pair — BTC-USD: 0 trades, 0% wins, $0.00 (+0.00%), fees $0.00, max drawdown 0.0%; ETH-USD: 5 trades, 40% wins, -$3.15 (-0.32%), fees $6.02, max drawdown 0.8%

## Side by side with buy-and-hold (held-out days 61–90)

| Approach | Net P&L | Net P&L % | Fees paid | Max drawdown |
|---|---:|---:|---:|---:|
| Top pick above (both pairs) | -$3.15 | -0.16% | $4.81 | 0.9% |
| Buy & hold BTC-USD ($1,000) | $72.59 | +7.26% | $12.44 | 8.6% |
| Buy & hold ETH-USD ($1,000) | $4.60 | +0.46% | $12.03 | 17.3% |
| Buy & hold both | $77.19 | +3.86% | $24.47 | — |

Note: the strategy only ever has $100 of each $1,000 invested, while buy-and-hold has all of it in the market, so buy-and-hold's gains *and* losses are naturally much larger.

## For reference: top 5 with hindsight (picked directly on days 61–90)

These are the best settings *after the fact*. Picking settings this way is overfitting: it flatters the strategy, because nobody could have known these settings in advance.

| # | Trades | Win rate | Net P&L | Net P&L % | Fees paid | Max drawdown | Break-even fee/side |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 13 | 38% | -$4.63 | -0.23% | $15.67 | 1.4% | 0.423% |
| 2 | 13 | 38% | -$7.07 | -0.35% | $15.65 | 1.8% | 0.329% |
| 3 | 13 | 38% | -$7.26 | -0.36% | $15.65 | 1.3% | 0.321% |
| 4 | 13 | 38% | -$7.59 | -0.38% | $15.65 | 1.4% | 0.309% |
| 5 | 13 | 38% | -$8.60 | -0.43% | $15.64 | 1.4% | 0.270% |

1. 1-minute candles · buy after a **2%** drop from the 60-minute high · take profit **+4%** · stop loss **-5%** · max hold **1440 min** (days 1–60: -$15.67)
2. 1-minute candles · buy after a **2%** drop from the 60-minute high · take profit **+4%** · stop loss **-3%** · max hold **1440 min** (days 1–60: -$15.90)
3. 5-minute candles · buy after a **1.5%** drop from the 30-minute high · take profit **+4%** · stop loss **-3%** · max hold **1440 min** (days 1–60: -$21.31)
4. 5-minute candles · buy after a **1.5%** drop from the 30-minute high · take profit **+4%** · stop loss **-5%** · max hold **1440 min** (days 1–60: -$20.54)
5. 1-minute candles · buy after a **2%** drop from the 60-minute high · take profit **+3%** · stop loss **-5%** · max hold **1440 min** (days 1–60: -$20.29)

## Overfitting check

- Share of all settings that were profitable on training days: **0.0%**; on the held-out days: **1.1%**.
- Share profitable on held-out days if fees were zero (slippage kept): **18.5%**.
- The top training pick went from -$4.54 (training) to -$3.15 (held-out).

## Default settings from config.yaml

1-minute candles · buy after a **1%** drop from the 60-minute high · take profit **+1.5%** · stop loss **-2%** · max hold **240 min**

| # | Trades | Win rate | Net P&L | Net P&L % | Fees paid | Max drawdown | Break-even fee/side |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 85 | 15% | -$107.48 | -5.37% | $101.97 | 7.4% | never (loses before fees) |

## Limits of this test

- 1-minute candles don't show the order of prices inside the minute; we assume the worse outcome when a stop and target are both touched.
- Real fills during sharp drops can be worse than the 0.05% slippage assumed.
- 90 days is one market regime. A strategy can look fine in one period and fail in the next.
- Full per-setting results are in `results/sweep.csv`.
