# PrymGyroSort v0.1.3-finance

**Multi-objective ranking filter** — weak-dominance isolation of high-value candidates under competing objectives.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Container](https://img.shields.io/badge/container-docker-2496ED?logo=docker&logoColor=white)](#containerized)
[![Honesty](https://img.shields.io/badge/honesty-NON__CLAIMS-important)](NON_CLAIMS.md)

| Layer | Source |
|-------|--------|
| Ranking kernel | [GyroRank](https://github.com/HeywoodGeblomi/GyroRank) — GyroController + FenwickMax / LowAux2D |
| Geometric wire | [prym-eigenform-pipeline-d12](https://github.com/HeywoodGeblomi/prym-eigenform-pipeline-d12) path-local dual-Rauzy streams |
| Domain adapters | Finance pair-filter · synthetic / certified geometric ensemble |

## What it does

1. Accepts an **N × 2** objective matrix (`matrix.bin`, lower = better).
2. Ranks points by **weak dominance** (Pareto-style layers).
3. Isolates the cleanest candidates on the rank-1 / top-fraction front.

The C++ core is domain-agnostic. Python sidecars map geometry or market features into the frozen binary contract.

## Honesty (mandatory)

Read **[NON_CLAIMS.md](NON_CLAIMS.md)** before citing or promoting.

- Path-local / engineered class for geometric mode; execution sieve only for finance.
- Does **not** claim global Lyapunov exponents or ownership of 8/5.
- Does **not** generate trading alpha or guarantee profitable trades.
- EXTERNAL-clean / no-χ. Not a classical 1-D comparison sort.
- `promote_ready = false` for global spectral or live-trading claims.

## Quick start (local)

```bash
# Geometric / synthetic
python3 python/live_path_wire.py --mode synthetic --n 4096 --seed 728 --out-dir work
g++ -O3 -std=c++17 -Icpp/include cpp/rank_driver.cpp -o work/rank_driver
./work/rank_driver work/matrix.bin 4096 2 work
python3 python/self_check.py --dir work

# Finance pair-filter sieve
python3 python/protocol_finance.py --out-dir work --n 4096 --seed 42
./work/rank_driver work/matrix.bin 4096 2 work
python3 python/viz_pareto.py --dir work --format both
```

## Containerized

```bash
docker build -t prym-gyro-sort:0.1.3 .

# Geometric synthetic (default)
docker run --rm -e N=4096 -e SEED=728 -v "$PWD/work:/work" prym-gyro-sort:0.1.3

# Finance adapter
docker run --rm -e MODE=finance -e N=4096 -e SEED=42 -v "$PWD/work:/work" prym-gyro-sort:0.1.3

# Compose
docker compose run --rm prym-gyro-rank
docker compose --profile finance run --rm finance
docker compose --profile viz run --rm viz   # after ranking has filled ./work
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
├── Dockerfile  docker-compose.yml  entrypoint.sh
├── cpp/
│   ├── rank_driver.cpp
│   └── include/gyro_rank.hpp
├── python/
│   ├── live_path_wire.py       # Path-2 geometric / certified wire
│   ├── protocol_finance.py     # Finance pair-filter adapter
│   ├── viz_pareto.py           # Path-A ASCII + HTML Pareto
│   ├── scaling_campaign.py     # Measurement harness
│   ├── self_check.py
│   └── generate_geometric_matrix.py
├── examples/prym_gyro_demo.cpp
├── data/certified_snapshot/    # seed-728 path-local monodromy
└── docs/
    ├── PROTOCOL_FINANCE.md
    ├── PATH2_LIVE_WIRE.md
    ├── PATH_A_VIZ.md
    ├── SCALING_HARNESS.md
    └── SCALING_RESULTS.md
```

## Credits

Geometric scaffold: Heywood Geblomi / prym-eigenform-pipeline-d12  
Ranking kernel: GyroRank (TDPSK lineage)  
Integration: THE BEASTIE BOYZ

## License

MIT
