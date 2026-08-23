# Stranger Receipt — California Housing extract

**Source:** Public California Housing (1990 Census / Pace & Barry) two-column extract.
**Producer:** `docs/stranger/filter_california_housing.py` (authoritative; pulls public URL when run with network).
**Committed file:** `docs/stranger/california_housing_two_col.csv` (≥10k rows, no network required for stranger path).

## Locked identity (Fenwick oracle)

```
n              = 10000
front_size     = 32
identity_mode  = fenwick_oracle
identity_ok    = true
identity_sha256 = 3a94ab3104a0f77f7378639f08b816ca7f76b9b00bde432542c7afd682bdb417
promote_ready  = true   # when identity_ok (current product behavior)
```

Re-measure after any kernel / Fenwick change. Additive product layers (Score Contract, Front Diff) do not alter this Fenwick identity for the same input.

Tip compatibility: v0.7.0-world-a and later main (as of 2026-08-23) produce the same identity_sha256.

## Verify

```bash
python3 python/pair_sieve_cli.py \
  --csv docs/stranger/california_housing_two_col.csv \
  --x-col median_income --y-col median_house_value \
  --x-sense higher --y-sense higher \
  --bundle /tmp/stranger

python3 python/verify_bundle.py /tmp/stranger   # exit 0
cat /tmp/stranger/report.json                   # identity_sha256 must match above
```

THE BEASTIE BOYZ · WORLD-A
