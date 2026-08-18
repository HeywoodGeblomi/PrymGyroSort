# Network Jitter Resilience

Simulated WS delivery pathologies on symbol-stable drift + quantile sieve.

| mode | n delivered | J@top | S@top | ΔJ vs clean | ΔS vs clean |
|:---|---:|---:|---:|---:|---:|
| clean | 60 | 0.429 | 0.600 | 0.000 | 0.000 |
| drop (15%) | 51 | 0.429 | 0.600 | 0.000 | 0.000 |
| reorder | 60 | 0.429 | 0.600 | 0.000 | 0.000 |
| delay | 60 | 0.429 | 0.600 | 0.000 | 0.000 |
| burst | 60 | 0.429 | 0.600 | 0.000 | 0.000 |

On mild drift (σ=0.15), median front durability held under drop/reorder/delay/burst.
Does **not** claim live exchange immunity.

```bash
python3 python/bench_network_jitter.py --ticks 60 --symbols 100
```

`promote_ready=false`
