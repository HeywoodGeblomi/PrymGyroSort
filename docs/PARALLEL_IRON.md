# Parallel Binding Iron

4 workers simultaneously attack legal + illegal layouts.

| metric | value |
|:---|---:|
| legal OK | 160 |
| illegal caught | **400** |
| illegal missed | **0** |
| **ALL_PASS** | **True** |

Malformed (N,3) / Fortran / strided / float32 / bad ranks — all raise under multi-process load. Zero silent accepts.

```bash
python3 python/test_parallel_iron.py --workers 4
```

`promote_ready=false`
