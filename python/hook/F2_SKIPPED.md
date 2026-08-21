# GYR-HOOK-001 F2 — skipped (honest)

**Status:** F2 (Photonic probe emit) is **not implemented**.

## Why

Photonic residual paths (`pure_residual_menu`, `hybrid_residual_menu`) are **sequential try-until-success** gates, not a scored menu of independent talents.

Probe-visible numbers at dispatch time are **array-level** only, e.g.:

- `classical_score`, `|sigma_delta|`, `residual_talent` (hybrid)
- structure samples: inv, eq, u, desc_runs

There is **no** already-visible pair `(score0, score1)` **per residual talent** that can fill `options.csv` with `N_opt ≥ 2` without inventing scores.

Inventing scores would violate GYR-HOOK-001 §1 / F2 exit (“two already-visible metrics”).

## Contract consequence

Initiative §4: *If F2 cannot emit two honest metrics without inventing scores, ship F1 only and record F2 skipped. That is still a successful ticket: the scheduler API exists.*

## What remains live

| Piece | Status |
|-------|--------|
| F1 `python/hook/run.py` | Live — options.csv → chosen.json, fenwick_oracle |
| F2 Photonic `--emit-options` | **Skipped** |
| F3 live path | Held until GO; needs either honest emit or an external menu |

GyroRank v0.2 untouched. Photonic default path unchanged (no flag added).
