# Multi-Asset Scaling Profiler

Zero-copy rank latency vs concurrent synthetic symbols (64 rows/symbol).

| Symbols | N rows | median µs | p95 µs | min µs |
|---:|---:|---:|---:|---:|
| 1 | 64 | 5.2 | 16.2 | 4.8 |
| 2 | 128 | 9.5 | 12.8 | 9.3 |
| 4 | 256 | 19.7 | 37.7 | 19.3 |
| 8 | 512 | 81.9 | 116.8 | 73.7 |
| 16 | 1024 | 258.1 | 294.0 | 239.2 |
| 32 | 2048 | 634.1 | 670.5 | 602.0 |
| 64 | 4096 | 1425.4 | 1469.4 | 1380.9 |
| 100 | 6400 | 2340.7 | 2386.5 | 2307.0 |

At 100 symbols / 6400 rows: **~2.3 ms median** rank (zero-copy).

Honesty: latency measurement only. Not alpha. `promote_ready=false`.

```bash
python3 python/bench_multi_asset.py --reps 20
```
