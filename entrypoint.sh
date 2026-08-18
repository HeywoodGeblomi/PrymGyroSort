#!/bin/bash
set -euo pipefail

N="${N:-4096}"
SEED="${SEED:-728}"
MODE="${MODE:-synthetic}"
MEMORY_PRESSURE="${MEMORY_PRESSURE:-0}"
WORKDIR="${WORKDIR:-/work}"

mkdir -p "$WORKDIR"
cd "$WORKDIR"

PY=/opt/prym-gyro/python

echo "[PrymGyroSort] v0.1.3  mode=${MODE}  N=${N}  seed=${SEED}"

if [ "$MODE" = "finance" ]; then
  echo "[PrymGyroSort] Finance protocol adapter…"
  python3 "$PY/protocol_finance.py" --out-dir "$WORKDIR" --n "$N" --seed "$SEED"
else
  echo "[PrymGyroSort] Geometric / synthetic matrix…"
  if [ -f "$PY/live_path_wire.py" ]; then
    python3 "$PY/live_path_wire.py" --mode synthetic --n "$N" --seed "$SEED" --out-dir "$WORKDIR"
  else
    python3 "$PY/generate_geometric_matrix.py" --n "$N" --seed "$SEED" --out-dir "$WORKDIR"
  fi
fi

echo "[PrymGyroSort] Ranking (GyroRank)…"
/usr/local/bin/rank_driver "$WORKDIR/matrix.bin" "$N" 2 "$WORKDIR" "$MEMORY_PRESSURE"

echo "[PrymGyroSort] Self-check…"
python3 "$PY/self_check.py" --dir "$WORKDIR" --max-time-ms 0 || true

if [ -f "$WORKDIR/rank_report.json" ]; then
  echo "---- rank_report ----"
  cat "$WORKDIR/rank_report.json"
fi
if [ -f "$WORKDIR/self_check.json" ]; then
  echo "---- self_check ----"
  cat "$WORKDIR/self_check.json"
fi

echo ""
echo "See /opt/prym-gyro/NON_CLAIMS.md — path-local / engineered class only. EXTERNAL-clean."
echo "[PrymGyroSort] done."
