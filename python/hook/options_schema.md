# Hook options schema (GYR-HOOK-001)

Menu matrix for the scheduler sidecar: **N_opt × 2** float64 scores.

## CSV

| Column | Type | Required | Notes |
|--------|------|----------|--------|
| `id` | string | yes | Talent name or block id (token) |
| `score0` | float64 | yes | First objective |
| `score1` | float64 | yes | Second objective |

Extra columns are ignored. Header required.

## Senses

Default: **lower, lower** (same as pair sieve). Optional `--x-sense` / `--y-sense` (`lower`|`higher`).

## Ranking

- Public ranks: `prym_gyro.rank`
- Reference: `prym_gyro.rank_fenwick_ref` → `exact_rank_2d_fenwick`
- `identity_ok` iff bit-identical; `identity_mode=fenwick_oracle`

## Output

- Rank-1 set **F** (undominated ids)
- Default: all of F (`chosen_ids`)
- `--chi`: one pick ∈ F
- `|F|==0` → exit 2, no invented id
- `|F|==1` → that id
- Every JSON: `promote_ready=false`

## Named falsifier (fixture)

`tests/fixtures/hook_menu.csv` (8 rows): under default lower/lower must **keep** `{A,B}` and **drop** `{G,H}`.

## Non-goals

No write into Photonic arrays; no GyroRank header edit; no claim that GyroRank sorts or Photonic ranks.
