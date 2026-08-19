# Fintech application map — PrymGyroSort v0.1.5.1-sieve

## Correct capability framing

| Strength | What it actually is | Finance use |
|----------|---------------------|-------------|
| **M=2 layer-rank (Fenwick)** | NSGA-II-style weak-dominance fronts, O(N log N) | Multi-objective portfolio / pair / factor tiers |
| **Quantile prefilter** | Approximate keep-top structural sieve | High-N candidate reduction before exact rank |
| **Insertion1D** | **Only when M=1** — sorted 1-D layers | Streaming percentiles, VaR order statistics |
| **Equal-x Fenwick fix** | Correct same-price / same-x dominance | Tied levels in books or identical scores |

**Not claimed:** live exchange matching engine, FIX/ITCH stack, microsecond guaranteed latency,
alpha generation, order routing, or production HFT colocation.

`promote_ready = false` remains in force.

## Mapped applications (honest)

### 1. Multi-objective portfolio / factor tiers (primary fit)
Objectives examples (lower = better after transform):
- obj0 = −expected return (or −momentum score)
- obj1 = variance, MDD, or tracking error

Layer-rank groups allocations into **non-dominated tiers**. Tier 1 = Pareto surface.

Module: `python/protocol_portfolio.py`

### 2. Pair / dislocation sieve (already shipped)
`protocol_finance.py` profiles: pairs | liquidity | stress | micro

### 3. Order-book impact depth (structural, offline / research)
Walk cumulative depth layers to estimate how far a market order consumes liquidity.
Uses sorted price levels (M=1 path) + optional M=2 (price vs size friction).

Module: `python/orderbook_impact.py`

### 4. Historical VaR order statistic (M=1)
Sort simulated PnL, take empirical quantile. Insertion1D / rank_1d is sufficient;
this is classical order statistics, not multi-objective ranking.

## What we deliberately do **not** build in this pass
- FIX/JSON exchange gateways (infra, not ranking theory)
- Live order-router or OMS
- Claims of “queue position = Fenwick index” as fill probability

## Run

```bash
python3 python/protocol_portfolio.py --n 500 --seed 7 --out-dir work
python3 python/prym_sieve_cli.py --matrix work/matrix.bin --n 500 --json

python3 python/orderbook_impact.py --n-levels 200 --order-size 5000 --seed 3
```
