# Stress-500: Prealloc vs Churn vs Rank-Only

| Symbols | N | churn µs | prealloc µs | rank-only µs | churn−pre µs | rank/pre % |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 64 | 148.5 | 31.5 | 5.4 | 117.0 | 17.2% |
| 4 | 256 | 67.8 | 68.8 | 20.0 | -1.0 | 29.0% |
| 16 | 1024 | 380.5 | 333.3 | 281.7 | 47.2 | 84.5% |
| 64 | 4096 | 1562.6 | 1634.4 | 1610.2 | -71.8 | 98.5% |
| 100 | 6400 | 2712.1 | 2574.4 | 2358.6 | 137.6 | 91.6% |
| 200 | 12800 | 5467.4 | 5335.0 | 5210.9 | 132.4 | 97.7% |
| 350 | 22400 | 12063.6 | 10331.7 | 9756.9 | 1731.9 | 94.4% |
| 500 | 32000 | 15734.1 | 15500.4 | 13918.8 | 233.7 | 89.8% |

## Interpretation

At scale (N ≥ ~1k), **rank-only is ~85–98% of prealloc time** → **GyroRank kernel dominates**.

Churn vs prealloc delta is small relative to total latency at 100–500 symbols.

**Shadow-Ring will not cut latency by orders of magnitude** on this path. Ingest isolation may still be useful for engineering cleanliness, but not as a claimed 2.3 ms → 300 µs breakthrough.

At 500 symbols / 32k rows: rank floor ≈ **14 ms** median.

Honesty: measurement only. `promote_ready=false`.

```bash
python3 python/bench_stress_500.py --reps 10
```
