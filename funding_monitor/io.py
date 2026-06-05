from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .records import FounderProfile, StartupRecord, parse_date


def read_records(path: str | Path) -> list[StartupRecord]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        items = payload.get("records", payload) if isinstance(payload, dict) else payload
        return [StartupRecord.from_dict(item) for item in items]
    if suffix == ".csv":
        return read_seed_csv(path)
    raise ValueError(f"Unsupported input format: {path}")


def write_json(records: list[StartupRecord], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump([record.to_dict() for record in records], handle, indent=2, ensure_ascii=False)


def write_startup_csv(records: list[StartupRecord], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "company_name",
        "website",
        "funding_amount",
        "funding_round",
        "announced_date",
        "article_published_date",
        "article_date_verified",
        "source_publisher",
        "source_url",
        "investors",
        "founders",
        "founder_linkedin_urls",
        "verification_status",
        "confidence",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "company_name": record.company_name,
                    "website": record.website,
                    "funding_amount": record.funding_amount,
                    "funding_round": record.funding_round,
                    "announced_date": record.announced_date.isoformat() if record.announced_date else "",
                    "article_published_date": (
                        record.article_published_date.isoformat() if record.article_published_date else ""
                    ),
                    "article_date_verified": str(record.article_date_verified).lower(),
                    "source_publisher": record.source_publisher,
                    "source_url": record.source_url,
                    "investors": "; ".join(record.investors),
                    "founders": "; ".join(founder.name for founder in verified_founders(record) if founder.name),
                    "founder_linkedin_urls": "; ".join(
                        founder.linkedin_url for founder in verified_founders(record) if founder.linkedin_url
                    ),
                    "verification_status": record.verification_status,
                    "confidence": record.confidence,
                    "notes": "; ".join(record.notes),
                }
            )


def write_founder_csv(records: list[StartupRecord], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "company_name",
        "website",
        "funding_amount",
        "funding_round",
        "announced_date",
        "founder_name",
        "founder_role",
        "linkedin_url",
        "founder_status",
        "founder_confidence",
        "source_url",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            for founder in verified_founders(record):
                writer.writerow(
                    {
                        "company_name": record.company_name,
                        "website": record.website,
                        "funding_amount": record.funding_amount,
                        "funding_round": record.funding_round,
                        "announced_date": record.announced_date.isoformat() if record.announced_date else "",
                        "founder_name": founder.name,
                        "founder_role": founder.role,
                        "linkedin_url": founder.linkedin_url,
                        "founder_status": founder.status,
                        "founder_confidence": founder.confidence,
                        "source_url": record.source_url,
                    }
                )


def write_founder_candidates_csv(records: list[StartupRecord], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "company_name",
        "funding_amount",
        "funding_round",
        "announced_date",
        "founder_name",
        "founder_role",
        "linkedin_url",
        "candidate_status",
        "candidate_confidence",
        "evidence",
        "source_url",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            for founder in record.founders:
                if founder.status == "verified":
                    continue
                writer.writerow(
                    {
                        "company_name": record.company_name,
                        "funding_amount": record.funding_amount,
                        "funding_round": record.funding_round,
                        "announced_date": record.announced_date.isoformat() if record.announced_date else "",
                        "founder_name": founder.name,
                        "founder_role": founder.role,
                        "linkedin_url": founder.linkedin_url,
                        "candidate_status": founder.status,
                        "candidate_confidence": founder.confidence,
                        "evidence": "; ".join(founder.evidence),
                        "source_url": record.source_url,
                    }
                )


def read_seed_csv(path: Path) -> list[StartupRecord]:
    records_by_key: dict[tuple[str, str, str, str], StartupRecord] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            company = clean_cell(row.get("startup") or row.get("company") or row.get("company_name"))
            if not company:
                continue

            round_size = clean_cell(row.get("round_size") or row.get("funding_amount") or row.get("amount"))
            amount, funding_round = split_round_size(round_size)
            source_url = clean_cell(row.get("article") or row.get("source_url") or row.get("url"))
            announced = parse_date(row.get("date") or row.get("announced_date"))
            key = (company.lower(), announced.isoformat() if announced else "", source_url.lower(), round_size.lower())

            record = records_by_key.get(key)
            if not record:
                record = StartupRecord(
                    company_name=company,
                    announced_date=announced,
                    funding_amount=amount,
                    funding_round=funding_round,
                    website=clean_cell(row.get("website") or row.get("company_website")),
                    source_url=source_url,
                    source_publisher=clean_cell(row.get("source")),
                    verification_status="needs_review",
                    raw={"seed_file": str(path), **row},
                )
                records_by_key[key] = record

            founder_name = clean_cell(row.get("founder_name") or row.get("name"))
            linkedin_url = clean_cell(row.get("linkedin_profile") or row.get("linkedin_url"))
            if founder_name or linkedin_url:
                record.founders.append(
                    FounderProfile(
                        name=founder_name,
                        role=clean_cell(row.get("founder_role") or row.get("role")),
                        linkedin_url=linkedin_url,
                        status="needs_review_seed_import",
                        confidence=confidence_from_source(row),
                        evidence=[
                            item
                            for item in [
                                clean_cell(row.get("source")),
                                clean_cell(row.get("status")),
                                f"seed_file:{path.name}",
                            ]
                            if item
                        ],
                    )
                )
    return list(records_by_key.values())


def clean_cell(value: Any) -> str:
    return str(value or "").strip()


def verified_founders(record: StartupRecord) -> list[FounderProfile]:
    return [founder for founder in record.founders if founder.status == "verified"]


def split_round_size(value: str) -> tuple[str, str]:
    text = value.strip()
    if not text:
        return "", ""
    parts = text.split()
    amount = normalize_amount(parts[0]) if parts and parts[0].startswith("$") else ""
    funding_round = " ".join(parts[1:]) if amount else text
    return amount, funding_round


def normalize_amount(value: str) -> str:
    text = str(value or "").strip()
    match = __import__("re").match(r"^\$(\d+)(?:\.0+)?([MB])$", text, __import__("re").I)
    if match:
        return f"${match.group(1)}{match.group(2).upper()}"
    return text


def confidence_from_source(row: dict[str, Any]) -> int:
    text = " ".join(str(value or "").lower() for value in row.values())
    if "strict" in text or "existing_report" in text:
        return 85
    if "confidence_75" in text:
        return 75
    if "confidence_60" in text:
        return 60
    return 50
