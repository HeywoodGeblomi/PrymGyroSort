# M=3 Tensor Sieve (honest lab)

Ground truth = **exact 3-D weak-dominance** (Python O(N²) layer peel).  
Filter = static vs dynamic OR-quantile.  
**No** `prym_gyro_native.rank_m3` — does not exist. Kernel stays **M=2**.

| N | mode | q_used | keep% | speedup | R@1 | R@top |
|---:|:---|---:|---:|---:|---:|---:|
| 400 | static | 0.250 | 39.5% | **6.78** | 1.00 | 1.00 |
| 400 | dynamic | 0.354 | 59.8% | 3.08 | 1.00 | 1.00 |
| 800 | static | 0.250 | 50.0% | **5.28** | 1.00 | 1.00 |
| 800 | dynamic | 0.376 | 71.0% | 2.40 | 1.00 | 1.00 |
| 1200 | static | 0.250 | 52.4% | **4.91** | 1.00 | 1.00 |
| 1200 | dynamic | 0.382 | 73.1% | 2.23 | 1.00 | 1.00 |

## Verdict on this suite

- Both filters hold **R@1 = R@top = 1.0** (planted-front ensemble).
- **Static q=0.25 is faster** (higher speedup); dynamic widens the gate and pays latency.
- DQVA does not earn its keep here — same recall, worse speed.

## Non-claims

- Not a C++ M=3 kernel.
- Not universal 3-D recall proof.
- `promote_ready=false`

```bash
python3 python/tensor_sieve.py --ladder 400,800,1200 --reps 2
```
