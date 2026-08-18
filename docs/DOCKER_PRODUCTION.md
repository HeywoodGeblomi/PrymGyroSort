# Production Container

Multi-stage. Non-root `quantoperator` (uid 10001). Portable ISA by default.

## Adversarial facts

| Claim | Verdict |
|-------|---------|
| Multi-stage strips compilers from runtime | **TRUE** |
| Non-root reduces privilege if native code is abused | **TRUE** (mitigation, not exploit-proof) |
| `-march=native` in published image can SIGILL elsewhere | **TRUE** — default portable; optional `MARCH=x86-64-v3` |
| OpenMP multi-threaded kernel in image | **FALSE** — no `#pragma omp` |

## Build / run

```bash
docker build -t prym-gyro-sieve:latest .
docker build --build-arg MARCH=x86-64-v3 -t prym-gyro-sieve:v3 .

docker run --rm prym-gyro-sieve:latest --n 4096 --seed 42
docker run --rm -v "$(pwd)/work:/app/work" prym-gyro-sieve:latest --n 4096 --out /app/work
```

`promote_ready=false`. Execution sieve only.
