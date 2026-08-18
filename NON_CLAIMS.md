# NON_CLAIMS — PrymGyroSort v0.1.1-prototype

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

5. **Synthetic generator.**  
   The self-check generator produces certificate-anchored synthetic points inspired by the published seed-728 path-local interval.  
   Wiring of the live pure-path dual-Rauzy evaluator from `prym-eigenform-pipeline-d12` is a deliberate next step, not claimed complete here.

6. **Promotion scope.**  
   Containerized + self-check GREEN means the integration prototype is reproducible and the ranking semantics are verified on the engineered class.  
   It does **not** mean a foundational advance in Teichmüller dynamics or a field-level sorting result.

## Scale & Memory Boundaries (v0.1.1-prototype)

* **Gating Threshold:** At $N \ge 65536$ or when `memory_pressure` is manually invoked, the `GyroController` explicitly flags a strategy deflection from the high-throughput `FenwickMax` path to the `LowAux2D` kernel.
* **Auxiliary Space Integrity:** The `LowAux2D` fallback preserves the $O(N \log N)$ time complexity but enforces rigid, low-overhead array bounds. Sub-linear auxiliary space ranking ($o(N)$) is explicitly **not claimed** and remains future work.
* **Measured footprint (this class):** N=4096 ≈ 1.5–2 ms (Fenwick); N=65536 + memory_pressure ≈ 40 ms (LowAux path). Certificate-anchored anchors remain isolated (recall 1.0; mean rank good ≪ rest).
* **Spectral Disconnect:** Running at higher $N$ scales the local resolution of the trajectory path, but `promote_ready` remains strictly **false** for any global spectral or Lyapunov exponent claims.

## What you may cite

- The integration pattern: geometric multi-objective points from a residual-0 Prym scaffold ranked by an adaptive GyroController / FenwickMax kernel.
- Self-check behaviour on synthetic low-residual vs high-residual clouds.
- Container reproducibility of the ranking pipeline.
- Scale deflection behavior at N≥65536 under memory_pressure.

## What you must not cite this as

- A certified computation of global $\lambda_2, \lambda_3$.
- A proof or independent derivation of the sum $8/5$.
- A general-purpose high-performance sequential sorter for arbitrary arrays.
- A sub-linear auxiliary-space ranking algorithm.
