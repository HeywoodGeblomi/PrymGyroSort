# Cache / Multi-Process Contention

N=6400, workers=4, static q=0.25 + native M=2 rank.

| mode | wall ms |
|:---|---:|
| sequential | 522.6 |
| parallel 4-way | **78.1** |
| ideal linear | 130.7 |
| efficiency (ideal/parallel) | **1.67** |

Per-worker median rank pipeline ≈ **1.1–1.2 ms** under concurrency.

**Read:** No evidence of destructive cross-process thrashing on this host — parallel wall is well under sequential. Efficiency > 1 reflects sequential overhead not dividing cleanly (imports/warmup), not superlinear magic.

Host-specific. `promote_ready=false`.

```bash
python3 python/bench_cache_contention.py --n 6400 --workers 4 --reps 6
```
