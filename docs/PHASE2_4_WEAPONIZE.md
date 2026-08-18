# Phases 2–4 — Native profile, richer objectives, streaming

**Core `gyro_rank.hpp`:** frozen.  
**Honesty:** execution sieve only — `promote_ready=false`.

## Phase 2 — Native / OpenMP

```bash
make                  # portable
make native           # -march=native -fopenmp
make binding-native   # PRYM_NATIVE=1 .so
```

Docker default stays portable.

## Phase 3 — Richer finance objectives (v0.1.4)

Opportunity (dislocation + OBI) vs risk (liquidity + MDD proxy).

## Phase 4 — Streaming scaffold

```bash
python3 python/stream_loop.py --window 4096 --interval-ms 100 --duration 2
```

Inject live rows via `RankStream.push_row(...)`. No exchange credentials shipped.

## Non-claims

Not a trading bot. Not alpha. See `NON_CLAIMS.md`.
