# Release Notes — PrymGyroSort v0.1.5-sieve

**Tag:** [`v0.1.5-sieve`](https://github.com/HeywoodGeblomi/PrymGyroSort/releases/tag/v0.1.5-sieve)  
**Branch tip:** `main`  
**Date:** 2026-08-19

## Highlights

### Production hardening
- Structured **exit codes**: 0 ok · 1 usage · 2 data · 3 runtime · 4 self-check fail
- Matrix guards: shape `(N,2)`, NaN/Inf reject, empty reject, file size match
- `--self-check` — ensemble / quantile / full / reject-NaN
- `--json` — machine-readable stdout
- Docker: multi-stage, non-root `quantoperator`, portable ISA, **HEALTHCHECK**

### Finance expansion
Profiles on `protocol_finance.py` (structural sieve — **not alpha**):

| Profile | Emphasis |
|---------|----------|
| `pairs` | dislocation × OBI vs liquidity/MDD |
| `liquidity` | depth / spread resilience |
| `stress` | drawdown / gap risk |
| `micro` | OBI×dislocation pressure vs friction |

### Carried forward from v0.1.4
- Production sieve CLI (quantile + native M=2)
- Zero-copy pybind11 binding (C-contiguous only)
- Binding iron (400/400 illegal catches under parallel stress)
- Durability horizon tracker

## Verified container smoke

```text
[sieve] self-check PASS version=0.1.5-sieve
[finance] 0.1.5 profile=stress n=4096 promote_ready=false
{"ok": true, "path": "quantile_q=0.25", "min_rank": 1, ...}
```

```bash
docker build -t prym-gyro-sieve:latest .
docker run --rm prym-gyro-sieve:latest --self-check
docker run --rm prym-gyro-sieve:latest --n 4096 --seed 42 --json
```

## Honesty

`promote_ready = false`  
Execution sieve only — not alpha, not order routing, not global spectral claims.  
See [NON_CLAIMS.md](NON_CLAIMS.md).

## Core

`cpp/include/gyro_rank.hpp` remains the frozen M=2 weak-dominance kernel.

## Prior tags

- **v0.1.4-sieve** — production CLI + Docker iron
- **v0.1.3-finance** — first finance adapter
- **v0.1.1-prototype** — LowAux2D memory gating
