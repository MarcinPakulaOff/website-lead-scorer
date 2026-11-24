# website-lead-scorer

Score a list of small businesses by **how much they need a new website**. Give it a CSV of firms (name, city, website), get back the same list sorted **best leads first**, each with plain reasons.

| Finding | Points |
|---|---|
| no website at all | 100 |
| website down (DNS, TLS, timeout, HTTP 4xx/5xx) | 80 |
| no HTTPS | 25 |
| not mobile-friendly (no `viewport` meta) | 25 |
| slow (> 3 s) | 15 |
| outdated (copyright year 3+ years old) | 15 |
| no meta description / no title | 5 each |

The rules live in one dictionary in `score.py`, and scoring is a pure function, so changing a weight is one line and is covered by tests.

- Fetching (`audit.py`) only observes facts; scoring (`score.py`) only judges them.
- Pages are fetched in a small thread pool, with a timeout and a 2 MB read limit.
- It reads the public homepage only, as a browser would. It does not scrape registers or collect personal data: the input list is yours.

## Usage

```bash
pip install -e .
lead-score examples/firms.csv --out leads.csv --min-score 30
```

```csv
name,city,website,score,reasons,https,load_ms
Sample Bakery,Kluczbork,,100,brak strony,,
Example Garage,Brzeg,example.com,30,brak HTTPS; brak opisu dla Google,False,122
```

(Reasons are in Polish because the tool is used for Polish small businesses.)

## Tests

`pytest -q`. The tests start a local HTTP server, so no network is needed. CI: Python 3.10 and 3.12.

## License

MIT
