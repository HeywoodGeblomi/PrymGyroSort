# NON_CLAIMS — PrymGyroSort v0.1.2-path2

## Mandatory honesty framing

1. **Path-local only.**  
   All geometric data and ranking operate on engineered path-local dual-Rauzy / period-vector streams (or synthetic certificate-anchored analogues).  
   Results do **not** constitute global statements about the Lyapunov spectrum of $\Omega E_{12}(4)$ or $H(4)^{\mathrm{odd}}$.

2. **No ownership of theorems.**  
   - Sum of positive Lyapunov exponents $= 8/5$ is due to Chen–Möller.  
   - Individual non-tautological exponents $\lambda_2 = 2/5$, $\lambda_3 = 1/5$ are due to Möller and Eskin–Kontsevich–Zorich (recorded in Eskin–Matheus).  
   This prototype does not claim, re-prove, or computationally establish those results.

3. **Not a classical 1-D sorter.**  
   PrymGyroSort is a multi-objective weak-dominance ranking filter (GyroRank kernel).  
   It isolates Pareto-optimal geometric seeds; it is not a drop-in replacement for `std::sort`, pdqsort, or PhotonicSort.

4. **EXTERNAL-clean / no-$\chi$.**  
   No internal irreversible state, no hidden commitment bit, no $\chi$-style non-reducible memory.  
   All decisions are driven by visible objectives only.

5. **`promote_ready = false` for global spectral claims.**  
   Higher $N$ only increases local trajectory resolution of the engineered ensemble. It does not unlock global Lyapunov certificates.

## Live-Path Wire (Path 2)

* **Default mode (`certified`):** ensemble anchored on the vendored seed-728 Diagram B path-local monodromy certificate (`pos_sum $\in$ [1.599945, 1.611119]`, contains $8/5$ under the stated QR model). Self-contained via `data/certified_snapshot/`.
* **`live` mode:** optional import of `prym-eigenform-pipeline-d12` pure dual-Rauzy recording (`scripts.lambda23_pure_path`). Falls back to certified if the package is not available.
* **`synthetic` mode:** legacy certificate-anchored generator (CI / offline fallback).
* **Still path-local only.** Live streams do **not** promote global Lyapunov claims.
* **`promote_ready` remains false** for any global spectral statement until isolation metrics are deliberately re-measured on live trajectories under the same self-check gates.

See `docs/PATH2_LIVE_WIRE.md` for the stream contract and usage.

## Scale & Memory Boundaries (v0.1.1+)

* **Gating Threshold:** At $N \ge 65536$ or when `memory_pressure` is manually invoked, the `GyroController` flags a strategy deflection from `FenwickMax` to `LowAux2D`.
* **Auxiliary Space Integrity:** LowAux2D preserves $O(N \log N)$ time with rigid low-overhead bounds. Sub-linear auxiliary ranking ($o(N)$) is **not claimed**.
* **Measured footprint (this class):** N=4096 ≈ 1.5–2 ms (Fenwick); N=65536 + memory_pressure ≈ 40 ms (LowAux). Certificate-anchored anchors remain isolated (recall 1.0; mean rank good ≪ rest).
* **Spectral Disconnect:** Higher $N$ scales local resolution only; `promote_ready` stays **false** for global spectral claims.

## What you may cite

- The integration pattern: geometric multi-objective points from a residual-0 Prym scaffold ranked by an adaptive GyroController / FenwickMax kernel.
- Self-check behaviour on certified / synthetic low-residual vs high-residual clouds.
- Container reproducibility of the ranking pipeline.
- Scale deflection behavior at N≥65536 under memory_pressure.
- Path-2 live-wire adapter as a stream interface to path-local dual-Rauzy artefacts (not as a global spectrum engine).

## What you must not cite this as

- A certified computation of global $\lambda_2, \lambda_3$.
- A proof or independent derivation of the sum $8/5$.
- A general-purpose high-performance sequential sorter for arbitrary arrays.
- A sub-linear auxiliary-space ranking algorithm.
