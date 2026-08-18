# Scale / memory notes — PrymGyroSort v0.1.1-prototype

## Large-N path (N ≥ 65536)

- Pure demo: `./prym_gyro_demo [N] [N_GOOD] [memory_pressure]`
  - Auto-enables `memory_pressure=true` when N ≥ 65536 (unless explicitly set to 0).
- GyroController gates **LowAux2D** when `memory_pressure == true` or `density_product > 2^26`.

## Measured (controlled engineered ensemble)

| N | memory_pressure | time_ms | recall (top 5% band) | mean_rank_good | mean_rank_rest |
|---|-----------------|---------|----------------------|----------------|----------------|
| 4096 | false | ~1.5 | 1.0 | ~5.6–5.8 | ~63–64 |
| 65536 | true | ~40 | 1.0 | ~8–9 | ~230+ |

## What is claimed / not claimed

- Claimed: correct strategy deflection under the documented gates; full isolation of certificate-anchored anchors on the low-rank front for this process class.
- **Not claimed:** sub-linear auxiliary space $o(N)$; global Lyapunov recovery; classical 1-D sort domination.

See NON_CLAIMS.md. `promote_ready` remains **false** for global spectral claims.
