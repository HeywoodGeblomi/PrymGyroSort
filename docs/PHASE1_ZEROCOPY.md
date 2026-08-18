# Phase 1 — Zero-Copy Binding

**Status:** implemented (pybind11 sidecar)  
**Core impact:** none — `gyro_rank.hpp` is included read-only

## Goal

Delete the file-path RTT between Python and the ranking kernel by passing
contiguous NumPy buffers via raw pointers.

## API

```python
from prym_gyro import rank, rank_report
import numpy as np

X = np.ascontiguousarray(objs, dtype=np.float64)  # (N, 2)
ranks = rank(X)                                   # int32[N]
info = rank_report(X)                             # ranks + strategy dict
```

## Build

```bash
cd python/bindings
python3 setup.py build_ext --inplace
# requires: pybind11, numpy, python3-dev, g++
```

## Microbench (reference host)

| N | Zero-copy median | File-path median | Notes |
|---:|---:|---:|------|
| 4096 | ~1.6 ms | ~13 ms | file path includes process spawn + IO |
| 65536 | ~72 ms | ~69 ms | ranking dominates; spawn amortized |

Isolation held (μ_good ≪ μ_rest) on both sizes.

## Non-claims

- Not a trading system. Execution-sieve ranking only.
- Docker image defaults remain the portable file-path container.
- Native `-march=native -fopenmp` is a separate optional profile (Phase 2).
