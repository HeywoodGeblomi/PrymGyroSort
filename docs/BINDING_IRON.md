# Binding Iron Tests

`python/test_binding_iron.py` — **11/11 PASS**

| Case | Result |
|------|--------|
| C-contiguous (N,2) float64 | PASS |
| python helper `rank()` | PASS |
| reject (N,3) | PASS |
| reject (N,) | PASS |
| reject 3-D | PASS |
| reject Fortran-order | PASS |
| reject strided non-contig | PASS |
| reject float32 | PASS |
| reject ranks wrong length | PASS |
| reject ranks float64 | PASS |
| helper copies F-order | PASS |

No silent copy on the native path. Helper may copy then rank.

```bash
python3 python/test_binding_iron.py
```

`promote_ready=false`
