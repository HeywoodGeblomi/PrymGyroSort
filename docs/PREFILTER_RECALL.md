# Coarse Pre-Filter: Latency vs Front Recall

Approximate sieve. Exact rank only on survivors. Full rank = ground truth.

| N | method | N' | keep% | pipeline ms | full ms | speedup | R@rank1 | R@top-frac |
|---:|:---|---:|---:|---:|---:|---:|---:|---:|
| 1024 | quantile | 422 | 41.2% | 0.16 | 0.47 | 2.11 | 1.00 | 1.00 |
| 1024 | anchor | 22 | 2.1% | 6.92 | 0.30 | 0.04 | 1.00 | 0.22 |
| 6400 | quantile | 2777 | 43.4% | 1.03 | 2.66 | 2.59 | 1.00 | 1.00 |
| 6400 | anchor | 85 | 1.3% | 44.23 | 2.54 | 0.06 | 1.00 | 0.23 |
| 12800 | quantile | 5591 | 43.7% | 2.17 | 5.22 | 2.38 | 1.00 | 1.00 |
| 12800 | anchor | 100 | 0.8% | 96.02 | 5.38 | 0.06 | 1.00 | 0.14 |
| 32000 | quantile | 13979 | 43.7% | 6.86 | 18.95 | 2.56 | 1.00 | 1.00 |
| 32000 | anchor | 246 | 0.8% | 219.72 | 14.83 | 0.07 | 1.00 | 0.15 |

## Verdict

| Filter | Decision |
|--------|----------|
| **quantile** (q=0.25 per axis, OR) | **SHIP** — ~2.1–2.6× speedup, R@rank1=1.0, R@top=1.0 |
| **anchor** | **KILL** — R@top collapses (0.14–0.23), slower than full rank |

## Non-claims

- Approximate sieve only — not exact weak-dominance ranks on full N.
- `promote_ready=false`

```bash
python3 python/prefilter_rank.py --method quantile --ladder 1024,6400,32000
```
