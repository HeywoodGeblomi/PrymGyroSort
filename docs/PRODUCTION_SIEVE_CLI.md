# Production Sieve CLI

Unified M=2 entry: optional static OR-quantile → native zero-copy rank.

```bash
# synthetic
python3 python/prym_sieve_cli.py --n 4096 --seed 42

# matrix.bin (float64 row-major N×2)
python3 python/prym_sieve_cli.py --matrix work/matrix.bin --n 4096 --out work

# full rank (no prefilter)
python3 python/prym_sieve_cli.py --n 2048 --no-prefilter

# multi-worker synthetic
python3 python/prym_sieve_cli.py --n 2048 --workers 4
```

Smoke: n=4096 q=0.25 → n'≈1755, ~2.4 ms on this host.

**Not alpha. Not order routing. `promote_ready=false`.**
