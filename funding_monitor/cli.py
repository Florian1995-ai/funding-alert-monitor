from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .enrichment import validate_founders
from .enrichment import enrich_founders_with_search
from .io import read_records, write_json
from .monitoring import collect_candidates
from .monitoring import collect_range_candidates
from .records import StartupRecord, parse_date
from .reporting import write_report_bundle
from .verification import date_window_from_days, verify_records

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


def main(argv: list[str] | None = None) -> int:
    if load_dotenv is not None:
        load_dotenv()

    parser = argparse.ArgumentParser(prog="funding-monitor", description="Monitor, verify, enrich, and report recently funded startups.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    monitor_parser = subparsers.add_parser("monitor", help="Find candidate funding announcements.")
    monitor_parser.add_argument("--days-back", type=int, default=2)
    monitor_parser.add_argument("--start-date")
    monitor_parser.add_argument("--end-date")
    monitor_parser.add_argument("--limit", type=int, default=50)
    monitor_parser.add_argument("--use-rss", action="store_true", default=True)
    monitor_parser.add_argument("--use-tavily", action="store_true")
    monitor_parser.add_argument("--output", required=True)

    verify_parser = subparsers.add_parser("verify", help="Verify article dates and company identity.")
    verify_parser.add_argument("--input", action="append", required=True)
    verify_parser.add_argument("--output", required=True)
    verify_parser.add_argument("--start-date")
    verify_parser.add_argument("--end-date")
    verify_parser.add_argument("--days-back", type=int)
    verify_parser.add_argument("--fetch-articles", action="store_true")
    verify_parser.add_argument("--allow-url-date-fallback", action="store_true")
    verify_parser.add_argument("--use-apify", action="store_true")
    verify_parser.add_argument("--max-apify-runs", type=int, default=0)
    verify_parser.add_argument("--fetch-timeout", type=int, default=8)
    verify_parser.add_argument("--max-workers", type=int, default=8)

    enrich_parser = subparsers.add_parser("enrich", help="Validate founder and LinkedIn rows already present in records.")
    enrich_parser.add_argument("--input", action="append", required=True)
    enrich_parser.add_argument("--output", required=True)
    enrich_parser.add_argument("--use-tavily", action="store_true")
    enrich_parser.add_argument("--use-exa", action="store_true")
    enrich_parser.add_argument("--max-records", type=int, default=0)
    enrich_parser.add_argument("--max-results-per-record", type=int, default=6)

    report_parser = subparsers.add_parser("report", help="Create CSV, JSON, and HTML report artifacts.")
    report_parser.add_argument("--input", action="append", required=True)
    report_parser.add_argument("--output-dir", required=True)
    report_parser.add_argument("--title", default="Recently Funded Startup Report")

    pipeline_parser = subparsers.add_parser("pipeline", help="Run verify, founder validation, and report generation from seed files.")
    pipeline_parser.add_argument("--input", action="append", required=True)
    pipeline_parser.add_argument("--output-dir", required=True)
    pipeline_parser.add_argument("--title", default="Recently Funded Startups - May 2026 and April 2026")
    pipeline_parser.add_argument("--start-date", default="2026-04-01")
    pipeline_parser.add_argument("--end-date", default="2026-05-31")
    pipeline_parser.add_argument("--fetch-articles", action="store_true")
    pipeline_parser.add_argument("--allow-url-date-fallback", action="store_true")
    pipeline_parser.add_argument("--use-apify", action="store_true")
    pipeline_parser.add_argument("--max-apify-runs", type=int, default=0)
    pipeline_parser.add_argument("--fetch-timeout", type=int, default=8)
    pipeline_parser.add_argument("--max-workers", type=int, default=8)
    pipeline_parser.add_argument("--enrich-founders", action="store_true")
    pipeline_parser.add_argument("--use-tavily", action="store_true")
    pipeline_parser.add_argument("--use-exa", action="store_true")
    pipeline_parser.add_argument("--max-enrich-records", type=int, default=0)

    args = parser.parse_args(argv)

    if args.command == "monitor":
        if args.start_date or args.end_date:
            records = collect_range_candidates(
                parse_required_date(args.start_date),
                parse_required_date(args.end_date),
                use_tavily=args.use_tavily,
                limit=args.limit,
            )
        else:
            records = collect_candidates(days_back=args.days_back, use_rss=args.use_rss, use_tavily=args.use_tavily, limit=args.limit)
        write_json(records, args.output)
        print(f"Wrote {len(records)} funding candidates to {args.output}")
        return 0

    if args.command == "verify":
        records = dedupe_record_list(load_many(args.input))
        start_date, end_date = resolve_window(args.start_date, args.end_date, args.days_back)
        records = verify_records(
            records,
            start_date,
            end_date,
            fetch_articles=args.fetch_articles,
            allow_url_date_fallback=args.allow_url_date_fallback,
            use_apify=args.use_apify,
            max_apify_runs=args.max_apify_runs,
            fetch_timeout=args.fetch_timeout,
            max_workers=args.max_workers,
        )
        write_json(records, args.output)
        print(f"Wrote {len(records)} verified/review records to {args.output}")
        return 0

    if args.command == "enrich":
        records = dedupe_record_list(load_many(args.input))
        if args.use_tavily or args.use_exa:
            records = enrich_founders_with_search(
                records,
                use_tavily=args.use_tavily,
                use_exa=args.use_exa,
                max_records=args.max_records,
                max_results_per_record=args.max_results_per_record,
            )
        records = validate_founders(records)
        write_json(records, args.output)
        print(f"Wrote {len(records)} enriched records to {args.output}")
        return 0

    if args.command == "report":
        records = dedupe_record_list(load_many(args.input))
        paths = write_report_bundle(records, args.output_dir, args.title)
        print_paths(paths)
        return 0

    if args.command == "pipeline":
        records = load_many(args.input)
        records = verify_records(
            records,
            parse_required_date(args.start_date),
            parse_required_date(args.end_date),
            fetch_articles=args.fetch_articles,
            allow_url_date_fallback=args.allow_url_date_fallback,
            use_apify=args.use_apify,
            max_apify_runs=args.max_apify_runs,
            fetch_timeout=args.fetch_timeout,
            max_workers=args.max_workers,
        )
        if args.enrich_founders:
            records = enrich_founders_with_search(
                records,
                use_tavily=args.use_tavily,
                use_exa=args.use_exa,
                max_records=args.max_enrich_records,
            )
        records = validate_founders(records)
        paths = write_report_bundle(records, args.output_dir, args.title)
        print_paths(paths)
        return 0

    return 1


def load_many(paths: list[str]) -> list[StartupRecord]:
    records: list[StartupRecord] = []
    for path in paths:
        records.extend(read_records(path))
    return records


def dedupe_record_list(records: list[StartupRecord]) -> list[StartupRecord]:
    seen: set[tuple[str, str]] = set()
    deduped: list[StartupRecord] = []
    for record in records:
        key = (record.company_name.lower(), record.source_url.lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def resolve_window(start: str | None, end: str | None, days_back: int | None) -> tuple[date | None, date | None]:
    if days_back is not None:
        return date_window_from_days(days_back)
    if start or end:
        return parse_required_date(start), parse_required_date(end)
    return None, None


def parse_required_date(value: str | None) -> date:
    parsed = parse_date(value)
    if parsed is None:
        raise ValueError(f"Invalid date: {value}")
    return parsed


def print_paths(paths: dict[str, Path]) -> None:
    for label, path in paths.items():
        print(f"{label}: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
