# Jorge Funding Outreach System

Automated pipeline that monitors recently funded startups, finds decision makers, enriches contacts, generates personalized research reports, and creates ready-to-send email drafts in Gmail.

## Quick Start (5 Steps)

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Add your API keys
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

Required keys:
- **TAVILY_API_KEY** — Web search ($0.005/query, ~$1/day) — [tavily.com](https://tavily.com)
- **EXA_API_KEY** — LinkedIn search ($0.01/query) — [exa.ai](https://exa.ai)
- **PERPLEXITY_API_KEY** — Deep research ($0.005/query) — [perplexity.ai](https://perplexity.ai)
- **OPENAI_API_KEY** — Email generation ($0.01/email) — [platform.openai.com](https://platform.openai.com)

### 3. Set up Gmail OAuth
Place your `credentials.json` from Google Cloud Console in this folder, then run:
```bash
python execution/auth_jorge_gmail.py
```
This opens a browser for Google login. Grant Gmail compose + read permissions. Creates `token_gmail.json`.

### 4. Run the pipeline for a company
```bash
python execution/jorge_mvp_orchestrator.py --company "Resolve AI" --amount "$125M" --round "Series A" --send
```
This will:
- Find 3-8 decision makers (CEO, CTO, HR leads) via Exa/Tavily
- Enrich each person's profile (LinkedIn, email, social)
- Generate a research report
- Create personalized email drafts in your Gmail

### 5. Review and send from Gmail
Open Gmail > Drafts > Look for `[Funding Proposal]` subject lines. Review personalization, then send.

## What's in the Box

### Data (`data/`)
| File | Description |
|------|-------------|
| `master_startups.csv` | 167 recently funded companies (Jan-Feb 2026), sorted by hiring signal strength |
| `master_startups_enriched.json` | Same data as queryable JSON |
| `deep_research/{Company}/` | Per-company folders with research report + email drafts |
| `rejected_entries_for_review.csv` | Entries filtered during consolidation (for manual review) |

Each company that goes through the pipeline gets a folder like:
```
data/deep_research/ElevenLabs/
├── research_report.md          # Full research dossier
└── email_drafts/               # All email drafts for this company
    ├── CEO_Piotr_Dabkowski.md
    ├── Executive_Siddharth_Srinivasan.md
    └── ...
```

### Scripts (`execution/`)
| Script | What it does |
|--------|-------------|
| `funding_monitor_hybrid.py` | Monitors 16 RSS feeds + Tavily for new funding news. Run daily. |
| `jorge_mvp_orchestrator.py` | Full pipeline: company -> decision makers -> enrich -> research -> email drafts |
| `jorge_person_enricher.py` | Finds LinkedIn, email, social profiles for each person |
| `jorge_research_report.py` | Generates markdown research report per company |
| `jorge_email_generator.py` | Writes personalized emails + creates Gmail drafts |
| `consolidate_startup_data.py` | Parses all research sources into master CSV/JSON |
| `extract_all_drafts.py` | Lists all existing Gmail drafts with [Funding Proposal] |
| `auth_jorge_gmail.py` | One-time Gmail OAuth setup |

### SOPs (`directives/`)
| File | Description |
|------|-------------|
| `jorge_full_system_blueprint.md` | Complete system architecture and workflow |
| `expanded_funding_sources.md` | All 40+ funding news sources monitored |
| `jorge_deep_research_prompt.md` | Prompt template for Claude Pro deep research (manual enrichment) |

## Daily Usage

### Option A: Automated monitoring
```bash
python execution/funding_monitor_hybrid.py
```
Checks 16 RSS feeds (free) + Tavily (paid fallback) for new funding announcements. Outputs to `.tmp/funding_alerts/`.

### Option B: Manual pipeline for a specific company
```bash
# Research + draft emails (saves as Gmail drafts)
python execution/jorge_mvp_orchestrator.py --company "CompanyName" --amount "$50M" --round "Series B" --send

# Research only (no emails)
python execution/jorge_mvp_orchestrator.py --company "CompanyName" --amount "$50M" --round "Series B"
```

### Option C: Deep research via Claude Pro
Open Claude Pro, paste the prompt from `directives/jorge_deep_research_prompt.md`, and fill in the company details. Use this when automated enrichment didn't find emails or social profiles.

## Estimated API Costs

| Action | Cost per company | Monthly (30 companies) |
|--------|-----------------|----------------------|
| Tavily search | ~$0.05 | ~$1.50 |
| Exa LinkedIn search | ~$0.10 | ~$3.00 |
| Perplexity research | ~$0.02 | ~$0.60 |
| OpenAI email gen | ~$0.03 | ~$0.90 |
| **Total per company** | **~$0.20** | **~$6/month** |

RSS monitoring is free (16 feeds).

## GitHub Actions (Automated Daily Monitoring)

The repo includes a GitHub Actions workflow (`.github/workflows/daily_funding_monitor.yml`) that runs the pipeline automatically 3x per day (8am, 1pm, 6pm UTC). When it finds new funding announcements, it runs the full pipeline and creates Gmail drafts for you.

### Setup GitHub Actions

1. Go to your repo on GitHub > Settings > Secrets and variables > Actions
2. Add the following **Repository secrets**:

| Secret Name | Value | Where to get it |
|-------------|-------|----------------|
| `TAVILY_API_KEY` | `tvly-...` | [tavily.com](https://tavily.com) dashboard |
| `EXA_API_KEY` | `exa-...` | [exa.ai](https://exa.ai) dashboard |
| `PERPLEXITY_API_KEY` | `pplx-...` | [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api) |
| `OPENAI_API_KEY` | `sk-...` | [platform.openai.com](https://platform.openai.com) |
| `GMAIL_TOKEN_JORGE` | Full JSON content of `token_jorge_gmail.json` | Generated by `auth_jorge_gmail.py` |

3. To test: Go to Actions tab > "Daily Funding Monitor" > "Run workflow" > Click "Run workflow"
4. Check the run logs to see if it found companies and created drafts

### What the workflow does each run:
1. Scans 16 RSS feeds + Tavily for new funding news
2. Picks up to 3 new companies per run
3. Finds decision makers (CEO, CTO, HR)
4. Enriches each person (LinkedIn, email, location)
5. Generates research reports (saved as artifacts)
6. Creates personalized email drafts in your Gmail

Research reports from each run are saved as downloadable artifacts (kept for 30 days).

---

## Push Notifications (Desktop Alerts)

Get instant desktop notifications when new funding rounds are detected.

### Option A: Self-hosted ntfy (recommended)

The `ntfy-funding-alerts/` folder contains a Docker setup for self-hosting:

```bash
cd ntfy-funding-alerts
docker-compose up -d
```

This starts an ntfy server on `http://localhost:8080`. Open `http://localhost:8080/jorge-funding` in your browser and click "Subscribe" to receive desktop alerts.

### Option B: Use the desktop listener

For native Windows notifications (no browser needed):

```bash
pip install plyer requests
python ntfy-funding-alerts/ntfy_desktop_listener.py
```

Use `--startup-install` to auto-start on Windows boot:
```bash
python ntfy-funding-alerts/ntfy_desktop_listener.py --startup-install
```

### Notification format
Each alert includes:
- Company name, funding amount, round type
- Founder name and role
- Clickable buttons: Open Report, News Article, Founder LinkedIn

---

## Important Notes

- **Never commit** `token_gmail.json`, `credentials.json`, or `.env` to git
- Email drafts are created in Gmail — always review before sending
- The `master_startups.csv` can be opened in Excel or Google Sheets for filtering
- Companies are sorted by hiring signal strength (strongest signals first)
- See `API_SETUP_GUIDE.md` for detailed step-by-step instructions for each API key
