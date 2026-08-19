# PrymGyroSort v0.1.5-sieve

**Multi-objective ranking filter** — weak-dominance isolation of high-value candidates under competing objectives.

[![Release](https://img.shields.io/github/v/release/HeywoodGeblomi/PrymGyroSort)](https://github.com/HeywoodGeblomi/PrymGyroSort/releases/tag/v0.1.5-sieve)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Container](https://img.shields.io/badge/container-docker-2496ED?logo=docker&logoColor=white)](#containerized)
[![Honesty](https://img.shields.io/badge/honesty-NON__CLAIMS-important)](NON_CLAIMS.md)

| Layer | Source |
|-------|--------|
| Ranking kernel | [GyroRank](https://github.com/HeywoodGeblomi/GyroRank) — GyroController + FenwickMax / LowAux2D |
| Geometric wire | [prym-eigenform-pipeline-d12](https://github.com/HeywoodGeblomi/prym-eigenform-pipeline-d12) path-local dual-Rauzy streams |
| Domain adapters | Finance profiles · synthetic / certified geometric ensemble |

## What it does

1. Accepts an **N × 2** objective matrix (`matrix.bin` or synthetic), lower = better.
2. Optional **static OR-quantile** prefilter, then ranks by **weak dominance**.
3. Isolates rank-1 / top-fraction candidates.

The C++ core is domain-agnostic. Python sidecars map geometry or market features into the frozen binary contract.

## Honesty (mandatory)

Read **[NON_CLAIMS.md](NON_CLAIMS.md)** before citing or promoting.

- Execution sieve only — structural ranking, not a predictive model.
- Does **not** claim global Lyapunov exponents or ownership of 8/5.
- Does **not** generate trading alpha or guarantee profitable trades.
- EXTERNAL-clean / no-χ. Not a classical 1-D comparison sort.
- `promote_ready = false` for global spectral or live-trading claims.

## Quick start (container)

```bash
docker build -t prym-gyro-sieve:latest .

# Self-check (exit 0 = PASS)
docker run --rm prym-gyro-sieve:latest --self-check

# Synthetic smoke
docker run --rm prym-gyro-sieve:latest --n 4096 --seed 42 --json

# Finance stress profile → rank
mkdir -p work
docker run --rm --entrypoint python3 -v "$PWD/work:/app/work" prym-gyro-sieve:latest \
  /app/python/protocol_finance.py --profile stress --n 4096 --out-dir /app/work
docker run --rm -v "$PWD/work:/app/work" prym-gyro-sieve:latest \
  --matrix /app/work/matrix.bin --n 4096 --json
```

## Finance profiles

| Profile | Emphasis |
|---------|----------|
| `pairs` | dislocation × OBI vs liquidity/MDD (default) |
| `liquidity` | depth / spread resilience |
| `stress` | drawdown / gap risk |
| `micro` | OBI×dislocation pressure vs friction |

Structural mapping only — **not** an order router.

## Production hardening

| Feature | Behavior |
|---------|----------|
| Exit codes | 0 ok · 1 usage · 2 data · 3 runtime · 4 self-check fail |
| Guards | shape `(N,2)`, NaN/Inf, empty, size match |
| `--self-check` / `--json` | operational probes |
| Docker | multi-stage · non-root · HEALTHCHECK · portable ISA |

## Local (no Docker)

```bash
python3 python/protocol_finance.py --profile pairs --n 4096 --out-dir work
python3 python/prym_sieve_cli.py --matrix work/matrix.bin --n 4096 --json
```

## Measured scaling (LowAux2D, `memory_pressure=1`)

| N | Wall time | Top-frac recall | Separation gap |
|---:|---:|---:|---:|
| 65,536 | ~38 ms | 1.000 | +230.7 |
| 262,144 | ~198 ms | 1.000 | +449.4 |
| 1,048,576 | ~1188 ms | 1.000 | +898.8 |

Full table: [docs/SCALING_RESULTS.md](docs/SCALING_RESULTS.md).  
Asymptotic o(N) auxiliary ranking is **not claimed**.

## Layout

```
PrymGyroSort/
├── README.md  NON_CLAIMS.md  LICENSE  RELEASE_NOTES.md
├── Dockerfile  docker-compose.yml
├── cpp/include/gyro_rank.hpp   # frozen M=2 kernel
├── python/
│   ├── prym_sieve_cli.py       # production entry (hardened)
│   ├── protocol_finance.py     # multi-profile finance adapter
│   ├── prefilter_rank.py       # static OR-quantile
│   ├── bindings/               # zero-copy native .so
│   └── sieve_durability.py     # long-horizon tracker
└── docs/
```

## Credits

Geometric scaffold: Heywood Geblomi / prym-eigenform-pipeline-d12  
Ranking kernel: GyroRank (TDPSK lineage)  
Integration: THE BEASTIE BOYZ

## License

MIT
