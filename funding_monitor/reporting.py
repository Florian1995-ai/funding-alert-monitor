from __future__ import annotations

import html
from collections import defaultdict
from datetime import date
from pathlib import Path

from .io import write_founder_candidates_csv, write_founder_csv, write_json, write_startup_csv
from .records import StartupRecord


def split_verified(records: list[StartupRecord]) -> tuple[list[StartupRecord], list[StartupRecord]]:
    verified = [record for record in records if record.verification_status == "verified"]
    needs_review = [record for record in records if record.verification_status != "verified"]
    return verified, needs_review


def write_report_bundle(records: list[StartupRecord], output_dir: str | Path, title: str) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records = dedupe_for_report(records)
    verified, needs_review = split_verified(records)

    paths = {
        "html": output_dir / "recently-funded-startups-may-april-2026.html",
        "startup_csv": output_dir / "funded-startups-may-april-2026.csv",
        "json": output_dir / "funded-startups-may-april-2026.json",
        "founder_csv": output_dir / "founders-linkedin-may-april-2026.csv",
        "founder_candidates_csv": output_dir / "founder-candidates-needs-review-may-april-2026.csv",
        "needs_review_csv": output_dir / "needs-review-may-april-2026.csv",
    }
    write_json(records, paths["json"])
    write_startup_csv(verified, paths["startup_csv"])
    write_founder_csv(verified, paths["founder_csv"])
    write_founder_candidates_csv(verified, paths["founder_candidates_csv"])
    write_startup_csv(needs_review, paths["needs_review_csv"])
    paths["html"].write_text(render_html_report(verified, needs_review, title), encoding="utf-8")
    return paths


def dedupe_for_report(records: list[StartupRecord]) -> list[StartupRecord]:
    grouped: dict[tuple[str, str, str, str], StartupRecord] = {}
    for record in records:
        date_value = record.article_published_date or record.announced_date
        key = (
            record.company_name.strip().lower(),
            date_value.isoformat() if date_value else "",
            normalize_amount(record.funding_amount).lower(),
        )
        existing = grouped.get(key)
        if not existing:
            record.funding_amount = normalize_amount(record.funding_amount)
            grouped[key] = record
            continue
        existing.founders = merge_founders(existing.founders, record.founders)
        existing.notes = sorted(set(existing.notes + record.notes))
        existing.confidence = max(existing.confidence, record.confidence)
        if not existing.website and record.website:
            existing.website = record.website
        existing.funding_round = choose_round(existing.funding_round, record.funding_round)
        if len(record.source_url) > len(existing.source_url) and "..." not in record.source_url:
            existing.source_url = record.source_url
        if not existing.source_title and record.source_title:
            existing.source_title = record.source_title
    return list(grouped.values())


def merge_founders(left, right):
    seen = {(founder.name.lower(), founder.linkedin_url.lower()) for founder in left}
    merged = list(left)
    for founder in right:
        key = (founder.name.lower(), founder.linkedin_url.lower())
        if key in seen:
            continue
        seen.add(key)
        merged.append(founder)
    return merged


def normalize_amount(value: str) -> str:
    import re

    text = str(value or "").strip()
    match = re.match(r"^\$(\d+)(?:\.0+)?([MB])$", text, re.I)
    if match:
        return f"${match.group(1)}{match.group(2).upper()}"
    return text


def choose_round(left: str, right: str) -> str:
    order = {
        "Pre-seed": 7,
        "Seed": 6,
        "Series A": 5,
        "Series B": 5,
        "Series C": 5,
        "Series D": 5,
        "Series E": 5,
    }
    if not left:
        return right
    if not right:
        return left
    return left if order.get(left, 0) >= order.get(right, 0) else right


def render_html_report(verified: list[StartupRecord], needs_review: list[StartupRecord], title: str) -> str:
    by_month: dict[str, list[StartupRecord]] = defaultdict(list)
    for record in verified:
        key = month_key(record.article_published_date or record.announced_date)
        by_month[key].append(record)

    may = sorted(by_month.get("May 2026", []), key=sort_key)
    april = sorted(by_month.get("April 2026", []), key=sort_key)
    other = [record for key, items in by_month.items() if key not in {"May 2026", "April 2026"} for record in items]

    founder_count = sum(len(verified_founders(record)) for record in verified)
    linkedin_count = sum(1 for record in verified for founder in verified_founders(record) if founder.linkedin_url)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <style>
    :root {{
      --bg: #f5f7fb;
      --card: #ffffff;
      --ink: #162033;
      --muted: #5d6c82;
      --line: #dce3ed;
      --accent: #0f5cc0;
      --accent2: #164b8f;
      --soft: #edf4ff;
      --green: #167449;
      --green-bg: #e8f7ef;
      --amber: #9a5b00;
      --amber-bg: #fff4df;
      --red: #a12c2c;
      --red-bg: #fdeaea;
      --shadow: 0 18px 40px rgba(18,39,70,0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, Arial, Helvetica, sans-serif;
      background: linear-gradient(180deg,#eef4fb 0%,#f9fbfe 100%);
      color: var(--ink);
      line-height: 1.5;
    }}
    a {{ color: var(--accent); text-decoration: none; word-break: break-word; }}
    a:hover {{ text-decoration: underline; }}
    .wrap {{ max-width: 1320px; margin: 0 auto; padding: 38px 24px 76px; }}
    .hero {{
      background: linear-gradient(135deg,#0d2a52 0%,#153f78 55%,#1c4b8f 100%);
      color: white;
      border-radius: 22px;
      padding: 36px 40px;
      box-shadow: var(--shadow);
      margin-bottom: 26px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 31px; line-height: 1.15; }}
    .subtitle {{ margin: 0; color: rgba(255,255,255,0.84); }}
    .meta {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap: 10px; margin-top: 22px; }}
    .pill {{
      background: rgba(255,255,255,0.12);
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 12px;
      padding: 11px 14px;
    }}
    .pill .k {{ font-size: 10px; text-transform: uppercase; letter-spacing: .08em; opacity: .8; }}
    .pill .v {{ font-size: 20px; font-weight: 800; margin-top: 3px; }}
    .note {{
      background: var(--soft);
      border-left: 4px solid var(--accent);
      border-radius: 8px;
      padding: 15px 18px;
      margin-bottom: 24px;
      font-size: 14px;
    }}
    .section {{ margin-top: 30px; }}
    .section-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
      padding-bottom: 12px;
      border-bottom: 2px solid var(--line);
    }}
    .section-header h2 {{ margin: 0; font-size: 21px; }}
    .badge {{
      background: var(--soft);
      border: 1px solid #c2d8f5;
      border-radius: 999px;
      color: var(--accent2);
      font-size: 12px;
      font-weight: 700;
      padding: 5px 10px;
      white-space: nowrap;
    }}
    table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      background: white;
      border: 1px solid var(--line);
      border-radius: 10px;
      overflow: hidden;
      box-shadow: 0 8px 24px rgba(18,39,70,0.05);
    }}
    th, td {{ padding: 11px 12px; border-bottom: 1px solid var(--line); vertical-align: top; font-size: 13px; }}
    th {{ background: #f0f5fb; color: #34445c; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }}
    tr:last-child td {{ border-bottom: 0; }}
    .company {{ font-weight: 800; font-size: 14px; }}
    .muted {{ color: var(--muted); font-size: 12px; }}
    .status {{ display: inline-block; border-radius: 999px; padding: 3px 8px; font-size: 11px; font-weight: 800; }}
    .verified {{ color: var(--green); background: var(--green-bg); }}
    .review {{ color: var(--amber); background: var(--amber-bg); }}
    .rejected {{ color: var(--red); background: var(--red-bg); }}
    .founders {{ min-width: 220px; }}
    .founder {{ margin-bottom: 8px; }}
    .founder:last-child {{ margin-bottom: 0; }}
    .nowrap {{ white-space: nowrap; }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <h1>{escape(title)}</h1>
      <p class="subtitle">Verified funding announcements grouped May 2026 first, then April 2026. Old articles and identity conflicts are excluded from the main tables.</p>
      <div class="meta">
        <div class="pill"><div class="k">Verified Startups</div><div class="v">{len(verified)}</div></div>
        <div class="pill"><div class="k">Verified Founders</div><div class="v">{founder_count}</div></div>
        <div class="pill"><div class="k">LinkedIn URLs</div><div class="v">{linkedin_count}</div></div>
        <div class="pill"><div class="k">Needs Review</div><div class="v">{len(needs_review)}</div></div>
      </div>
    </section>
    <div class="note">Verification requires a valid source URL, a funding article date in April or May 2026, and company identity evidence. Founder rows are included only after basic public LinkedIn/profile sanity checks.</div>
    {render_section("May 2026", may)}
    {render_section("April 2026", april)}
    {render_section("Other Verified Dates", other) if other else ""}
    {render_review_section(needs_review)}
  </main>
</body>
</html>
"""


def render_section(title: str, records: list[StartupRecord]) -> str:
    return f"""
    <section class="section">
      <div class="section-header"><h2>{escape(title)}</h2><span class="badge">{len(records)} startups</span></div>
      {render_table(records, show_status=False)}
    </section>
"""


def render_review_section(records: list[StartupRecord]) -> str:
    limited = sorted(records, key=lambda record: (record.verification_status, record.company_name.lower()))
    return f"""
    <section class="section">
      <div class="section-header"><h2>Needs Review / Rejected</h2><span class="badge">{len(records)} rows</span></div>
      {render_table(limited, show_status=True)}
    </section>
"""


def render_table(records: list[StartupRecord], *, show_status: bool) -> str:
    if not records:
        return '<div class="note">No records in this section.</div>'
    status_header = "<th>Status</th>" if show_status else ""
    rows = "\n".join(render_row(record, show_status=show_status) for record in records)
    return f"""
      <table>
        <thead>
          <tr>
            <th>Startup</th>
            <th>Round</th>
            <th>Date</th>
            <th>Source</th>
            <th>Founders / LinkedIn</th>
            {status_header}
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
"""


def render_row(record: StartupRecord, *, show_status: bool) -> str:
    date_text = record.article_published_date or record.announced_date
    status_cell = f"<td>{status_badge(record.verification_status)}</td>" if show_status else ""
    return f"""
          <tr>
            <td>
              <div class="company">{escape(record.company_name)}</div>
              {link_or_text(record.website, record.website, "muted")}
            </td>
            <td><strong>{escape(record.funding_amount)}</strong><div class="muted">{escape(record.funding_round)}</div></td>
            <td class="nowrap">{escape(date_text.isoformat() if date_text else "")}</td>
            <td>{link_or_text(record.source_url, record.source_publisher or record.source_url)}<div class="muted">{escape(record.source_title)}</div></td>
            <td class="founders">{render_founders(record)}</td>
            {status_cell}
          </tr>
"""


def render_founders(record: StartupRecord) -> str:
    founders = verified_founders(record)
    if not founders:
        return '<span class="muted">No verified founder LinkedIn yet</span>'
    parts = []
    for founder in founders:
        label = escape(founder.name or "Unknown founder")
        role = f'<div class="muted">{escape(founder.role)}</div>' if founder.role else ""
        link = link_or_text(founder.linkedin_url, "LinkedIn") if founder.linkedin_url else '<span class="muted">LinkedIn missing</span>'
        parts.append(f'<div class="founder"><strong>{label}</strong>{role}{link}</div>')
    return "".join(parts)


def verified_founders(record: StartupRecord):
    return [founder for founder in record.founders if founder.status == "verified"]


def status_badge(status: str) -> str:
    css = "verified" if status == "verified" else "rejected" if status.startswith("rejected") else "review"
    return f'<span class="status {css}">{escape(status)}</span>'


def link_or_text(url: str, label: str, css_class: str = "") -> str:
    css = f' class="{css_class}"' if css_class else ""
    if url and url.startswith(("http://", "https://")):
        return f'<a{css} href="{escape(url)}" target="_blank" rel="noopener">{escape(label or url)}</a>'
    if label:
        return f"<span{css}>{escape(label)}</span>"
    return ""


def month_key(value: date | None) -> str:
    if not value:
        return "Unknown"
    return value.strftime("%B %Y")


def sort_key(record: StartupRecord) -> tuple[str, str]:
    value = record.article_published_date or record.announced_date
    return (value.isoformat() if value else "", record.company_name.lower())


def escape(value: object) -> str:
    return html.escape(str(value or ""))
