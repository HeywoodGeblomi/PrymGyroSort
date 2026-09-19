#!/usr/bin/env python3
"""Check checked-in golden seals. Exit 0 / 1 only. No --chi."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = ROOT / "artifacts" / "golden"
BOOK = GOLDEN_ROOT / "book"
SUMS = GOLDEN_ROOT / "SHA256SUMS"
BOOK_SUM = GOLDEN_ROOT / "book.sha256"


def fail(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 1


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_sums(sumfile: Path, base: Path) -> int:
    if not sumfile.is_file():
        return fail(f"missing {sumfile}")
    for ln in sumfile.read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split()
        if len(parts) < 2:
            return fail(f"malformed sums line: {ln!r}")
        want, name = parts[0], parts[-1]
        target = Path(name)
        if not target.is_file():
            target = base / name
        if not target.is_file():
            target = ROOT / name
        if not target.is_file():
            return fail(f"missing listed file: {name}")
        got = sha256_file(target)
        if got != want:
            return fail(f"hash mismatch: {name}")
    return 0


def main() -> int:
    sys.path.insert(0, str(ROOT / "python"))
    from verify_bundle import verify

    if not BOOK.is_dir():
        return fail("missing artifacts/golden/book")
    rc = verify(BOOK, rerun=True)
    if rc != 0:
        return rc
    if BOOK_SUM.is_file():
        rc = check_sums(BOOK_SUM, ROOT)
        if rc != 0:
            return rc
    if SUMS.is_file():
        rc = check_sums(SUMS, GOLDEN_ROOT)
        if rc != 0:
            return rc
    print("golden ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
