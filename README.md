# PrymGyroSort

## What

2-col CSV → undominated front + sha256. Exact Fenwick 2-D pair sieve. Sealed bundle is `front.csv` + `report.json` + `MANIFEST.sha256`.

## Run + verify

```bash
python3 python/pair_sieve_cli.py \
  --csv examples/book.csv --x-col risk --y-col cost \
  --bundle artifacts/golden/book

python3 python/verify_bundle.py artifacts/golden/book
# exit 0

sha256sum -c artifacts/golden/book.sha256
# or python3 python/verify_golden.py
```

Re-seal must match the checked-in `artifacts/golden/book` front and manifest. Default path is EXTERNAL-clean.

## Not a sort / not a forecast / default no-χ

Isolation + identity hash. Not a sort. Not a forecast. Not advice. Do not pass `--chi` on the default path. `--chi` is optional and non-default; golden and CI never pass it.

## Honesty

Read **[NON_CLAIMS.md](NON_CLAIMS.md)**.

---

## Optional χ (non-default)

```bash
python3 python/pair_sieve_cli.py \
  --csv examples/book.csv --x-col risk --y-col cost \
  --chi --bundle /tmp/bchi
python3 python/verify_bundle.py /tmp/bchi
```

When `--chi` is on, `chi_token` must contain `r_chi=`. A hash-only token fails verification. Not used in golden or CI.

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

## License

**Dual licensed.**

- Non-commercial / research / evaluation / non-production → **AGPLv3** (see [LICENSE](LICENSE) and [LICENSE-AGPL](LICENSE-AGPL))
- Any commercial use, production deployment, embedding, SaaS, or redistribution as product → **requires a commercial license** from the copyright holder (see [LICENSE-COMMERCIAL](LICENSE-COMMERCIAL) and [COMMERCIAL.md](COMMERCIAL.md)).

Copyright (c) 2026 Heywood Geblomi.

Kernel: [GyroRank](https://github.com/HeywoodGeblomi/GyroRank) Fenwick-only (library; not promoted as an OS).
