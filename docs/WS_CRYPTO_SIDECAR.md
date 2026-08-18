# WebSocket Crypto Sidecar

Public Binance `bookTicker` → feature rows → `RankStream` zero-copy rank.

**No API keys. No order routing. Execution sieve only.**

## Mapping

| Field | Source |
|-------|--------|
| dislocation | \|mid − rolling mean\| |
| obi | (bidQty − askQty) / (bidQty + askQty) |
| bid_ask | ask − bid |
| depth | bidQty + askQty |
| mdd_proxy | (peak − mid) / peak |

## Usage

```bash
python3 python/ws_crypto_sidecar.py --duration 15 --interval-ms 200
python3 python/ws_crypto_sidecar.py --synthetic --duration 5
python3 python/ws_crypto_sidecar.py --duration 10 --fallback-synthetic
```

Some hosts may get HTTP 451 from Binance (geo policy); use `--fallback-synthetic` or run on an unrestricted network.

## Non-claims

Not a trading bot. Not alpha. `promote_ready=false`. See `NON_CLAIMS.md`.
