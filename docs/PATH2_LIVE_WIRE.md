# Path 2 — Live-Path Wire Execution

**Status:** implemented (v0.1.2-path2 candidate)  
**promote_ready:** false  
**Honesty:** path-local only; EXTERNAL-clean / no-χ

## Goal

Replace the purely synthetic geometric matrix generator with a stream
sourced from (or anchored on) the real path-local dual-Rauzy / period
evaluation surface of
[prym-eigenform-pipeline-d12](https://github.com/HeywoodGeblomi/prym-eigenform-pipeline-d12).

## Modes

| Mode | Description |
|------|-------------|
| `certified` (default) | Vendored seed-728 Diagram B path-local monodromy snapshot + controlled ensemble around the certified pos-sum interval `[1.599945, 1.611119]`. Self-contained. |
| `live` | Attempt import of `scripts.lambda23_pure_path.record_pure_path` from a prym-eigenform-pipeline-d12 checkout. Emits rows from real pure dual-Rauzy paths. Falls back to `certified` if import fails. |
| `synthetic` | Legacy certificate-anchored synthetic (identical to `generate_geometric_matrix.py`). CI fallback. |

## Objective mapping

- **obj0** = `|pos_sum_proxy − 8/5|`
- **obj1** = QR / geometric residual proxy (interval width, decision-gap inverse, length-ratio residual)

Lower is better. Weak-dominance ranking isolates low-residual path-local anchors.

## Contract (unchanged)

```
matrix.bin   # N × 2 float64 row-major
is_good.npy  # N bool
meta.json    # mode, seed, cert interval, promote_ready=false, scope
```

`rank_driver` and `self_check.py` consume this layout without change.

## Usage

```bash
# Default: certified ensemble (self-contained)
python3 python/live_path_wire.py --mode certified --n 4096 --out-dir work

# Live (requires prym-eigenform-pipeline-d12 on PYTHONPATH or sibling clone)
python3 python/live_path_wire.py --mode live --n 4096 --n-paths 24 --steps 400 --out-dir work

# Then rank as before
g++ -O3 -std=c++17 -Icpp/include cpp/rank_driver.cpp -o work/rank_driver
./work/rank_driver work/matrix.bin 4096 2 work
python3 python/self_check.py --dir work
```

## Non-claims (mandatory)

- Path-local engineered / certified streams only.
- Does **not** claim global individual Lyapunov exponents.
- Does **not** own the sum 8/5 (Chen–Möller).
- `promote_ready` remains **false** until deliberate re-measurement on live trajectories under formal gates.
- See root `NON_CLAIMS.md`.

## Vendored snapshot

`data/certified_snapshot/` holds the seed-728 path-local monodromy sum and
λ₂/λ₃ enclosure JSON so the default mode never requires a network fetch or
full Prym clone.
