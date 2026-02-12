#!/usr/bin/env python3
"""Create local fixture directory scaffold (raw folder only)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "tests" / "fixtures" / "raw"


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    print(f"[ok] created: {RAW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
