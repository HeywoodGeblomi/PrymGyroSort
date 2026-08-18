# Protocol Adapter: Quantitative Pair Filtering (v0.1.3)

Domain adapter that maps high-frequency / statistical-arbitrage style
pair features into the frozen PrymGyroSort `matrix.bin` contract.

**Core impact:** none — pure Python sidecar. C++ ranking kernel unchanged.

## Problem class

High-frequency statistical arbitrage pair filtering: rank candidate
pair dislocations by structural efficiency (size of dislocation vs
immediate execution risk).

## Objective mapping (M = 2, lower = better)

| Objective | Name | Definition |
|-----------|------|------------|
| **obj0** | pricing_residual_proxy | `1 / (|spread − rolling_mean| + ε)` — larger mean-reversion dislocation → **lower** obj0 (preferred) |
| **obj1** | liquidity_risk_proxy | `bid_ask_spread / (book_depth + ε)` — thicker book / tighter spread → **lower** obj1 (preferred) |

Weak-dominance ranking isolates candidates that are simultaneously
deeply dislocated **and** cheap to trade.

## Input schema (CSV)

```
timestamp,asset_a_price,asset_b_price,historical_mean,bid_ask_spread,book_depth
```

- `spread` is derived as `asset_a_price - asset_b_price`
- `historical_mean` is the rolling / reference mean of that spread
- Missing file → synthetic bootstrap ensemble (seeded, reproducible)

## Output contract (unchanged)

```
matrix.bin   # N × 2 float64 row-major
is_good.npy  # optional: high-dislocation + low-risk anchors
meta.json    # domain, version, N, M, promote_ready=false
```

## Honesty & operational boundaries

* **No alpha generation.** Does not predict direction or guarantee profitable trades.
* **Execution sieve only.** Ranks structural efficiency of candidate entries.
* **Slippage & latency.** Ranking latency is milliseconds-class; live execution risk is owned by the downstream broker / OMS.
* **`promote_ready = false`** for any claim of live trading profitability or risk-free arb.
* Path-local / engineered class when using synthetic bootstrap; live CSV is user-supplied market data, not a certified edge.

## Usage

```bash
# Synthetic bootstrap
python3 python/protocol_finance.py --out-dir work --n 4096 --seed 42

# Real CSV
python3 python/protocol_finance.py --input data/market_feed.csv --out-dir work

# Unchanged ranking + viz
./work/rank_driver work/matrix.bin <N> 2 work
python3 python/viz_pareto.py --dir work --format both
```

See root `NON_CLAIMS.md` for global project honesty surface.
