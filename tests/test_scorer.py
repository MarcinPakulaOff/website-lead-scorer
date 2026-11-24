import csv
import http.server
import threading

import pytest

from lead_scorer.audit import Facts, fetch, newest_copyright_year, normalize, parse_html
from lead_scorer.cli import main
from lead_scorer.score import score

MODERN = b"""<html><head><title>Modern Shop</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="We sell bread."></head>
<body><footer>&copy; 2026 Modern Shop</footer></body></html>"""
OLD = b"""<html><head><title>Old</title></head><body>Copyright 2012-2018</body></html>"""


@pytest.fixture(scope="module")
def server():
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            pages = {"/modern": MODERN, "/old": OLD}
            if self.path not in pages:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(pages[self.path])

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_copyright_year_takes_newest():
    assert newest_copyright_year("© 2016–2019 Firma") == 2019
    assert newest_copyright_year("&copy; 2024") == 2024
    assert newest_copyright_year("no year here 2020") is None


def test_normalize_adds_scheme():
    assert normalize(" example.com ") == "http://example.com"
    assert normalize("https://x.pl") == "https://x.pl"


def test_parse_html_reads_head():
    f = parse_html(Facts(url="x"), MODERN.decode())
    assert f.viewport and f.description and f.title == "Modern Shop" and f.newest_year == 2026


def test_no_site_is_best_lead():
    s = score(None, this_year=2026)
    assert s.score == 100 and s.reasons == ("brak strony",)


def test_modern_https_site_scores_zero():
    f = parse_html(Facts(url="x", reachable=True, status=200, https=True, ms=300), MODERN.decode())
    assert score(f, this_year=2026).score == 0


def test_old_http_site_collects_reasons():
    f = parse_html(Facts(url="x", reachable=True, status=200, https=False, ms=5000), OLD.decode())
    s = score(f, this_year=2026)
    assert set(s.reasons) == {"brak HTTPS", "brak wersji mobilnej", "wolne ładowanie", "stary rok w stopce", "brak opisu dla Google"}


def test_fetch_real_pages(server):
    ok = fetch(server + "/modern")
    assert ok.reachable and ok.status == 200 and ok.viewport and not ok.https
    missing = fetch(server + "/nope")
    assert not missing.reachable and missing.status == 404
    assert score(missing, this_year=2026).reasons == ("strona nie działa",)
    down = fetch("http://127.0.0.1:9/")
    assert not down.reachable and down.error


def test_cli_sorts_best_leads_first(server, tmp_path):
    src = tmp_path / "firms.csv"
    src.write_text(f"name,city,website\nModern,Brzeg,{server}/modern\nOld,Olesno,{server}/old\nNone,Kluczbork,\n", encoding="utf-8")
    out = tmp_path / "leads.csv"
    assert main([str(src), "--out", str(out)]) == 0
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert [r["name"] for r in rows] == ["None", "Old", "Modern"]
    assert rows[0]["reasons"] == "brak strony"


def test_cli_min_score_filters(server, tmp_path):
    src = tmp_path / "firms.csv"
    src.write_text(f"name,city,website\nModern,Brzeg,{server}/modern\nNone,Kluczbork,\n", encoding="utf-8")
    out = tmp_path / "leads.csv"
    main([str(src), "--out", str(out), "--min-score", "30"])
    assert [r["name"] for r in csv.DictReader(out.open(encoding="utf-8"))] == ["None"]


def test_cli_requires_columns(tmp_path):
    src = tmp_path / "bad.csv"
    src.write_text("company\nX\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        main([str(src), "--out", str(tmp_path / "o.csv")])
