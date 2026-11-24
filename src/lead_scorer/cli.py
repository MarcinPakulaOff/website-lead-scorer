"""lead-score firms.csv --out leads.csv

Input CSV columns: name, city, website (website may be empty).
Output: the same rows plus score and reasons, best leads first.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from concurrent.futures import ThreadPoolExecutor

from .audit import fetch
from .score import score


def read_rows(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    missing = {"name", "website"} - set(rows[0] if rows else {})
    if missing:
        raise SystemExit(f"missing columns: {', '.join(sorted(missing))}")
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="lead-score")
    ap.add_argument("input")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--min-score", type=int, default=0)
    args = ap.parse_args(argv)

    rows = read_rows(args.input)
    sites = [r.get("website", "").strip() for r in rows]
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        facts = list(pool.map(lambda u: fetch(u) if u else None, sites))

    year = dt.date.today().year
    out = []
    for row, f in zip(rows, facts):
        s = score(f, this_year=year)
        if s.score < args.min_score:
            continue
        out.append({**row, "score": s.score, "reasons": "; ".join(s.reasons),
                    "https": "" if f is None else f.https, "load_ms": "" if f is None else f.ms})
    out.sort(key=lambda r: -r["score"])

    fields = list(rows[0].keys()) + ["score", "reasons", "https", "load_ms"] if rows else ["score"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} leads -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
