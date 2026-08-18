# Protocol Adapter: Quantitative Pair Filtering (v0.1.4)

**Core impact:** none — pure Python sidecar.

## Objectives (richer mapping)

| Objective | Name | Definition |
|-----------|------|------------|
| **obj0** | opportunity_proxy | `0.6 · 1/(|spread−mean|+ε) + 0.4 · (1−OBI)/2` |
| **obj1** | risk_proxy | `0.6 · (bid_ask/depth) + 0.4 · mdd_proxy` |

## CSV schema

```
timestamp,asset_a_price,asset_b_price,historical_mean,bid_ask_spread,book_depth[,obi,mdd_proxy]
```

## Honesty

Execution sieve only. **No alpha.** `promote_ready = false`.

```bash
python3 python/protocol_finance.py --out-dir work --n 4096 --seed 42
```
