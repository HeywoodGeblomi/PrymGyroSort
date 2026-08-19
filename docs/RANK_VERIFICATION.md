# Ranking verification (v0.1.5-sieve+)

## Claim under test

`exact_rank_2d_fenwick` implements **2-D weak-dominance layer ranks**
(NSGA-II-style successive nondominated fronts), lower-better on both objectives.

Not the same as domination-count ranks (`1 + |dominators|`).

## Independent oracle

Pure-Python O(N²) successive nondominated sorting (`python/verify_rank_rigor.py`).
No pymoo dependency required.

## Formal background

- 2-objective maxima / nondominated sorting: **O(N log N)** (Kung, Luccio, Preparata 1975).
- Fenwick/BIT sweeps are a standard engineering realization of that class.

## Properties checked

| ID | Property |
|----|----------|
| P1 | ranks ≥ 1 |
| P2 | every rank-1 point is nondominated |
| P3 | every nondominated point has rank 1 |
| P4 | if j weakly dominates i then rank(j) < rank(i) |
| P5 | deterministic |

## Results (post-fix)

**11/11** cases: native ≡ layer-rank oracle; all properties PASS.

Cases: hand chain, random n=20..200, all-identical, antichain Pareto front,
total chain, finance stress profile n=150, duplicate-x, front+dominated cloud.

Domination-count ranks match only on chains/identical (expected).

## Bugs found and fixed

1. **Gate misfire:** `sortedness_0 > 0.97 && n < 4096` selected `Insertion1D` for M=2
   (broke antichains / monotone obj0). **Fix:** `Insertion1D` only when `m ≤ 1`.
2. **Equal-x batching:** same-x points never saw each other → weak dominance on y
   missed. **Fix:** sequential update in (x,y) order with exclusive y prefix query.

## Non-claims

- Not a proof of equivalence to every multi-objective library's ranking variant.
- pymoo not run in CI here (optional external cross-check).
- `promote_ready=false` — mechanical ranking verification only.

```bash
python3 python/verify_rank_rigor.py
```
