# Expanded Funding News Sources for Daily Monitoring
**Created:** 2026-02-04
**Purpose:** Comprehensive list of sources to ensure same-day coverage of tech startup funding announcements

---

## Current Sources (Already Configured)

```python
include_domains = [
    "techcrunch.com",
    "businesswire.com",
    "prnewswire.com",
    "crunchbase.com",
    "globenewswire.com",
]
```

---

## TIER 1: Add Immediately (High Value, Verified)

### Press Release Wires (Earliest Source)
These are where startups POST their funding PRs - often hours before media picks them up.

| Domain | Why Add | Coverage |
|--------|---------|----------|
| `accesswire.com` | Popular with early-stage startups | US tech, seed-Series B |
| `accessnewswire.com` | Same network | US tech |
| `prweb.com` | Very popular with smaller startups | US, budget-friendly wire |
| `einpresswire.com` | Low-cost wire, lots of seed/A rounds | US + EU tech |
| `newswire.com` | Mid-tier wire, detailed use-of-funds | B2B SaaS, infra |

### Funding-Only Aggregators (High Signal)
These sites ONLY cover funding - no noise.

| Domain | Why Add | Coverage |
|--------|---------|----------|
| `vcnewsdaily.com` | Pure funding feed, US cities, round stages | US tech daily |
| `thesaasnews.com` | SaaS-specific, Series A archive | B2B SaaS |
| `finsmes.com` | Dense list of seed-Series B, USA archive | US + global |

### Tech Media with Funding Beats
Systematic funding coverage, often same-day.

| Domain | Why Add | Coverage |
|--------|---------|----------|
| `venturebeat.com` | "Funding Daily" series | AI, software, infra |
| `siliconangle.com` | Strong AI/cloud focus | Enterprise tech |
| `geekwire.com` | Seattle + national tech | PNW, devtools, AI |

---

## TIER 2: Regional Coverage (NYC, LA, Other Metros)

| Domain | Region | Why Add |
|--------|--------|---------|
| `alleywatch.com` | NYC | Daily funding reports for NYC startups |
| `latechwatch.com` | LA | Daily funding reports for LA startups |
| `dot.la` | LA | Weekly "Raises" column |
| `builtin.com` | National | Weekly funding recaps by city |
| `builtinnyc.com` | NYC | NYC-specific |
| `builtinsf.com` | SF/Bay Area | Bay Area-specific |
| `builtinseattle.com` | Seattle | Seattle-specific |
| `builtinla.com` | LA | LA-specific |
| `builtinchicago.org` | Chicago | Chicago-specific |

---

## TIER 3: Nice-to-Have (Broader Coverage)

| Domain | Notes |
|--------|-------|
| `bizjournals.com` | Local business journals (some paywalled) |
| `axios.com` | Pro Rata deals digest (some paywalled) |
| `startupnewswire.com` | Startup-focused wire |
| `techstartupweekly.com` | Niche blog |

---

## Recommended Updated Configuration

```python
# funding_rss_monitor.py or tavily queries

include_domains = [
    # === TIER 0: Current (keep) ===
    "techcrunch.com",
    "businesswire.com",
    "prnewswire.com",
    "crunchbase.com",
    "globenewswire.com",

    # === TIER 1: Add Now ===
    # Press release wires (earliest source)
    "accesswire.com",
    "accessnewswire.com",
    "prweb.com",
    "einpresswire.com",
    "newswire.com",

    # Funding-only aggregators
    "vcnewsdaily.com",
    "thesaasnews.com",
    "finsmes.com",

    # Tech media with funding beats
    "venturebeat.com",
    "siliconangle.com",
    "geekwire.com",

    # === TIER 2: Regional ===
    "alleywatch.com",
    "latechwatch.com",
    "dot.la",
    "builtin.com",
    "builtinnyc.com",
    "builtinsf.com",
    "builtinseattle.com",
    "builtinla.com",

    # === TIER 3: Optional ===
    # "bizjournals.com",  # Often paywalled
    # "axios.com",        # Often paywalled
]
```

---

## Additional Query Patterns for New Sources

Add these to capture press-release language:

```python
queries = [
    # Existing
    '"raises" "million" funding startup',
    '"secures" "funding" Series A OR Series B',

    # New: Press release patterns
    '"announced today" "raises" "million" Series',
    '"has raised" "seed funding" "platform"',
    '"funding round" "to accelerate" OR "to expand"',

    # Hiring intent (for filtering)
    '"funding" "expand its team" OR "grow the team" OR "hiring"',
]
```

---

## Hiring Intent Keywords (for Filtering)

Many funding PRs explicitly mention hiring plans. Filter for:

```python
hiring_keywords = [
    "expand its team",
    "grow its team",
    "add headcount",
    "double the team",
    "hiring across",
    "hiring key roles",
    "expand engineering",
    "grow its engineering",
    "expand go-to-market",
    "support hiring",
]
```

---

## US Location Detection

Press release wires use datelines like:
- `SAN FRANCISCO, CA / ACCESSWIRE /`
- `BOSTON, MA / PRWeb /`
- `NEW YORK, NY / Newswire /`

Regex pattern:
```python
us_dateline_pattern = r'([A-Z]+(?:\s[A-Z]+)?),\s*(CA|NY|MA|TX|WA|CO|IL|GA|FL|NC|PA|OH|AZ|VA|OR|NV|UT|MN|TN|MD|WI|MO|IN|SC|AL|KY|LA|OK|CT|IA|MS|AR|KS|NE|NM|ID|NH|ME|HI|RI|MT|DE|SD|ND|AK|VT|WY|DC)\s*[-–/]'
```

---

## Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| Sources monitored | 5 | 20+ |
| Same-day detection | ~60% | ~90%+ |
| Regional coverage | Weak | Strong (NYC, LA, Seattle, Chicago) |
| Seed/early-stage | Moderate | Strong (PRWeb, EIN, AccessWire) |

---

## Implementation Steps

1. **Update `funding_rss_monitor.py`** - Add new domains to `include_domains`
2. **Add new query patterns** - Press release language
3. **Add hiring intent filter** - Prioritize leads with explicit hiring mentions
4. **Test for 1 week** - Monitor for noise/duplicates
5. **Tune weights** - Give higher priority to press wires (earliest) vs. media (delayed)

---

## Implementation Complete

**Script:** `execution/funding_monitor_hybrid.py`

### Usage

```bash
# Dry run - see what's new without processing
python execution/funding_monitor_hybrid.py --dry-run

# Run full pipeline for top 5 companies
python execution/funding_monitor_hybrid.py --run-pipeline --limit 5

# Save results to file
python execution/funding_monitor_hybrid.py --output .tmp/funding_results.json
```

### Test Results (2026-02-04)

| Source Type | Articles Found |
|-------------|----------------|
| RSS Feeds (FREE) | 32 |
| Tavily API | 39 |
| **Total Unique** | **64** |

**Top finds from today:**
- ElevenLabs - $500M Series D
- Resolve AI - $125M Series A
- Positron - $230M Series B
- Skyryse - $300M Series C
- Bedrock Robotics - $270M

### GitHub Actions Schedule

Add to `.github/workflows/funding_monitor.yml`:

```yaml
name: Funding Monitor

on:
  schedule:
    - cron: '0 8,14,20 * * *'  # 8am, 2pm, 8pm UTC
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install feedparser requests python-dotenv
      - run: python execution/funding_monitor_hybrid.py --run-pipeline --limit 3
        env:
          TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
          EXA_API_KEY: ${{ secrets.EXA_API_KEY }}
```

---

_Verified and tested 2026-02-04_
