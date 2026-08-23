# WORLD-A — 15-minute stranger path

**Exact 2-objective sealed front + offline verify.**  
This is the public recipe for the sealed-front product in PrymGyroSort.  
No ranking OS claims. No forecasts. No trading advice. See [NON_CLAIMS.md](../NON_CLAIMS.md).

When two independent machines produce the same `identity_sha256` on the same input and both pass `verify_bundle`, you have external evidence. When a non-authored workflow fails if `verify_bundle` fails, you have A-shaped use.

**Until at least one independent external matching identity exists, do not claim absolute A.** The product is `promote_ready=true` for the sealed-front job only.

## Prerequisites (≤2 min)

- Python 3.8+
- `numpy`, `pybind11`, a C++17 compiler (`g++` or equivalent)
- ~30–60 s for the one-time native binding build

```bash
git clone --branch v0.7.0-world-a https://github.com/HeywoodGeblomi/PrymGyroSort.git
cd PrymGyroSort
python3 -m pip install --upgrade pip
python3 -m pip install numpy pybind11 setuptools wheel
cd python/bindings && python3 setup.py build_ext --inplace && cd ../..
export PYTHONPATH="${PWD}/python:${PWD}/python/bindings"
```

(`v0.7.0-world-a` pins the sealed-front identity. Later main is compatible for the Fenwick identity; Score Contract / Front Diff are additive product layers and do not change the identity hash for the same input.)

## Path A — Book example (built-in, ~30 s)

```bash
python3 python/pair_sieve_cli.py \
  --csv examples/book.csv \
  --x-col risk --y-col cost \
  --bundle /tmp/book

python3 python/verify_bundle.py /tmp/book
# expect: exit 0
```

## Path B — Stranger (California Housing extract, committed CSV, ~30 s)

The repo already contains a ≥10k two-column extract of the public California Housing data set (1990 Census / Pace & Barry). No network required.

```bash
python3 python/pair_sieve_cli.py \
  --csv docs/stranger/california_housing_two_col.csv \
  --x-col median_income --y-col median_house_value \
  --x-sense higher --y-sense higher \
  --bundle /tmp/stranger

python3 python/verify_bundle.py /tmp/stranger
# expect: exit 0
```

Inspect the seal:

```bash
cat /tmp/stranger/report.json
# note identity_sha256, identity_ok=true, identity_mode=fenwick_oracle, promote_ready=true
```

**Expected locked identity for the committed extract:**

```
identity_sha256 = 3a94ab3104a0f77f7378639f08b816ca7f76b9b00bde432542c7afd682bdb417
n = 10000
front_size = 32
```

Recorded in [docs/stranger/STRANGER_RECEIPT.md](stranger/STRANGER_RECEIPT.md). Re-measure only after a kernel / Fenwick change.

Optional provenance re-filter (requires network + pandas):

```bash
python3 -m pip install pandas
python3 docs/stranger/filter_california_housing.py   # rewrites the csv from the public URL
# then re-run the --bundle + verify steps above
```

## Publish your result (the external evidence step)

Open a [Discussion](https://github.com/HeywoodGeblomi/PrymGyroSort/discussions) or Issue and post:

- the `identity_sha256` from `report.json`
- machine note (OS, Python version, compiler if known)
- optional: `MANIFEST.sha256` contents or a link to your bundle

Two independent machines agreeing on the same input hash + report hash constitutes external reproduction.

## What this is / is not

| Is | Is not |
|----|--------|
| Exact undominated set for two numeric scores | Multi-objective evolutionary search (NSGA etc.) |
| Offline `verify_bundle` pass/fail | Predictive model or forecast |
| Fenwick identity hash (reproducible) | Ranking OS or second kernel |
| Optional χ pick (default off) | Investment / trading advice |

Kernel remains [GyroRank](https://github.com/HeywoodGeblomi/GyroRank) Fenwick-only library. Ranker is not promoted as a universal OS.

## CI gate

Every push to `main` runs the book + California sealed paths above and asserts `verify_bundle` exit 0. See `.github/workflows/prove.yml`.

## GitHub About (UI)

Repository description should read:

> Exact 2-D Fenwick pair sieve. CSV in → sealed undominated front + identity hash + offline verify. promote_ready=true for this job only. Not a sort. Not a forecast.

---

*WORLD-A-002. Absolute A in this niche requires at least one external reproduction (independent matching identity_sha256) and one non-authored use that fails when verify fails. Until then, do not claim A. promote_ready remains job-scoped only.*
