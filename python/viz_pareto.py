#!/usr/bin/env python3
"""
PrymGyroSort — Isolated Visualization Profile (Path A)

Read-only sidecar. Consumes work/ artifacts:
  matrix.bin, ranks.bin, is_good.npy

Outputs:
  - ASCII Pareto scatter (pareto_ascii.txt)
  - Light HTML + inline SVG (pareto.html) — zero external deps

Never touches the C++ core, Dockerfile builder stage, or ranking kernel.
Requires only numpy (already present for self_check).

Usage:
  python3 python/viz_pareto.py --dir work
  python3 python/viz_pareto.py --dir work --format both --width 72 --height 24
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np


def load_work(d: Path) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray], dict]:
    matrix = np.fromfile(d / "matrix.bin", dtype=np.float64)
    if matrix.size % 2 != 0:
        raise SystemExit(f"[viz] matrix.bin size {matrix.size} not divisible by 2")
    matrix = matrix.reshape(-1, 2)
    n = matrix.shape[0]

    ranks_path = d / "ranks.bin"
    if not ranks_path.exists():
        raise SystemExit("[viz] ranks.bin missing — run rank_driver first")
    ranks = np.fromfile(ranks_path, dtype=np.int32)
    if ranks.size != n:
        raise SystemExit(f"[viz] ranks length {ranks.size} != matrix N {n}")

    is_good = None
    if (d / "is_good.npy").exists():
        is_good = np.load(d / "is_good.npy")
        if is_good.size != n:
            is_good = None

    meta = {}
    for name in ("meta.json", "rank_report.json", "self_check.json"):
        p = d / name
        if p.exists():
            try:
                meta[name] = json.loads(p.read_text())
            except Exception:
                pass
    return matrix, ranks, is_good, meta


def _norm(x: np.ndarray) -> np.ndarray:
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-15:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def render_ascii(
    matrix: np.ndarray,
    ranks: np.ndarray,
    is_good: Optional[np.ndarray],
    width: int = 72,
    height: int = 22,
    max_rank_show: int = 8,
) -> str:
    n = matrix.shape[0]
    xs = _norm(matrix[:, 0])
    ys = _norm(matrix[:, 1])
    grid = [[" " for _ in range(width)] for _ in range(height)]
    order = np.argsort(-ranks)
    for idx in order:
        c = int(xs[idx] * (width - 1))
        r = int(ys[idx] * (height - 1))
        r = max(0, min(height - 1, r))
        c = max(0, min(width - 1, c))
        rk = int(ranks[idx])
        good = bool(is_good[idx]) if is_good is not None else False
        if rk == 1:
            ch = "@" if good else "#"
        elif rk <= max_rank_show:
            ch = "o" if good else "."
        else:
            ch = "·" if not good else "+"
        grid[r][c] = ch

    lines: List[str] = []
    lines.append("Pareto scatter  (obj0 → right, obj1 → down; top-left = best)")
    lines.append("  legend: #/@ = rank-1 front (@=good anchor)  o/.= mid  ·/+= rest")
    lines.append("┌" + "─" * width + "┐")
    for row in grid:
        lines.append("│" + "".join(row) + "│")
    lines.append("└" + "─" * width + "┘")

    front = int((ranks == 1).sum())
    n_good = int(is_good.sum()) if is_good is not None else 0
    good_front = int(((ranks == 1) & is_good).sum()) if is_good is not None else 0
    lines.append(
        f"  N={n}  rank-1 front={front}  good={n_good}  good_on_front={good_front}  "
        f"max_rank={int(ranks.max())}"
    )
    lines.append(
        f"  obj0 range [{matrix[:,0].min():.4g}, {matrix[:,0].max():.4g}]  "
        f"obj1 range [{matrix[:,1].min():.4g}, {matrix[:,1].max():.4g}]"
    )
    return "\n".join(lines)


def render_html(
    matrix: np.ndarray,
    ranks: np.ndarray,
    is_good: Optional[np.ndarray],
    svg_w: int = 720,
    svg_h: int = 480,
    title: str = "PrymGyroSort Pareto front",
) -> str:
    n = matrix.shape[0]
    pad = 48
    plot_w = svg_w - 2 * pad
    plot_h = svg_h - 2 * pad
    x, y = matrix[:, 0], matrix[:, 1]
    x_lo, x_hi = float(x.min()), float(x.max())
    y_lo, y_hi = float(y.min()), float(y.max())
    if x_hi - x_lo < 1e-15:
        x_hi = x_lo + 1.0
    if y_hi - y_lo < 1e-15:
        y_hi = y_lo + 1.0

    def sx(v: float) -> float:
        return pad + (v - x_lo) / (x_hi - x_lo) * plot_w

    def sy(v: float) -> float:
        return pad + (v - y_lo) / (y_hi - y_lo) * plot_h

    order = np.argsort(-ranks)
    circles = []
    for idx in order:
        rk = int(ranks[idx])
        good = bool(is_good[idx]) if is_good is not None else False
        cx, cy = sx(float(x[idx])), sy(float(y[idx]))
        if rk == 1:
            r, fill, stroke = 5.5, ("#e63946" if good else "#1d3557"), "#000"
            opacity = 0.95
        elif rk <= 5:
            r, fill, stroke = 3.5, ("#f4a261" if good else "#457b9d"), "#333"
            opacity = 0.75
        else:
            r, fill, stroke = 2.0, ("#a8dadc" if good else "#c0c0c0"), "none"
            opacity = 0.45
        circles.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="0.6" opacity="{opacity}"/>'
        )

    front = int((ranks == 1).sum())
    n_good = int(is_good.sum()) if is_good is not None else 0
    good_front = int(((ranks == 1) & is_good).sum()) if is_good is not None else 0

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{title}</title>
<style>
  body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 1.5rem; background: #f8f9fa; color: #212529; }}
  h1 {{ font-size: 1.15rem; margin: 0 0 0.5rem; }}
  .meta {{ font-size: 0.85rem; color: #495057; margin-bottom: 1rem; }}
  .wrap {{ background: #fff; border: 1px solid #dee2e6; border-radius: 8px; padding: 0.75rem; display: inline-block; }}
  .legend {{ font-size: 0.8rem; margin-top: 0.75rem; color: #495057; }}
  .note {{ font-size: 0.75rem; color: #868e96; margin-top: 1rem; max-width: 40rem; }}
</style>
</head>
<body>
  <h1>{title}</h1>
  <div class="meta">
    N={n} &nbsp;|&nbsp; rank-1 front={front} &nbsp;|&nbsp; good anchors={n_good}
    &nbsp;|&nbsp; good on front={good_front} &nbsp;|&nbsp; max_rank={int(ranks.max())}
  </div>
  <div class="wrap">
    <svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">
      <rect x="0" y="0" width="{svg_w}" height="{svg_h}" fill="#ffffff"/>
      <rect x="{pad}" y="{pad}" width="{plot_w}" height="{plot_h}" fill="#f1f3f5" stroke="#adb5bd"/>
      <text x="{pad + plot_w/2}" y="{svg_h - 12}" text-anchor="middle" font-size="12" fill="#495057">obj0  (lower → better, left)</text>
      <text x="14" y="{pad + plot_h/2}" text-anchor="middle" font-size="12" fill="#495057"
            transform="rotate(-90 14 {pad + plot_h/2})">obj1  (lower → better, top)</text>
      <text x="{pad}" y="{pad - 8}" font-size="10" fill="#868e96">({x_lo:.3g}, {y_lo:.3g})</text>
      <text x="{pad + plot_w}" y="{pad - 8}" text-anchor="end" font-size="10" fill="#868e96">obj0 max {x_hi:.3g}</text>
      {''.join(circles)}
    </svg>
  </div>
  <div class="legend">
    <span style="color:#1d3557">●</span> rank-1 front &nbsp;
    <span style="color:#e63946">●</span> good anchor on front &nbsp;
    <span style="color:#457b9d">●</span> mid ranks &nbsp;
    <span style="color:#c0c0c0">●</span> rest
  </div>
  <p class="note">
    Path-local geometric ranking only. Does not claim global Lyapunov exponents or ownership of 8/5.
    Isolated Visualization Profile (Path A) — read-only sidecar; core compilation runtime untouched.
  </p>
</body>
</html>
"""


def main() -> int:
    p = argparse.ArgumentParser(description="PrymGyroSort isolated Pareto visualization (Path A)")
    p.add_argument("--dir", default=".", help="work directory with matrix.bin + ranks.bin")
    p.add_argument("--format", choices=["ascii", "html", "both"], default="both")
    p.add_argument("--width", type=int, default=72)
    p.add_argument("--height", type=int, default=22)
    p.add_argument("--svg-width", type=int, default=720)
    p.add_argument("--svg-height", type=int, default=480)
    p.add_argument("--out-prefix", default="pareto")
    args = p.parse_args()

    d = Path(args.dir)
    matrix, ranks, is_good, meta = load_work(d)

    if args.format in ("ascii", "both"):
        text = render_ascii(matrix, ranks, is_good, width=args.width, height=args.height)
        print(text)
        out_txt = d / f"{args.out_prefix}_ascii.txt"
        out_txt.write_text(text + "\n")
        print(f"[viz] wrote {out_txt}", file=sys.stderr)

    if args.format in ("html", "both"):
        html = render_html(matrix, ranks, is_good, svg_w=args.svg_width, svg_h=args.svg_height)
        out_html = d / f"{args.out_prefix}.html"
        out_html.write_text(html)
        print(f"[viz] wrote {out_html}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
