#!/usr/bin/env python3
"""
PrymGyroSort — WebSocket crypto sidecar (public feeds only)

Binance public bookTicker → RankStream feature rows → zero-copy rank.
No API keys. No order routing. Execution sieve only.

Usage:
  python3 python/ws_crypto_sidecar.py --duration 15 --interval-ms 200
  python3 python/ws_crypto_sidecar.py --synthetic --duration 5
  python3 python/ws_crypto_sidecar.py --duration 10 --fallback-synthetic
"""
from __future__ import annotations

import argparse, asyncio, json, sys, time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, List, Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "bindings"))

from stream_loop import RankStream, StreamConfig  # noqa: E402

BINANCE_WS = "wss://stream.binance.com:9443/stream"

@dataclass
class SymbolState:
    mids: Deque[float] = field(default_factory=lambda: deque(maxlen=64))
    peak: float = 0.0
    trough: float = 0.0
    mean: float = 0.0
    count: int = 0

def update_symbol(st: SymbolState, mid: float) -> None:
    st.mids.append(mid)
    st.count += 1
    st.mean = float(sum(st.mids) / len(st.mids))
    if st.count == 1:
        st.peak = st.trough = mid
    else:
        st.peak = max(st.peak, mid)
        st.trough = min(st.trough, mid)
    if st.count % 32 == 0:
        st.peak = 0.9 * st.peak + 0.1 * mid
        st.trough = 0.9 * st.trough + 0.1 * mid

def book_ticker_to_row(bid, ask, bid_qty, ask_qty, st: SymbolState) -> Optional[np.ndarray]:
    if bid <= 0 or ask <= 0 or ask < bid:
        return None
    mid = 0.5 * (bid + ask)
    update_symbol(st, mid)
    spread = ask - bid
    depth = max(bid_qty + ask_qty, 1e-12)
    obi = (bid_qty - ask_qty) / depth
    dislocation = abs(mid - st.mean)
    mdd = max(0.0, (st.peak - mid) / st.peak) if st.peak > 1e-12 else 0.0
    return np.array([dislocation, obi, spread, depth, mdd], dtype=np.float64)

class CryptoSidecar:
    def __init__(self, symbols: List[str], window=4096, interval_ms=200.0, top_frac=0.05):
        self.symbols = [s.lower().replace("-", "") for s in symbols]
        self.cfg = StreamConfig(window=window, interval_ms=interval_ms, top_frac=top_frac)
        self.stream = RankStream(self.cfg)
        self.states: Dict[str, SymbolState] = defaultdict(SymbolState)
        self.msg_count = 0
        self.row_count = 0

    def handle_book_ticker(self, symbol: str, payload: dict) -> None:
        try:
            bid, ask = float(payload["b"]), float(payload["a"])
            bid_qty, ask_qty = float(payload["B"]), float(payload["A"])
        except (KeyError, TypeError, ValueError):
            return
        row = book_ticker_to_row(bid, ask, bid_qty, ask_qty, self.states[symbol])
        if row is None:
            return
        self.stream.push_row(row)
        self.row_count += 1

    async def rank_ticker(self, stop_at: float) -> None:
        interval = self.cfg.interval_ms / 1000.0
        while time.perf_counter() < stop_at:
            if len(self.stream.state.buf) > 0:
                report = self.stream.rank_window()
                print(
                    f"[ws-sieve] tick={report['ticks']}  n={report['n']}  "
                    f"rank_ms={report['elapsed_ms']:.3f}  msgs={self.msg_count}  "
                    f"rows={self.row_count}  front={report['front_idx'][:5]}"
                )
            await asyncio.sleep(interval)

    async def run_binance(self, duration_s: float) -> None:
        try:
            import websockets
        except ImportError as e:
            raise SystemExit("pip install websockets") from e
        streams = "/".join(f"{s}@bookTicker" for s in self.symbols)
        url = f"{BINANCE_WS}?streams={streams}"
        stop_at = time.perf_counter() + duration_s
        print(f"[ws-sieve] connecting public Binance bookTicker  symbols={self.symbols}")
        print("[ws-sieve] honesty: execution sieve only — no orders, no keys, promote_ready=false")
        rank_task = asyncio.create_task(self.rank_ticker(stop_at))
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                while time.perf_counter() < stop_at:
                    raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    self.msg_count += 1
                    msg = json.loads(raw)
                    data = msg.get("data", msg)
                    sym = str(data.get("s", "")).lower()
                    if not sym:
                        stream = str(msg.get("stream", ""))
                        sym = stream.split("@")[0] if stream else ""
                    if sym:
                        self.handle_book_ticker(sym, data)
        finally:
            rank_task.cancel()
            try:
                await rank_task
            except asyncio.CancelledError:
                pass
        print(f"[ws-sieve] done  msgs={self.msg_count} rows={self.row_count} — sieve only")

    async def run_synthetic(self, duration_s: float) -> None:
        print("[ws-sieve] synthetic mode (no network)")
        stop_at = time.perf_counter() + duration_s
        rng = np.random.default_rng(7)
        rank_task = asyncio.create_task(self.rank_ticker(stop_at))
        try:
            while time.perf_counter() < stop_at:
                for s in self.symbols:
                    mid = 100 + float(rng.normal(0, 1))
                    spread = abs(float(rng.normal(0.05, 0.01)))
                    bid, ask = mid - 0.5 * spread, mid + 0.5 * spread
                    bq, aq = abs(float(rng.normal(10, 3))), abs(float(rng.normal(10, 3)))
                    self.handle_book_ticker(
                        s, {"b": str(bid), "a": str(ask), "B": str(bq), "A": str(aq), "s": s.upper()}
                    )
                    self.msg_count += 1
                await asyncio.sleep(0.01)
        finally:
            rank_task.cancel()
            try:
                await rank_task
            except asyncio.CancelledError:
                pass
        print(f"[ws-sieve] synthetic done  rows={self.row_count} ticks={self.stream.state.ticks}")

async def amain(args):
    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
    side = CryptoSidecar(symbols, window=args.window, interval_ms=args.interval_ms, top_frac=args.top_frac)
    if args.synthetic:
        await side.run_synthetic(args.duration)
    else:
        try:
            await side.run_binance(args.duration)
        except Exception as e:
            print(f"[ws-sieve] feed error: {type(e).__name__}: {e}", file=sys.stderr)
            if args.fallback_synthetic:
                print("[ws-sieve] falling back to synthetic", file=sys.stderr)
                await side.run_synthetic(min(args.duration, 5.0))
            else:
                return 1
    return 0

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", default="btcusdt,ethusdt,solusdt,bnbusdt")
    p.add_argument("--window", type=int, default=4096)
    p.add_argument("--interval-ms", type=float, default=200.0)
    p.add_argument("--top-frac", type=float, default=0.05)
    p.add_argument("--duration", type=float, default=15.0)
    p.add_argument("--synthetic", action="store_true")
    p.add_argument("--fallback-synthetic", action="store_true")
    return asyncio.run(amain(p.parse_args()))

if __name__ == "__main__":
    raise SystemExit(main())
