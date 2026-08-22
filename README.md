# PrymGyroSort — Sealed Front Product

**CSV two scores in → sealed undominated front out. Offline `verify_bundle` pass/fail.** Exact Fenwick identity hash. Optional χ pick (default off). Ranker stays a library.

`promote_ready=true` for this job only — not a universal ranking OS, not a second kernel, not investment advice.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Honesty](https://img.shields.io/badge/honesty-NON__CLAIMS-important)](NON_CLAIMS.md)

## Seal and verify

```bash
# Seal
python3 python/pair_sieve_cli.py \
  --csv examples/book.csv --x-col risk --y-col cost \
  --bundle /tmp/b

# Verify offline (exit 0 = pass)
python3 python/verify_bundle.py /tmp/b
```

Bundle contents:

- **front.csv** — undominated rows + rank (optional `chi_pick` mark)
- **report.json** — `identity_ok`, `identity_sha256`, `identity_mode=fenwick_oracle`, `strategy=Fenwick2D`, `promote_ready`
- **MANIFEST.sha256** — SHA-256 of `front.csv` and `report.json` only

Stranger path (California Housing extract):

```bash
python3 docs/stranger/filter_california_housing.py
python3 python/pair_sieve_cli.py \
  --csv docs/stranger/california_housing_two_col.csv \
  --x-col median_income --y-col median_house_value \
  --x-sense higher --y-sense higher \
  --bundle /tmp/stranger
python3 python/verify_bundle.py /tmp/stranger
```

## Optional χ (default off)

```bash
python3 python/pair_sieve_cli.py \
  --csv examples/book.csv --x-col risk --y-col cost \
  --chi --bundle /tmp/bchi
python3 python/verify_bundle.py /tmp/bchi
```

When `--chi` is on, `chi_token` must contain `r_chi=` (commit+reveal tape). A hash-only token fails verification.

## Senses

```bash
python3 python/pair_sieve_cli.py --csv data.csv --x-col score --y-col cost \
  --x-sense higher --y-sense lower --bundle /tmp/s
```

higher-is-better = negate that column before Fenwick.

## Optional prefilters (off by default)

`--prefilter or_quantile` · `--prefilter prym`

## Prove

```bash
python3 python/pair_sieve_cli.py --prove --json
```

## Honesty

Read **[NON_CLAIMS.md](NON_CLAIMS.md)**. Product is **isolation + proof**, not prediction. No alpha, no live trading, not multi-objective NSGA.

## License

MIT. Kernel: [GyroRank](https://github.com/HeywoodGeblomi/GyroRank) Fenwick-only (library; not promoted as an OS).
