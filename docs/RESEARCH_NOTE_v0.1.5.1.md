# Research Note — PrymGyroSort v0.1.5.1-sieve+finance

**Tag:** `v0.1.5.1-research`  
**Core sieve tag:** `v0.1.5.1-sieve`  
**Status:** `promote_ready=false` — structural / research only. Not a trading system.

## Scope

This note freezes the **finance research sidecar layer** built on the verified M=2 layer-rank sieve:

- Portfolio adapter (`protocol_portfolio.py`)
- Circuit breaker + immutable tier export
- Research HRP consumers (equal / inv_vol / hrp / hrp_vol)
- Durability, dropout catch, corr-spike, structural spread, centroid replay

The C++ kernel (`gyro_rank.hpp`) remains frozen. Sidecars do not claim alpha, order routing, or live allocation.

## Ranking verification (kernel)

- Independent O(N²) layer-rank oracle: **11/11 PASS**
- Fixes in `v0.1.5.1-sieve`: Insertion1D only for M≤1; equal-x Fenwick sequential update
- See `docs/RANK_VERIFICATION.md`

## Finance pipeline (measured)

| Step | Result |
|------|--------|
| Portfolio n=500 → sieve | n′≈214, ~0.23–0.30 ms, min_rank=1 |
| Circuit breaker | OK on nominal; trips if n′<50 or n′>0.9n |
| Tier-1 size | ≈7–8 anchors |
| Tier-2 dropout catch (drift=0.05) | catch@r2=0.90, catch@2..3=1.00, lost=0 |
| Corr mean-collapse | **Does not** trip size-based breaker |
| Structural spread | 0.170 → 0.028 as ρ→1 (primary homogenization signal) |
| Rolling tier-1 (20 win, drift=0.05) | J@tier1 mean≈0.89, origin_surv≈0.86 |
| Centroid replay (60 win) | J≈0.89, origin_surv≈0.73, smooth centroid drift |
| HRP modes (synthetic returns) | hrp lowest port_vol; equal highest eff_n |

## Non-claims

- Not investment advice or a live allocator
- Synthetic features/returns unless otherwise stated
- Relative quantile + size breaker intentionally ignore uniform macro shifts
- Eigenvalue entropy on M=2 Gram is a weak absolute signal; use **spread**
- `promote_ready=false`

## Key scripts

```text
python/protocol_portfolio.py
python/tier_export.py
python/hrp_research.py
python/hrp_risk_scaled.py
python/hrp_tail_stress.py
python/verify_hrp_export.py
python/tier1_roll_stability.py
python/tier2_dropout_catch.py
python/corr_spike_breaker.py
python/structural_entropy.py
python/tier_centroid_replay.py
docs/FINTECH_MAP.md
docs/RANK_VERIFICATION.md
```

## Reproduce (container)

```bash
docker build -t prym-gyro-sieve:latest .
docker run --rm -e PYTHONUNBUFFERED=1 --entrypoint python3 \
  -v "$PWD/work:/app/work" prym-gyro-sieve:latest \
  /app/python/protocol_portfolio.py --n 500 --seed 7 --out-dir /app/work
docker run --rm -v "$PWD/work:/app/work" prym-gyro-sieve:latest \
  --matrix /app/work/matrix.bin --n 500 --out /app/work --json
docker run --rm -e PYTHONUNBUFFERED=1 --entrypoint python3 \
  -v "$PWD/work:/app/work" prym-gyro-sieve:latest \
  /app/python/tier_export.py --report /app/work/report.json \
  --ranks /app/work/ranks.npy --out-dir /app/work
```
