#!/usr/bin/env python3
"""
PrymGyroSort — Sub-Linear Performance Scaling Measurement Campaign

Isolated evaluation harness. Does not modify the ranking kernel or public API.
Honesty: measurement only. o(N) auxiliary ranking is NOT claimed.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LADDER = [65536, 262144, 1048576]


def _ensure_executable(src: Path) -> Optional[Path]:
    """Stage binary to /tmp (artifacts FS may strip execute bits)."""
    if not src.is_file():
        return None
    dst = Path("/tmp") / f"prym_gyro_rank_driver_{os.getpid()}"
    shutil.copy2(src, dst)
    dst.chmod(0o755)
    return dst


def find_rank_driver(work: Path) -> Optional[Path]:
    candidates = [
        work / "rank_driver",
        ROOT / "work" / "rank_driver",
        ROOT / "rank_driver",
        Path("./rank_driver"),
        Path("/tmp/rank_driver"),
    ]
    for c in candidates:
        if c.is_file():
            exe = _ensure_executable(c)
            if exe is not None:
                return exe
    return None


def build_rank_driver(work: Path) -> Optional[Path]:
    work.mkdir(parents=True, exist_ok=True)
    out = work / "rank_driver"
    src = ROOT / "cpp" / "rank_driver.cpp"
    inc = ROOT / "cpp" / "include"
    if not src.exists():
        print(f"[campaign] missing {src}", file=sys.stderr)
        return None
    cmd = ["g++", "-O3", "-std=c++17", f"-I{inc}", str(src), "-o", str(out)]
    print(f"[campaign] building: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        return None
    if out.is_file():
        return _ensure_executable(out)
    return None


def generate_matrix(n: int, seed: int, n_good: int, out_dir: Path) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    wire = ROOT / "python" / "live_path_wire.py"
    gen = ROOT / "python" / "generate_geometric_matrix.py"
    if wire.exists():
        cmd = [sys.executable, str(wire), "--mode", "synthetic", "--n", str(n),
               "--seed", str(seed), "--n-good", str(n_good), "--out-dir", str(out_dir)]
    elif gen.exists():
        cmd = [sys.executable, str(gen), "--n", str(n), "--seed", str(seed),
               "--n-good", str(n_good), "--out-dir", str(out_dir)]
    else:
        print("[campaign] no matrix generator found", file=sys.stderr)
        return False
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        return False
    return (out_dir / "matrix.bin").exists()


def run_rank(driver: Path, out_dir: Path, n: int, m: int, memory_pressure: int) -> Dict[str, Any]:
    cmd = [str(driver), str(out_dir / "matrix.bin"), str(n), str(m), str(out_dir), str(memory_pressure)]
    t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True)
    wall_s = time.perf_counter() - t0
    report: Dict[str, Any] = {}
    rp = out_dir / "rank_report.json"
    if rp.exists():
        try:
            report = json.loads(rp.read_text())
        except Exception:
            pass
    return {"returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr,
            "host_wall_ms": wall_s * 1000.0, "report": report}


def run_self_check(out_dir: Path, top_frac: float = 0.05) -> Dict[str, Any]:
    script = ROOT / "python" / "self_check.py"
    cmd = [sys.executable, str(script), "--dir", str(out_dir),
           "--top-frac", str(top_frac), "--min-good-recall", "0.0", "--max-time-ms", "0"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    sc: Dict[str, Any] = {}
    path = out_dir / "self_check.json"
    if path.exists():
        try:
            sc = json.loads(path.read_text())
        except Exception:
            pass
    if not sc and r.stdout:
        try:
            sc = json.loads(r.stdout)
        except Exception:
            pass
    sc["_self_check_returncode"] = r.returncode
    return sc


def estimate_aux_bytes(n: int, memory_pressure: bool) -> int:
    if memory_pressure:
        return int(n * 4 * 4 + 64 * 1024)
    return int(n * 8 * 8 + 256 * 1024)


def run_ladder(ladder, seed, n_good_ratio, memory_pressure, work_root, top_frac, build):
    work_root.mkdir(parents=True, exist_ok=True)
    driver = find_rank_driver(work_root)
    if driver is None and build:
        driver = build_rank_driver(work_root)
    if driver is None:
        print("[campaign] rank_driver not found/built", file=sys.stderr)

    rows = []
    for n in ladder:
        n_good = min(max(8, int(n * n_good_ratio)), 256)
        out_dir = work_root / f"scale_N{n}"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"[campaign] N={n} generating ensemble (n_good={n_good}) …", flush=True)
        if not generate_matrix(n, seed, n_good, out_dir):
            rows.append({"n": n, "error": "matrix_generation_failed"})
            continue

        row = {
            "n": n, "n_good": n_good,
            "memory_pressure": bool(memory_pressure),
            "space_mode": "LowAux2D" if memory_pressure else "FenwickMax",
            "aux_bytes_est": estimate_aux_bytes(n, bool(memory_pressure)),
        }
        if driver is None:
            row["error"] = "rank_driver_missing"
            rows.append(row)
            continue

        print(f"[campaign] N={n} ranking (memory_pressure={memory_pressure}) …", flush=True)
        rank_info = run_rank(driver, out_dir, n, 2, memory_pressure)
        report = rank_info.get("report") or {}
        row["time_ms"] = report.get("time_ms", rank_info.get("host_wall_ms"))
        row["host_wall_ms"] = rank_info.get("host_wall_ms")
        row["rank_returncode"] = rank_info.get("returncode")
        row["strategy"] = report.get("strategy") or row["space_mode"]

        if rank_info.get("returncode") != 0:
            row["error"] = "rank_failed"
            row["stderr"] = (rank_info.get("stderr") or "")[:500]
            rows.append(row)
            continue

        print(f"[campaign] N={n} self_check …", flush=True)
        sc = run_self_check(out_dir, top_frac=top_frac)
        row["recall"] = sc.get("recall")
        row["mean_rank_good"] = sc.get("mean_rank_good")
        row["mean_rank_rest"] = sc.get("mean_rank_rest")
        if sc.get("mean_rank_good") is not None and sc.get("mean_rank_rest") is not None:
            row["separation_gap"] = float(sc["mean_rank_rest"]) - float(sc["mean_rank_good"])
        else:
            row["separation_gap"] = None
        row["self_check_ok"] = sc.get("ok")
        row["max_rank"] = sc.get("max_rank")
        rows.append(row)
        print(f"[campaign] N={n} done  time_ms={row.get('time_ms')}  recall={row.get('recall')}  gap={row.get('separation_gap')}", flush=True)
    return rows


def format_table(rows):
    lines = [
        "| Scale (N) | Space Mode | Wall Time (ms) | Aux Bytes (est) | Top-frac Recall | Separation Gap |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for r in rows:
        if r.get("error") and r.get("time_ms") is None:
            lines.append(f"| {r.get('n')} | {r.get('space_mode', '—')} | — | {r.get('aux_bytes_est', '—')} | — | error: {r.get('error')} |")
            continue
        t = r.get("time_ms")
        t_s = f"{float(t):.2f}" if t is not None else "—"
        rec = r.get("recall")
        rec_s = f"{float(rec):.3f}" if rec is not None else "—"
        gap = r.get("separation_gap")
        gap_s = f"+{float(gap):.1f}" if gap is not None else "—"
        lines.append(f"| {r.get('n')} | {r.get('space_mode', '—')} | {t_s} | {r.get('aux_bytes_est', '—')} | {rec_s} | {gap_s} |")
    return "\n".join(lines)


def write_results_md(rows, path: Path, args):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    body = [
        "# Scaling Campaign Results", "",
        f"**Timestamp:** {ts}  ",
        f"**Ladder:** {args.ladder}  ",
        f"**memory_pressure:** {args.memory_pressure}  ",
        f"**seed:** {args.seed}  ", "",
        "## Table", "", format_table(rows), "",
        "## Notes", "",
        "- Measurement campaign only. Asymptotic o(N) auxiliary ranking is **not claimed**.",
        "- Aux bytes are engineering estimates for the LowAux2D / Fenwick working set, not heap-profiler ground truth.",
        "- Path-local engineered ensemble; no global Lyapunov language.",
        "- See `docs/SCALING_HARNESS.md` and root `NON_CLAIMS.md`.", "",
        "## Raw JSON", "", "```json", json.dumps(rows, indent=2), "```", "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body))
    print(f"[campaign] wrote {path}")


def main() -> int:
    p = argparse.ArgumentParser(description="PrymGyroSort sub-linear scaling measurement campaign")
    p.add_argument("--ladder", default=",".join(str(x) for x in DEFAULT_LADDER))
    p.add_argument("--seed", type=int, default=728)
    p.add_argument("--n-good-ratio", type=float, default=0.012)
    p.add_argument("--memory-pressure", type=int, default=1, choices=[0, 1])
    p.add_argument("--work-root", default=str(ROOT / "work"))
    p.add_argument("--top-frac", type=float, default=0.05)
    p.add_argument("--no-build", action="store_true")
    p.add_argument("--results", default=str(ROOT / "docs" / "SCALING_RESULTS.md"))
    args = p.parse_args()
    ladder = [int(x.strip()) for x in args.ladder.split(",") if x.strip()]
    if not ladder:
        print("[campaign] empty ladder", file=sys.stderr)
        return 2

    print("[*] Initiating Sub-Linear Performance Scaling Measurement Campaign…")
    print(f"    ladder={ladder}  memory_pressure={args.memory_pressure}  seed={args.seed}")
    rows = run_ladder(ladder, args.seed, args.n_good_ratio, args.memory_pressure,
                      Path(args.work_root), args.top_frac, build=not args.no_build)
    print()
    print(format_table(rows))
    print()
    write_results_md(rows, Path(args.results), args)
    json_path = Path(args.results).with_suffix(".json")
    json_path.write_text(json.dumps(rows, indent=2))
    print(f"[campaign] wrote {json_path}")
    print("[+] Campaign complete. No o(N) claim asserted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
