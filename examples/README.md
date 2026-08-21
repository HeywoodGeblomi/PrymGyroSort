# Deal packs — Pair Sieve Product

Three named CSVs. Isolation only: undominated rows on two scores. Not a trading system, not a valuation model.

| Pack | File | x (sense) | y (sense) | Who uses this |
|------|------|-----------|-----------|---------------|
| **Book** | `book.csv` | risk / drawdown (**lower**) | cost / friction (**lower**) | Anyone ranking book risk vs execution cost |
| **Listing** | `listing.csv` | price (**lower**) | repair / days-on-market (**lower**) | Shortlist candidates under budget and condition |
| **Latency** | `latency.csv` | p99_ms (**lower**) | error_rate (**lower**) | Pick services that are both fast and reliable |

All packs are **synthetic=true** (labeled). ≥200 rows each. No NaNs.

## Exact CLIs

```bash
# Book
python3 python/pair_sieve_cli.py --csv examples/book.csv --x-col risk --y-col cost --json --out /tmp/book

# Listing
python3 python/pair_sieve_cli.py --csv examples/listing.csv --x-col price --y-col repair_days --json --out /tmp/listing

# Latency
python3 python/pair_sieve_cli.py --csv examples/latency.csv --x-col p99_ms --y-col error_rate --json --out /tmp/latency

# Sugar (optional)
python3 python/pair_sieve_cli.py --pack listing --json --out /tmp/listing
```

Open `/tmp/<pack>/front.csv` in Excel. `report.json` carries `identity_ok` and `identity_sha256`.

## Sample shape (expect)

| Field | Typical |
|-------|--------|
| n | ≥200 |
| front_size | ≥1 |
| wall_ms | milliseconds |
| identity_ok | true |
| promote_ready | false |

Do not claim the Book pack is a trading system. Do not claim the Listing pack values property. Isolation only.
