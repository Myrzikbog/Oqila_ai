#!/usr/bin/env python3
"""Lists the legal facts that have not been re-checked for N days (default 90): the manual re-check list.

Open each source_url, compare with the fact in services/legal_kb.json and update `verified_at` (and the value if it
changed). Unverified facts are listed too, as they always need a manual check.

Usage:  python scripts/legal_kb_stale.py [--days 90]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.legal_kb import kb  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args()
    stale = kb.stale(args.days)
    unverified = [f for f in kb.facts.values() if f["status"] == "unverified"]
    if not stale and not unverified:
        print(f"All {len(kb.facts)} facts were checked within {args.days} days.")
        return 0
    for item in stale:
        print(f"STALE {item['age_days']:>4} days  {item['id']:<28} {item['status']:<10} {item['source_url']}")
    for fact in unverified:
        print(f"UNVERIFIED       {fact['id']:<28} {fact['source_url']}")
    print(f"\n{len(stale)} stale, {len(unverified)} unverified of {len(kb.facts)} facts.")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
