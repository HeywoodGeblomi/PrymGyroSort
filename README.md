# PrymGyroSort v0.1.1-prototype

**Prototype Sorter — multi-objective geometric ranking filter**

| Role | Source |
|------|--------|
| Array structure | [prym-eigenform-pipeline-d12](https://github.com/HeywoodGeblomi/prym-eigenform-pipeline-d12) (period vectors of $S(1,-2)$, path-local dual Rauzy evaluation streams) |
| Sorter kernel | [GyroRank](https://github.com/HeywoodGeblomi/GyroRank) (adaptive multi-objective ranking, GyroController + FenwickMax exact 2-D weak-dominance) |

## What it does

1. Generates an ensemble of geometric evaluation points (certificate-anchored + residual cloud).
2. Each point carries **M = 2 objectives** (lower = better):
   - **obj0**: convergence residual $|\text{local pos-sum proxy} - 8/5|$
   - **obj1**: controlled QR / geometric residual proxy
3. Feeds the $N \times 2$ matrix into `gyro::execute_gyro_rank`.
4. Returns weak-dominance ranks → Pareto-style isolation of the cleanest path-local seeds / segments.

## Honesty (mandatory)

Read **[NON_CLAIMS.md](NON_CLAIMS.md)** before citing or promoting.

- Path-local engineered class only.
- Does **not** claim global individual Lyapunov exponents $\lambda_2=2/5$, $\lambda_3=1/5$.
- Does **not** claim ownership of the sum $8/5$ (Chen–Möller).
- EXTERNAL-clean / no-$\chi$. Not a classical 1-D comparison sort.
- Synthetic generator is certificate-anchored for self-check; live pure-path wiring is follow-on.

## Scale & Memory Boundaries (v0.1.1-prototype)

* **Gating Threshold:** At $N \ge 65536$ or when `memory_pressure` is manually invoked, the `GyroController` explicitly flags a strategy deflection from the high-throughput `FenwickMax` path to the `LowAux2D` kernel.
* **Auxiliary Space Integrity:** The `LowAux2D` fallback preserves the $O(N \log N)$ time complexity but enforces rigid, low-overhead array bounds. Sub-linear auxiliary space ranking ($o(N)$) is explicitly **not claimed** and remains future work.
* **Measured footprint:** N=4096 ≈ 1.5–2 ms (Fenwick); N=65536 + memory_pressure ≈ 40 ms (LowAux path). Certificate-anchored anchors remain isolated (recall 1.0).
* **Spectral Disconnect:** Running at higher $N$ scales local resolution, but `promote_ready` remains strictly **false** for any global spectral or Lyapunov exponent claims.

See [docs/SCALE_NOTES.md](docs/SCALE_NOTES.md).

## Quick start (local)

```bash
python3 python/generate_geometric_matrix.py --n 4096 --seed 728 --out-dir work
g++ -O3 -std=c++17 -Icpp/include cpp/rank_driver.cpp -o work/rank_driver
./work/rank_driver work/matrix.bin 4096 2 work
python3 python/self_check.py --dir work
```

Or pure demo:

```bash
g++ -O3 -std=c++17 -Iinclude examples/prym_gyro_demo.cpp -o prym_gyro_demo
./prym_gyro_demo 4096 48 0
./prym_gyro_demo 65536 128 1   # memory_pressure
```

## Containerized

```bash
docker build -t prym-gyro-sort:0.1.1 .
docker run --rm -e N=4096 -e SEED=728 prym-gyro-sort:0.1.1
```

## Self-check criteria

- ≥ 60% of certificate-anchored low-residual points in top 5% ranks
- Mean rank of good anchors < mean rank of residual cloud
- Soft timing gate from rank_report (optional)

Measured: **GREEN** at N=4096 and N=65536.

## Layout

```
PrymGyroSort/
├── README.md / NON_CLAIMS.md / LICENSE
├── Dockerfile / docker-compose.yml / entrypoint.sh
├── cpp/rank_driver.cpp + include/gyro_rank.hpp
├── python/generate_geometric_matrix.py + self_check.py
├── examples/prym_gyro_demo.cpp
└── docs/SCALE_NOTES.md
```

## Credits

Geometric scaffold: Heywood Geblomi / prym-eigenform-pipeline-d12  
Ranking kernel: GyroRank (TDPSK lineage)  
Integration: THE BEASTIE BOYZ

## License

MIT
