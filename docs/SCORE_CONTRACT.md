# Score Contract v0.1 (DOM-AXX-001 / Phase-A++.0)

Machine-readable schema that freezes the two axes of a sealed front.
Strangers can recompute the contract hash and refuse a seal on mismatch
without trusting the producer.

## Schema

See `python/score_contract.schema.json`.

- Exactly two axes.
- `sense`: `"lower"` | `"higher"` (matches pair_sieve_cli `--x-sense` / `--y-sense`).
- `score_kind`: `"observed"` (default) | `"model"` | `"mixed"`.
  Predicted scores require a separate model seal; never treated as observed
  inside the dominance oracle.
- `formula_or_procedure_id` strongly encouraged (no free-text vibes).
- `additionalProperties: false`.

## Canonical hash rule (locked)

```python
import json, hashlib
canonical = json.dumps(contract, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
contract_hash = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
```

## Embedding in report.json (additive)

```json
"score_contract": { ... full object ... },
"score_contract_hash": "<64-hex>"
```

## verify_bundle

- Missing keys → soft pass (existing seals continue to work).
- Present → recompute hash from embedded `score_contract` and require exact
  match to `score_contract_hash`; mismatch fails closed.
- Optional `--require-contract` for strict mode (later).

## Honesty

The Score Contract defines the two axes and their sense only.
It does **not** claim that the numeric scores are truth about the future.
See NON_CLAIMS.
