# Release Notes — PrymGyroSort v0.1.4-sieve

**Tag (create in UI):** `v0.1.4-sieve`  
**Commit basis:** `main` @ `f3cdf7ec`+ (CLI ensemble fix)  
**Date:** 2026-08-18

## Highlights

- **Production sieve CLI** — `python/prym_sieve_cli.py` (static OR-quantile + native M=2, optional multi-worker)
- **Zero-copy pybind11 binding** — C-contiguous `(N,2)` only; hard reject non-contig / wrong shape / dtype
- **Multi-stage Docker** — non-root `quantoperator`, portable ISA default (no `-march=native` / no OpenMP myths)
- **Coarse quantile prefilter** — measured ~2.5× pipeline speedup; R@1/R@top = 1.0 on suite; anchor filter killed
- **Binding iron** — 11/11 single-process; 400/400 illegal catches under 4-worker parallel stress
- **Durability horizon** — 500-tick production-path tracker (local S@top≈0.60; origin front high turnover)
- **Kinetic A/B** — velocity transform **does not ship** (27/27 no durability gain)
- **M=3 lab only** — exact 3-D ranks in Python; **no** `rank_m3` native; static 3-axis quantile preferred over DQVA

## Verified container smoke (host Docker)

```text
[sieve] path=quantile_q=0.25  n'=1755  ms≈1.0  min_rank=1
work/ranks.npy + work/report.json written via volume mount
```

```bash
docker build -t prym-gyro-sieve:latest .
docker run --rm prym-gyro-sieve:latest --n 4096 --seed 42
```

## Honesty

`promote_ready = false`  
Execution sieve only — not alpha, not order routing, not global spectral claims.  
See [NON_CLAIMS.md](NON_CLAIMS.md).

## Core

`cpp/include/gyro_rank.hpp` remains the frozen M=2 weak-dominance kernel.

## Prior

- **v0.1.3-finance** — finance adapter + Path-2 wire + viz + scaling campaign  
- **v0.1.1-prototype** — memory-hardened LowAux2D gating
