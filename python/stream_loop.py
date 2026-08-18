#!/usr/bin/env python3
"""PrymGyroSort Phase-4 streaming scaffold — circular window + zero-copy rank. Sieve only."""
from __future__ import annotations
import argparse, asyncio, sys, time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Iterable, Optional
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))
from prym_gyro import rank  # noqa: E402

@dataclass
class StreamConfig:
    window: int = 4096
    top_frac: float = 0.05
    interval_ms: float = 100.0
    memory_pressure: Optional[bool] = None
    seed: int = 42

@dataclass
class StreamState:
    buf: Deque[np.ndarray] = field(default_factory=deque)
    ticks: int = 0
    last_ranks: Optional[np.ndarray] = None

def map_row_batch(rows: np.ndarray) -> np.ndarray:
    dislocation, obi, bid_ask, depth, mdd = rows[:,0], rows[:,1], rows[:,2], rows[:,3], rows[:,4]
    def _n(x):
        lo, hi = float(x.min()), float(x.max())
        return np.zeros_like(x) if hi - lo < 1e-15 else (x - lo) / (hi - lo)
    opp_dis = _n(1.0 / (dislocation + 1e-5))
    opp_obi = _n((1.0 - np.clip(obi, -1.0, 1.0)) * 0.5)
    liq = _n(bid_ask / (depth + 1e-5))
    risk_mdd = _n(np.maximum(mdd, 0.0))
    return np.column_stack([0.6*opp_dis+0.4*opp_obi, 0.6*liq+0.4*risk_mdd]).astype(np.float64)

def synthetic_row(rng):
    return np.array([float(rng.exponential(0.35)), float(rng.uniform(-1,1)),
                     float(rng.uniform(0.01,0.30)), float(rng.uniform(800,40000)),
                     float(rng.uniform(0,0.08))], dtype=np.float64)

class RankStream:
    def __init__(self, cfg: StreamConfig):
        self.cfg = cfg
        self.state = StreamState(buf=deque(maxlen=cfg.window))
        self.rng = np.random.default_rng(cfg.seed)

    def push_row(self, row):
        self.state.buf.append(np.asarray(row, dtype=np.float64).reshape(5))

    def push_rows(self, rows: Iterable):
        for r in rows: self.push_row(r)

    def rank_window(self) -> dict:
        n = len(self.state.buf)
        if n == 0: return {"n": 0, "front_idx": [], "elapsed_ms": 0.0}
        X = np.ascontiguousarray(map_row_batch(np.stack(list(self.state.buf))))
        t0 = time.perf_counter()
        ranks = rank(X, memory_pressure=self.cfg.memory_pressure)
        elapsed = (time.perf_counter() - t0) * 1e3
        k = max(1, int(self.cfg.top_frac * n))
        front = np.argsort(ranks, kind="stable")[:k]
        self.state.last_ranks = ranks
        self.state.ticks += 1
        return {"n": n, "ticks": self.state.ticks, "elapsed_ms": elapsed,
                "front_idx": front.tolist(), "front_ranks": ranks[front].tolist(),
                "scope": "execution sieve only; promote_ready=false"}

    async def run_synthetic(self, duration_s=2.0, rows_per_tick=32):
        interval = self.cfg.interval_ms / 1000.0
        end = time.perf_counter() + duration_s
        print(f"[stream] synthetic window={self.cfg.window} interval={self.cfg.interval_ms}ms")
        while time.perf_counter() < end:
            for _ in range(rows_per_tick):
                self.push_row(synthetic_row(self.rng))
            r = self.rank_window()
            print(f"[stream] tick={r['ticks']} n={r['n']} rank_ms={r['elapsed_ms']:.3f} front={r['front_idx'][:5]}...")
            await asyncio.sleep(interval)
        print("[stream] done — sieve only, no alpha claim")

async def amain(args):
    cfg = StreamConfig(window=args.window, top_frac=args.top_frac,
                       interval_ms=args.interval_ms, seed=args.seed)
    stream = RankStream(cfg)
    await stream.run_synthetic(duration_s=args.duration, rows_per_tick=args.rows_per_tick)
    return 0

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--window", type=int, default=4096)
    p.add_argument("--top-frac", type=float, default=0.05)
    p.add_argument("--interval-ms", type=float, default=100.0)
    p.add_argument("--duration", type=float, default=2.0)
    p.add_argument("--rows-per-tick", type=int, default=32)
    p.add_argument("--seed", type=int, default=42)
    return asyncio.run(amain(p.parse_args()))

if __name__ == "__main__":
    raise SystemExit(main())
