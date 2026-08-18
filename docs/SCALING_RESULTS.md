# Scaling Campaign Results

**Timestamp:** 2026-08-18 15:06:19 UTC  
**Ladder:** 65536,262144,1048576  
**memory_pressure:** 1  
**seed:** 728  

## Table

| Scale (N) | Space Mode | Wall Time (ms) | Aux Bytes (est) | Top-frac Recall | Separation Gap |
|---:|---|---:|---:|---:|---:|
| 65536 | LowAux2D | 37.98 | 1114112 | 1.000 | +230.7 |
| 262144 | LowAux2D | 197.81 | 4259840 | 1.000 | +449.4 |
| 1048576 | LowAux2D | 1188.11 | 16842752 | 1.000 | +898.8 |

## Observations (measurement only)

* **Recall:** held at 1.000 across the full ladder — no algorithmic collapse of top-fraction isolation.
* **Separation gap:** *increased* with N (+230 → +449 → +899), consistent with more rank layers rather than loss of structure.
* **Wall time:** roughly linear-to-mildly-superlinear in N under LowAux2D (~38 ms → 198 ms → 1188 ms). No exponential spike observed in this class.
* **Aux estimate:** scales ~$O(N)$ as expected for LowAux2D; **not** an $o(N)$ claim.

## Notes

- Measurement campaign only. Asymptotic o(N) auxiliary ranking is **not claimed**.
- Aux bytes are engineering estimates for the LowAux2D working set, not heap-profiler ground truth.
- Path-local engineered ensemble; no global Lyapunov language.
- See `docs/SCALING_HARNESS.md` and root `NON_CLAIMS.md`.
