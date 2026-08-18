#!/bin/bash
set -euo pipefail
WORKDIR=${WORKDIR:-/tmp/prymgyro}
mkdir -p "$WORKDIR"
cd "$WORKDIR"

echo "[PrymGyroSort] Generating geometric matrix (Prym-anchored)..."
python3 /opt/prym-gyro/python/generate_geometric_matrix.py -n "${N:-4096}" --seed "${SEED:-728}" --n-good "${N_GOOD:-48}" --out-dir .

echo "[PrymGyroSort] Ranking with GyroRank kernel..."
/usr/local/bin/rank_driver matrix.bin ranks.bin

echo "[PrymGyroSort] Self-check..."
python3 /opt/prym-gyro/python/self_check.py --dir .
STATUS=$?

echo "---- self_check report ----"
cat self_check.json 2>/dev/null || true
echo "See NON_CLAIMS.md — path-local / engineered class only. EXTERNAL-clean."
exit $STATUS
