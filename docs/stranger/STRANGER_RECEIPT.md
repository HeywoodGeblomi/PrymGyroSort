# Stranger Receipt — California Housing extract

**Source:** Public California Housing (1990 Census / Pace & Barry) two-column extract.
**Committed file:** `docs/stranger/california_housing_two_col.csv` is a **40-row sample**. It is not the 10,000-row slice.

## Sample identity (Fenwick oracle, c76dee0)

```
n              = 40
front_size     = 1
identity_mode  = fenwick_oracle
identity_ok    = true
identity_sha256 = ca9236b163c867ceeb98b0488fcc26a47369aeed8af92c834f7653dbec199315
promote_ready  = true   # when identity_ok (current product behavior)
```

Senses on the verify command below: `median_income` higher, `median_house_value` higher.

## 10,000-row rebuild

Rebuild steps, source URL, columns, row selection, and cap handling are in [SOURCE.md](SOURCE.md). The slice is not committed. At `c76dee0` it measures:

```
n              = 10000
front_size     = 31
identity_sha256 = 22cc811f06d78cf00792d4ccf941e96a09cd62b26170d9e58a93bcbc722fa67a
```

Before the `(x, y)` Fenwick flush (PR #28), the same 10,000-row file measured identity `3a94ab3104a0f77f7378639f08b816ca7f76b9b00bde432542c7afd682bdb417` and `front_size=32`. That older hash is pre-fix. Re-measure after any later kernel change.

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
