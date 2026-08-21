# GYR-HOOK-001 F3 — live path

External menu only (F2 Photonic emit skipped).

```bash
# rank step: data checksum must not change
python3 python/hook/live.py \
  --csv tests/fixtures/hook_menu.csv \
  --json

# rank then one talent invoke (stand-in sort after chosen_id)
python3 python/hook/live.py \
  --csv tests/fixtures/hook_menu.csv \
  --invoke --json
```

- `checksum_stable_through_rank=true` required
- `identity_mode=fenwick_oracle`
- `promote_ready=false`
- Sort / talent runs **once**, only after `chosen_id` is recorded
