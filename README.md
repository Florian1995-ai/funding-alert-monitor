# Funding Alert Monitor

Find newly funded startups, verify the source article date, enrich founder and LinkedIn data, and export CSV/JSON/HTML reports.

This repo is designed for community use: bring your own API keys, run the monitor on a schedule, and generate reports from either live funding alerts or your own seed CSVs.

## What It Does

- Monitors funding announcements from RSS feeds and optional Tavily search.
- Verifies every source URL before accepting it into a report.
- Rejects old TechCrunch, Crunchbase, or press release pages when the article date is outside the target window.
- Flags placeholder/truncated URLs such as `...` or `[...]`.
- Validates founder and LinkedIn rows with basic identity signals instead of naive same-name searches.
- Exports:
  - `funded-startups-may-april-2026.csv`
  - `funded-startups-may-april-2026.json`
  - `founders-linkedin-may-april-2026.csv`
  - `needs-review-may-april-2026.csv`
  - `recently-funded-startups-may-april-2026.html`

See `examples/seed-funded-startups.csv` for a minimal input format and `examples/report/` for a sample generated community report.

## Install

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
pip install -r requirements.txt
```

On macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements.txt
```

## Configure

Copy `.env.example` to `.env` and add any keys you want to use.

```bash
cp .env.example .env
```

Required for RSS-only monitoring: none.

Optional integrations:

- `TAVILY_API_KEY` through `TAVILY_API_KEY_10` for search-based discovery with automatic rotation.
- `EXA_API_KEY` through `EXA_API_KEY_10` for external enrichment workflows with automatic rotation.
- `PERPLEXITY_API_KEY` for deeper research workflows.
- `APIFY_API_TOKEN` through `APIFY_API_TOKEN_10` for browser/crawler fallback when normal page fetches fail.

## Usage

Find candidate funding announcements:

```bash
funding-monitor monitor --days-back 2 --limit 50 --use-tavily --output .tmp/funding-candidates.json
```

Verify article dates and company identity:

```bash
funding-monitor verify \
  --input .tmp/funding-candidates.json \
  --start-date 2026-04-01 \
  --end-date 2026-05-31 \
  --fetch-articles \
  --output .tmp/funding-verified.json
```

Validate founder/LinkedIn rows:

```bash
funding-monitor enrich --input .tmp/funding-verified.json --output .tmp/funding-enriched.json
```

Create a report bundle:

```bash
funding-monitor report \
  --input .tmp/funding-enriched.json \
  --output-dir reports/may-april-2026 \
  --title "Recently Funded Startups - May 2026 and April 2026"
```

Run the seed-to-report pipeline in one command with your own CSV exports:

```bash
funding-monitor pipeline \
  --input examples/seed-funded-startups.csv \
  --output-dir reports/may-april-2026 \
  --start-date 2026-04-01 \
  --end-date 2026-05-31 \
  --fetch-articles \
  --title "Recently Funded Startups - May 2026 and April 2026"
```

## Verification Rules

Accepted rows must have:

- A valid, non-placeholder source URL.
- A source article date in the requested period.
- Company identity evidence from the source page when the page is crawled.
- No generic extracted company names such as `AI`, `FM`, or `Company`.

The verifier checks article dates in this order:

1. `article:published_time` or equivalent meta tags.
2. JSON-LD `datePublished`.
3. `<time datetime>`.
4. URL date only when explicitly allowed with `--allow-url-date-fallback`.

Rows that fail these checks are written to `needs-review-may-april-2026.csv`, not the main report.

## GitHub Actions

`.github/workflows/funding-alerts.yml` runs the public monitor on a schedule and uploads JSON/CSV/HTML artifacts. Add these optional secrets in GitHub:

- `TAVILY_API_KEY` through `TAVILY_API_KEY_10`
- `EXA_API_KEY` through `EXA_API_KEY_10`
- `PERPLEXITY_API_KEY`
- `APIFY_API_TOKEN` through `APIFY_API_TOKEN_10`

The workflow uploads artifacts by default and does not send outreach.

## Development

Run tests:

```bash
python -m unittest discover -s tests
```

Run the CLI directly:

```bash
python -m funding_monitor.cli --help
```

## Public Repo Setup

To configure a GitHub repository with optional provider secrets:

```bash
python execution/setup_github.py --repo your-name/funding-alert-monitor
```

The script reads `GITHUB_TOKEN` plus optional Tavily, Exa, Perplexity, and Apify keys from `.env`.
