# Sub-Linear Performance Scaling Harness Specification

**Status:** measurement campaign only  
**Claim surface:** asymptotic sub-linear auxiliary allocation $o(N)$ is explicitly **NOT claimed**  
**Core API impact:** none — offline runner + documentation only

This harness tracks the resilience of the `GyroController` and its `LowAux2D`
fallback under escalating volume ladders. Results inform whether a true $o(N)$
structure is warranted or whether LowAux2D is the honest ceiling for this class.

## Evaluation Ladder

| Scale point | $N$ |
|-------------|-------|
| $2^{16}$ | 65,536 |
| $2^{18}$ | 262,144 |
| $2^{20}$ | 1,048,576 |

**Constraints**

* All primary ladder points execute with forced `memory_pressure=1` (isolates LowAux2D).
* Optional control column at $N=2^{16}$ with `memory_pressure=0` (Fenwick path) for comparison only when host RAM allows.
* Data source: certified / synthetic monodromy ensemble (`live_path_wire` or `generate_geometric_matrix`), seed-728 style anchors.

## Metrics

| Symbol | Name | Definition |
|--------|------|------------|
| $T_{\mathrm{wall}}$ | Wall time | Rank execution duration (ms) from `rank_report.json` |
| $B_{\mathrm{aux}}$ | Aux footprint | Estimated internal allocation (bytes); LowAux path ≈ $O(N)$ working set (documented estimate, not a profiler claim) |
| $R_{\mathrm{top}}$ | Top-fraction recall | Fraction of good anchors in the lowest `top_frac` ranks (`self_check.py`) |
| $\Delta_{\mathrm{mean}}$ | Separation gap | $\mu_{\mathrm{rest}} - \mu_{\mathrm{good}}$ (mean rank rest minus mean rank good) |

## Failure modes under observation

1. **Algorithmic:** Does $\Delta_{\mathrm{mean}}$ collapse at $N=2^{20}$? (resolution loss under density)
2. **Systems:** Does $T_{\mathrm{wall}}$ spike super-linearly? (cache / branch pressure)

## Runner

```bash
# Build rank_driver once (host)
g++ -O3 -std=c++17 -Icpp/include cpp/rank_driver.cpp -o work/rank_driver

# Full ladder (may be heavy at 2^20)
python3 python/scaling_campaign.py --ladder 65536,262144,1048576 --memory-pressure 1

# Smoke subset
python3 python/scaling_campaign.py --ladder 65536 --memory-pressure 1
```

Outputs:

* Console markdown table
* `docs/SCALING_RESULTS.md` (timestamped run)
* Per-N work dirs under `work/scale_N<n>/` (matrix, ranks, reports)

## Honesty

* Measurement campaign only.
* No asymptotic $o(N)$ claim is asserted from these numbers.
* Path-local engineered ensemble only; no global Lyapunov language.
* See root `NON_CLAIMS.md`.
