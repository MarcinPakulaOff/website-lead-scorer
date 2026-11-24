"""Turn facts into a score. Pure functions, so the rules are easy to read and test.

Higher score = the business needs a new website more = a better lead.
"""

from __future__ import annotations

from dataclasses import dataclass

from .audit import Facts

RULES = {
    "no_site": (100, "brak strony"),
    "down": (80, "strona nie działa"),
    "no_https": (25, "brak HTTPS"),
    "no_viewport": (25, "brak wersji mobilnej"),
    "slow": (15, "wolne ładowanie"),
    "outdated": (15, "stary rok w stopce"),
    "no_description": (5, "brak opisu dla Google"),
    "no_title": (5, "brak tytułu strony"),
}


@dataclass(frozen=True)
class Scored:
    score: int
    reasons: tuple[str, ...]


def score(facts: Facts | None, *, this_year: int, slow_ms: int = 3000, outdated_years: int = 3) -> Scored:
    if facts is None:
        hits = ["no_site"]
    elif not facts.reachable or (facts.status or 0) >= 400:
        hits = ["down"]
    else:
        hits = []
        if not facts.https:
            hits.append("no_https")
        if not facts.viewport:
            hits.append("no_viewport")
        if facts.ms is not None and facts.ms > slow_ms:
            hits.append("slow")
        if facts.newest_year and this_year - facts.newest_year >= outdated_years:
            hits.append("outdated")
        if not facts.description:
            hits.append("no_description")
        if not facts.title:
            hits.append("no_title")
    return Scored(sum(RULES[h][0] for h in hits), tuple(RULES[h][1] for h in hits))
