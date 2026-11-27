"""k-score weak dominance and deterministic cap-tie policies.

Weak dominance, lower is better: row A dominates row B when A is <= B on
every score and < B on at least one. Identical rows do not dominate each
other. The layer of a row is 1 plus the maximum layer among rows that
dominate it. Rows with no dominator are layer 1.

k = 2 uses exact_rank_2d_fenwick. That path is the one whose bytes are
compared to the book, housing, and abalone identities. k > 2 uses
dominance_graph_v1: build the dominance DAG, then set each layer when every
dominator is known. Time is O(k n^2). Memory is O(n + E), where E is the
number of dominating pairs and E <= n(n-1). This is not a timed speed claim.

The brute oracle used by tests is layer relaxation: repeat a full pair scan
until the layers stop changing. Each pass is O(k n^2) and there are at most
n passes, so the worst case is O(k n^3).

Cap policies
------------
A cap is a positive integer K, the number of rows requested. Layers are
walked from 1 upward. If K lands exactly on a layer boundary, every policy
keeps the same rows and boundary_rows is 0. If K falls inside a layer, that
layer is the boundary and boundary_rows is its size.

- include_all_tied: keep the whole boundary layer. This is order-independent
  and, when the table has at least one row, it does not return an empty
  selection. It can exceed the cap. tiebreak_key is "none".
- exclude_tied: drop the whole boundary layer. This is order-independent and
  a hard ceiling (the selection is never larger than the cap). It can return
  zero rows. tiebreak_key is "none".
- strict_cap: keep every layer before the boundary, then fill the remaining
  slots so the selection has exactly min(cap, n) rows. It is order-independent
  only when the tiebreak key is unique on the boundary. The tiebreak used when
  the caller does not name one is input_index, ascending. A named secondary
  key is ascending raw value, then input_index. Equal keys use that index, so
  the policy is recorded as not order-independent.

Default policy: include_all_tied. strict_cap and exclude_tied stay available.
Same input and the same policy produce the same selection mask bytes.
Receipts that already name a policy keep that policy; this default applies
only when the caller does not name one.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

POLICIES = ("include_all_tied", "exclude_tied", "strict_cap")
DEFAULT_POLICY = "include_all_tied"
DEFAULT_TIEBREAK = "input_index"
GRAPH_METHOD = "dominance_graph_v1"
FENWICK_METHOD = "exact_rank_2d_fenwick"
GRAPH_COMPLEXITY = "O(k n^2) time, O(n + E) memory, E = number of dominating pairs"
FENWICK_COMPLEXITY = "O(n log n) time after the (x, y) sort"
RELAX_COMPLEXITY = "O(L k n^2) with L <= n, so O(k n^3) worst case"


def permutation_invariant(policy: str) -> bool:
    return policy in ("include_all_tied", "exclude_tied")


def normalize_policy(policy: str | None, tiebreak_key: str | None) -> tuple[str, str]:
    name = DEFAULT_POLICY if policy is None else policy
    if name not in POLICIES:
        raise ValueError(f"unknown cap policy {name!r}")
    if name == "strict_cap":
        key = DEFAULT_TIEBREAK if tiebreak_key is None else tiebreak_key
        if key in ("", "none"):
            raise ValueError("strict_cap needs a tiebreak key")
        return name, key
    if tiebreak_key not in (None, "none"):
        raise ValueError(f"{name} does not take a tiebreak key")
    return name, "none"


def row_dominates(a: np.ndarray, b: np.ndarray) -> bool:
    """True when a weakly dominates b."""
    strict = False
    for t in range(int(a.shape[0])):
        av = float(a[t])
        bv = float(b[t])
        if av > bv:
            return False
        if av < bv:
            strict = True
    return strict


def rank_layers_graph(X: np.ndarray) -> np.ndarray:
    """Layer assignment for any k >= 2. See the module docstring for cost."""
    data = np.asarray(X, dtype=np.float64)
    if data.ndim != 2 or data.shape[1] < 2:
        raise ValueError("matrix must have shape (n, k) with k >= 2")
    n = int(data.shape[0])
    children: list[list[int]] = [[] for _ in range(n)]
    indegree = [0] * n
    for i in range(n):
        ai = data[i]
        for j in range(i + 1, n):
            if row_dominates(ai, data[j]):
                children[i].append(j)
                indegree[j] += 1
            elif row_dominates(data[j], ai):
                children[j].append(i)
                indegree[i] += 1
    ranks = [0] * n
    best = [0] * n
    queue = [i for i in range(n) if indegree[i] == 0]
    for i in queue:
        ranks[i] = 1
    head = 0
    while head < len(queue):
        i = queue[head]
        head += 1
        ri = ranks[i]
        for child in children[i]:
            if ri > best[child]:
                best[child] = ri
            indegree[child] -= 1
            if indegree[child] == 0:
                ranks[child] = best[child] + 1
                queue.append(child)
    if any(r == 0 for r in ranks):
        raise RuntimeError("dominance graph was not a DAG")
    return np.asarray(ranks, dtype=np.int32)


def rank_layers_relax(X: np.ndarray) -> np.ndarray:
    """Independent layer oracle. Worst case O(k n^3). For checks, not the fast path."""
    data = np.asarray(X, dtype=np.float64)
    n = int(data.shape[0])
    ranks = np.ones(n, dtype=np.int32)
    for _ in range(max(n, 1)):
        nxt = np.ones(n, dtype=np.int32)
        changed = False
        for i in range(n):
            best = 0
            bi = data[i]
            for j in range(n):
                if i != j and row_dominates(data[j], bi):
                    rj = int(ranks[j])
                    if rj > best:
                        best = rj
            layer = best + 1
            nxt[i] = layer
            if layer != int(ranks[i]):
                changed = True
        ranks = nxt
        if not changed:
            return ranks
    raise RuntimeError("layer relaxation did not settle")


def rank_layers(X: np.ndarray) -> np.ndarray:
    """Return the int32 layer vector. k = 2 is the Fenwick fast path."""
    data = np.ascontiguousarray(X, dtype=np.float64)
    if data.ndim != 2 or data.shape[1] < 2:
        raise ValueError("matrix must have shape (n, k) with k >= 2")
    if data.shape[1] == 2:
        from prym_gyro import exact_rank_2d
        return np.asarray(exact_rank_2d(data[:, 0], data[:, 1]), dtype=np.int32)
    return rank_layers_graph(data)


def rank_method_name(k: int) -> str:
    return FENWICK_METHOD if int(k) == 2 else GRAPH_METHOD


def rank_complexity(k: int) -> str:
    return FENWICK_COMPLEXITY if int(k) == 2 else GRAPH_COMPLEXITY


def _cut(ranks: np.ndarray, cap: int | None) -> dict:
    n = int(ranks.shape[0])
    if cap is None:
        return {"kind": "none", "layer": None, "boundary_rows": 0, "prefix_before": n, "take": n}
    kcap = int(cap)
    if kcap < 1:
        raise ValueError("cap must be >= 1")
    if kcap >= n:
        return {"kind": "none", "layer": None, "boundary_rows": 0, "prefix_before": n, "take": n}
    max_layer = int(ranks.max()) if n else 0
    counts = np.bincount(ranks, minlength=max_layer + 1)
    prefix = 0
    for layer in range(1, int(counts.shape[0])):
        count = int(counts[layer])
        if count == 0:
            continue
        if prefix + count > kcap:
            return {
                "kind": "inside",
                "layer": layer,
                "boundary_rows": count,
                "prefix_before": prefix,
                "take": kcap - prefix,
            }
        prefix += count
        if prefix == kcap:
            return {
                "kind": "exact",
                "layer": layer,
                "boundary_rows": 0,
                "prefix_before": prefix,
                "take": 0,
            }
    return {"kind": "none", "layer": None, "boundary_rows": 0, "prefix_before": prefix, "take": 0}


def _boundary_order(boundary: np.ndarray, tiebreak_key: str, tiebreak_values, n: int) -> np.ndarray:
    if tiebreak_key == "input_index":
        return np.sort(np.asarray(boundary, dtype=np.int32))
    if tiebreak_values is None:
        raise ValueError(f"tiebreak values missing for {tiebreak_key}")
    values = np.asarray(tiebreak_values, dtype=np.float64).reshape(-1)
    if int(values.shape[0]) != n:
        raise ValueError("tiebreak values length does not match rows")
    if not np.isfinite(values).all():
        raise ValueError("tiebreak values must be finite")
    ordered = sorted((float(values[int(i)]), int(i)) for i in boundary)
    return np.asarray([i for _, i in ordered], dtype=np.int32)


def selection_sha256(mask: np.ndarray) -> str:
    arr = np.ascontiguousarray(mask, dtype=np.int32)
    return hashlib.sha256(arr.tobytes()).hexdigest()


def apply_cap(
    ranks: np.ndarray,
    cap: int | None,
    policy: str | None = None,
    tiebreak_key: str | None = None,
    tiebreak_values=None,
) -> tuple[np.ndarray, dict]:
    """Return an int32 0/1 mask and the cap record for that mask."""
    name, key = normalize_policy(policy, tiebreak_key)
    layers = np.asarray(ranks, dtype=np.int32).reshape(-1)
    info = _cut(layers, cap)
    n = int(layers.shape[0])
    mask = np.zeros(n, dtype=np.int32)
    if info["kind"] == "none":
        mask[:] = 1
    elif info["kind"] == "exact":
        mask[layers <= int(info["layer"])] = 1
    else:
        layer = int(info["layer"])
        mask[layers < layer] = 1
        boundary = np.flatnonzero(layers == layer)
        if name == "include_all_tied":
            mask[boundary] = 1
        elif name == "exclude_tied":
            pass
        else:
            order = _boundary_order(boundary, key, tiebreak_values, n)
            mask[order[: int(info["take"])]] = 1
    record = {
        "value": None if cap is None else int(cap),
        "policy": name,
        "tiebreak_key": key,
        "boundary_rows": int(info["boundary_rows"]),
        "selected_count": int(mask.sum()),
        "selection_sha256": selection_sha256(mask),
        "permutation_invariant": permutation_invariant(name),
    }
    return mask, record


def load_adjusted_csv(path: Path, columns: list[dict]) -> np.ndarray:
    """Read named columns and apply lower/higher so the kernel sees lower-is-better."""
    import csv

    with Path(path).open(newline="") as f:
        rows = list(csv.DictReader(f))
    if len(columns) < 2:
        raise ValueError("need at least two KPI columns")
    stacked = []
    for spec in columns:
        name = spec["name"]
        sense = spec["sense"]
        if sense not in ("lower", "higher"):
            raise ValueError(f"sense {sense!r}")
        vals = np.empty(len(rows), dtype=np.float64)
        for i, row in enumerate(rows):
            vals[i] = float(row[name])
        if not np.isfinite(vals).all():
            raise ValueError(f"non-finite values in {name}")
        if sense == "higher":
            vals = -vals
        stacked.append(vals)
    return np.column_stack(stacked)


def load_tiebreak_column(path: Path, tiebreak_key: str) -> np.ndarray | None:
    if tiebreak_key in ("none", "input_index"):
        return None
    import csv

    with Path(path).open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or tiebreak_key not in rows[0]:
        raise ValueError(f"tiebreak column {tiebreak_key!r} is not in the CSV")
    vals = np.array([float(r[tiebreak_key]) for r in rows], dtype=np.float64)
    if not np.isfinite(vals).all():
        raise ValueError("tiebreak values must be finite")
    return vals


def build_kpi_receipt(
    path,
    *,
    adjusted: np.ndarray,
    columns: list[dict],
    pair_sieve_version: str,
    cap: int | None,
    policy: str | None = None,
    tiebreak_key: str | None = None,
    tiebreak_values=None,
    input_path=None,
):
    """Rank, apply the cap policy, and write a schema-v2 receipt via receipt.py."""
    from receipt import build_receipt_v2, write_receipt

    data = np.ascontiguousarray(adjusted, dtype=np.float64)
    if data.ndim != 2 or data.shape[1] != len(columns):
        raise ValueError("columns and adjusted matrix disagree")
    ranks = rank_layers(data)
    _mask, cap_record = apply_cap(ranks, cap, policy, tiebreak_key, tiebreak_values)
    receipt = build_receipt_v2(
        input_path=Path(input_path) if input_path else None,
        columns=columns,
        ranks=ranks,
        adjusted=data,
        pair_sieve_version=pair_sieve_version,
        cap_record=cap_record,
    )
    write_receipt(Path(path), receipt)
    return receipt
