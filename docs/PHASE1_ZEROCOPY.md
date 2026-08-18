# Phase 1 — Zero-Copy Binding (hardened)

- Matrix/ranks must be **C-contiguous**.
- Non-contiguous → **raises** (no silent copy).
- `prym_gyro.rank()` applies `np.ascontiguousarray` first.
- Rank path has **no OpenMP parallel regions**.

```bash
cd python/bindings && python3 setup.py build_ext --inplace
```
