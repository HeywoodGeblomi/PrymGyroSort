# Release Notes — PrymGyroSort v0.1.3-finance

**Tag:** `v0.1.3-finance`  
**Date:** 2026-08-18

## Highlights

- **Finance protocol adapter** — pair-filter execution sieve (`protocol_finance.py`)
- **Path-2 live wire** — certified / live / synthetic geometric streams
- **Path-A visualization** — zero-dependency ASCII + inline-SVG Pareto sidecar
- **Scaling campaign** — LowAux2D measured through N=2^20 (recall 1.0 held)
- **Container** — multi-stage Docker image, compose profiles (`finance`, `viz`)

## Performance snapshot

| Mode | N | Time | Notes |
|------|---:|------|-------|
| Finance synthetic | 4096 | ~2.9 ms | recall 1.0, gap +58 |
| Geometric LowAux2D | 65536 | ~38 ms | recall 1.0 |
| Geometric LowAux2D | 1e6 | ~1.2 s | recall 1.0, gap +899 |

## Honesty

`promote_ready = false` for global spectral claims and live-trading profitability.  
See [NON_CLAIMS.md](NON_CLAIMS.md).

## Container

```bash
docker build -t prym-gyro-sort:0.1.3 .
docker run --rm -e MODE=finance -e N=4096 -v "$PWD/work:/work" prym-gyro-sort:0.1.3
```

## Upgrade from v0.1.1

- New: `python/protocol_finance.py`, `python/viz_pareto.py`, `python/scaling_campaign.py`, `python/live_path_wire.py`
- New docs under `docs/`
- Dockerfile / entrypoint aligned to `rank_driver <matrix> <N> <M> <out_dir> [pressure]`
- Core `gyro_rank.hpp` unchanged
