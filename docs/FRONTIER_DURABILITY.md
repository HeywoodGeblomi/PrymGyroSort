# Frontier Durability (symbol-stable)

Fixed symbol IDs; features drift each tick. Jaccard + survival of rank-1 / top-frac.

| path | symbols | J@rank1 | J@top | S@rank1 | S@top | median ms |
|:---|---:|---:|---:|---:|---:|---:|
| full | 100 | 0.571 | 0.429 | 0.750 | 0.600 | 0.04 |
| quantile | 100 | 0.571 | 0.429 | 0.750 | 0.600 | 0.04 |

## Read

- **J@rank1 ≈ 0.57 / S@rank1 ≈ 0.75** under mild synthetic drift: front is partially durable, not frozen.
- **Quantile path matches full** on durability → sieve does not scramble membership vs full rank on this stream.
- Near-0 Jaccard would mean total reshuffle every tick.

## Non-claims

Synthetic observational metric only. Not alpha. `promote_ready=false`.

```bash
python3 python/frontier_durability.py --symbols 100 --ticks 50
```
