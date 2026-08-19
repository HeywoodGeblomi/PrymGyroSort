#!/usr/bin/env python3
"""Independent layer-rank oracle vs native. See docs/RANK_VERIFICATION.md."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))
from prym_gyro import rank as native_rank

def weakly_dominates(a, b) -> bool:
    return (a[0] <= b[0] and a[1] <= b[1]) and (a[0] < b[0] or a[1] < b[1])

def layer_rank_bruteforce(X: np.ndarray) -> np.ndarray:
    n = X.shape[0]
    ranks = np.zeros(n, dtype=np.int32)
    remaining = set(range(n))
    layer = 1
    while remaining:
        rem = list(remaining)
        dominated = set()
        for i in rem:
            for j in rem:
                if i != j and weakly_dominates(X[j], X[i]):
                    dominated.add(i)
                    break
        front = [i for i in rem if i not in dominated] or rem
        for i in front:
            ranks[i] = layer
            remaining.discard(i)
        layer += 1
        if layer > n + 1:
            break
    return ranks

def nondominated_mask(X):
    n = X.shape[0]
    nd = np.ones(n, dtype=bool)
    for i in range(n):
        for j in range(n):
            if i != j and weakly_dominates(X[j], X[i]):
                nd[i] = False
                break
    return nd

def check_properties(X, ranks):
    fails = []
    if (ranks < 1).any():
        fails.append("P1")
    nd = nondominated_mask(X)
    for i in range(len(ranks)):
        if ranks[i] == 1 and not nd[i]:
            fails.append("P2"); break
    for i in range(len(ranks)):
        if nd[i] and ranks[i] != 1:
            fails.append("P3"); break
    for i in range(len(ranks)):
        for j in range(len(ranks)):
            if weakly_dominates(X[j], X[i]) and not (ranks[j] < ranks[i]):
                fails.append("P4"); return fails
    return fails

def suite(name, X):
    X = np.ascontiguousarray(X, dtype=np.float64)
    nat = native_rank(X)
    lay = layer_rank_bruteforce(X)
    return {
        "name": name,
        "n": X.shape[0],
        "match": bool(np.array_equal(nat, lay)),
        "agree": float((nat == lay).mean()),
        "props": check_properties(X, nat),
    }

def main():
    rng = np.random.default_rng(42)
    cases = [
        ("hand_chain", np.array([[0.,0.],[0.5,0.5],[1.,1.]])),
        ("random_50", rng.random((50, 2))),
        ("random_200", rng.random((200, 2))),
        ("all_identical", np.ones((30, 2))),
        ("antichain_ND", np.column_stack([np.linspace(0,1,40), np.linspace(1,0,40)])),
        ("total_chain", np.column_stack([np.linspace(0,1,40), np.linspace(0,1,40)])),
    ]
    X = rng.random((60, 2)); X[::3, 0] = X[0, 0]
    cases.append(("dup_x", X))
    front = np.column_stack([np.linspace(0,1,25), np.linspace(1,0,25)])
    cases.append(("front_plus_cloud", np.vstack([front, rng.random((75,2))+1.0])))
    ok = 0
    for name, X in cases:
        r = suite(name, X)
        status = "PASS" if r["match"] and not r["props"] else "FAIL"
        print(f"{r['name']:<20} n={r['n']:<4} match={r['match']} agree={r['agree']:.3f} props={r['props'] or 'PASS'} → {status}")
        ok += status == "PASS"
    print(f"{ok}/{len(cases)} PASS")
    return 0 if ok == len(cases) else 1

if __name__ == "__main__":
    raise SystemExit(main())
