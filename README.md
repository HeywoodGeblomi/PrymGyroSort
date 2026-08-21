# PrymGyroSort — Pair Sieve Product

**Certified 2-objective isolation: the non-dominated deals from a CSV, with a Fenwick identity hash, in milliseconds at 1e5–1e6 rows.**

`promote_ready=false`. Exact ranking is Fenwick-only (GyroRank v0.2). No Scan2D. No LowAux2D.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Honesty](https://img.shields.io/badge/honesty-NON__CLAIMS-important)](NON_CLAIMS.md)

## Five-minute demo

```bash
python3 python/pair_sieve_cli.py --csv examples/book.csv --x-col risk --y-col cost --json --out /tmp/sieve
```

- **front.csv** — rows no other row beats on both scores
- **report.json** — `identity_ok`, `identity_sha256`, `strategy=Fenwick2D`
- Re-run Fenwick → same bits (`identity_mode=fenwick_repeat`)

## Honesty

Read **[NON_CLAIMS.md](NON_CLAIMS.md)**. Product is **isolation + proof**, not prediction. No alpha, no Lyapunov ownership, no live trading.

## Senses

```bash
python3 python/pair_sieve_cli.py --csv data.csv --x-col score --y-col cost \
  --x-sense higher --y-sense lower --json
```

higher-is-better = negate that column before Fenwick.

## Optional prefilters (off by default)

`--prefilter or_quantile` · `--prefilter prym`

## Prove / pick

```bash
python3 python/pair_sieve_cli.py --prove --json
python3 python/pair_sieve_cli.py --csv examples/book.csv --x-col risk --y-col cost --chi --json
```

## License

MIT. Kernel: [GyroRank](https://github.com/HeywoodGeblomi/GyroRank) Fenwick-only.
