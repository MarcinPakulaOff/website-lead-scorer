"""Fetch one homepage and collect facts about it. No scoring here, only observations."""

from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser

USER_AGENT = "Mozilla/5.0 (compatible; WebsiteLeadScorer/0.1)"
MAX_BYTES = 2_000_000


@dataclass
class Facts:
    url: str
    reachable: bool = False
    status: int | None = None
    final_url: str = ""
    https: bool = False
    ms: int | None = None
    kb: int | None = None
    viewport: bool = False
    title: str = ""
    description: bool = False
    newest_year: int | None = None
    error: str = ""
    extra: dict = field(default_factory=dict)


class _Head(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.viewport = False
        self.description = False
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            name = a.get("name", "").lower()
            if name == "viewport" and "width" in a.get("content", ""):
                self.viewport = True
            if name == "description" and a.get("content", "").strip():
                self.description = True
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


YEAR = re.compile(r"(?:©|&copy;|copyright)[^<]{0,40}?((?:19|20)\d{2})(?:\s*[-–]\s*((?:19|20)\d{2}))?", re.I)


def newest_copyright_year(html: str) -> int | None:
    """Newest year next to a copyright sign, e.g. '© 2016–2019' -> 2019."""
    years = [int(y) for m in YEAR.finditer(html) for y in m.groups() if y]
    return max(years) if years else None


def normalize(url: str) -> str:
    url = url.strip()
    if url and not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    return url


def parse_html(facts: Facts, html: str) -> Facts:
    head = _Head()
    try:
        head.feed(html)
    except Exception:  # broken HTML is a finding, not a crash
        pass
    facts.viewport, facts.description = head.viewport, head.description
    facts.title = " ".join(head.title.split())[:120]
    facts.newest_year = newest_copyright_year(html)
    return facts


def fetch(url: str, timeout: float = 10.0) -> Facts:
    facts = Facts(url=normalize(url))
    req = urllib.request.Request(facts.url, headers={"User-Agent": USER_AGENT})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(MAX_BYTES)
            facts.status, facts.final_url = resp.status, resp.geturl()
            charset = resp.headers.get_content_charset() or "utf-8"
    except urllib.error.HTTPError as exc:
        facts.status, facts.final_url, facts.error = exc.code, facts.url, f"HTTP {exc.code}"
        return facts
    except Exception as exc:  # DNS, TLS, timeout: the site is effectively down
        facts.error = type(exc).__name__
        return facts
    facts.ms = int((time.monotonic() - start) * 1000)
    facts.reachable = True
    facts.https = facts.final_url.lower().startswith("https://")
    facts.kb = len(body) // 1024
    try:
        text = body.decode(charset, errors="replace")
    except LookupError:  # unknown charset name in the header
        text = body.decode("utf-8", errors="replace")
    return parse_html(facts, text)
