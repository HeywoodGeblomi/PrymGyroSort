# Phases 2–4 (honesty-hardened)

Rank path is **sequential** (no `#pragma omp` in Fenwick/LowAux).

```bash
make native           # -march=native
make native-omp       # optional fopenmp link; does not parallelize rank loops
make binding-native
python3 python/stream_loop.py --window 4096 --interval-ms 100 --duration 2
```

`promote_ready=false`. Not alpha. Not a trading bot.
