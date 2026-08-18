# Sieve Durability Horizon (production path)

500 ticks, 100 symbols, σ=0.15. Pipeline = `prym_sieve_cli` (static q + native M=2).

| path | J@top | S@top (consec.) | origin S@50 | origin S@100 | origin S@final | ms |
|:---|---:|---:|---:|---:|---:|---:|
| full | 0.429 | 0.600 | 0.20 | 0.00 | 0.20 | ~0.03 |
| quantile_q=0.25 | 0.429 | 0.600 | 0.20 | 0.00 | 0.20 | ~0.03 |

## Read

- **Local durability** (consecutive ticks): median S@top ≈ **0.60**, J@top ≈ **0.43** — partial stability tick-to-tick.
- **Origin half-life**: under this drift, the tick-0 top-frac set is largely gone by ~50–100 ticks (S@100 ≈ 0). High turnover — not a frozen elite club.
- Quantile path **matches full** on all horizon metrics.

## Non-claims

Synthetic observational only. Not alpha. `promote_ready=false`.

```bash
python3 python/sieve_durability.py --symbols 100 --ticks 500 --sigma 0.15
```
