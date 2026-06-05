from __future__ import annotations

import csv
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from funding_monitor.cli import main
from funding_monitor.enrichment import FounderProfile, StartupRecord, validate_founders
from funding_monitor.providers import env_keys
from funding_monitor.verification import (
    extract_article_date,
    extract_date_from_url,
    has_placeholder_url,
    verify_record,
)


class DateExtractionTests(unittest.TestCase):
    def test_extracts_article_published_time(self) -> None:
        html = '<html><head><meta property="article:published_time" content="2026-05-13T12:00:00Z"></head></html>'
        self.assertEqual(extract_article_date(html), date(2026, 5, 13))

    def test_extracts_json_ld_date(self) -> None:
        html = """
        <script type="application/ld+json">
        {"@type": "NewsArticle", "datePublished": "2026-04-22T08:15:00Z"}
        </script>
        """
        self.assertEqual(extract_article_date(html), date(2026, 4, 22))

    def test_extracts_time_datetime(self) -> None:
        html = '<article><time datetime="2026-05-01">May 1, 2026</time></article>'
        self.assertEqual(extract_article_date(html), date(2026, 5, 1))

    def test_extracts_url_date(self) -> None:
        url = "https://techcrunch.com/2026/05/11/example-raises-20m-series-a/"
        self.assertEqual(extract_date_from_url(url), date(2026, 5, 11))

    def test_extracts_businesswire_compact_url_date(self) -> None:
        url = "https://www.businesswire.com/news/home/20210223005330/en/Aviatrix-Raises-75-Million-in-Series-D-Funding"
        self.assertEqual(extract_date_from_url(url), date(2021, 2, 23))


class VerificationTests(unittest.TestCase):
    def test_rejects_old_techcrunch_article(self) -> None:
        record = StartupRecord(
            company_name="Chartboost",
            announced_date=date(2026, 5, 11),
            funding_amount="$2M",
            funding_round="Series A",
            source_url="https://techcrunch.com/2011/10/24/chartboost-raises-2-million-in-series-a-funding-already-profitable/",
        )
        verified = verify_record(
            record,
            date(2026, 4, 1),
            date(2026, 5, 31),
            allow_url_date_fallback=True,
        )
        self.assertEqual(verified.verification_status, "rejected_article_date_outside_target_window")

    def test_rejects_placeholder_url(self) -> None:
        self.assertTrue(has_placeholder_url("https://news.crunchbase.com/venture/biggest-funding-rounds-a..."))
        record = StartupRecord(company_name="Flock", source_url="https://news.crunchbase.com/venture/biggest-funding-rounds-a...")
        verified = verify_record(record, date(2026, 4, 1), date(2026, 5, 31))
        self.assertEqual(verified.verification_status, "rejected_invalid_source_url")

    def test_rejects_generic_company_name(self) -> None:
        record = StartupRecord(company_name="AI", source_url="https://example.com/2026/05/10/ai-raises/")
        verified = verify_record(record, date(2026, 4, 1), date(2026, 5, 31), allow_url_date_fallback=True)
        self.assertEqual(verified.verification_status, "rejected_invalid_company_name")

    def test_rejects_same_name_identity_conflict(self) -> None:
        record = StartupRecord(
            company_name="Oxygen",
            source_url="https://example.com/2026/05/10/oxygen-raises-series-a/",
        )
        html = """
        <html><head><meta property="article:published_time" content="2026-05-10"></head>
        <body>Carbon Labs raised a Series A round for climate software.</body></html>
        """
        verified = verify_record(
            record,
            date(2026, 4, 1),
            date(2026, 5, 31),
            html_by_url={record.source_url: html},
        )
        self.assertEqual(verified.verification_status, "rejected_identity_conflict")

    def test_rejects_aggregate_source_with_url_date_fallback(self) -> None:
        record = StartupRecord(
            company_name="Hermeus",
            funding_amount="$297.0B",
            source_url="https://techcrunch.com/2026/04/01/startup-funding-shatters-all-records-in-q1/",
        )
        verified = verify_record(
            record,
            date(2026, 4, 1),
            date(2026, 5, 31),
            allow_url_date_fallback=True,
        )
        self.assertEqual(verified.verification_status, "rejected_not_startup_funding_article")

    def test_rejects_event_page_about_raising_series_a(self) -> None:
        record = StartupRecord(
            company_name="Learn what it takes to raise a Series A in 2027 at Disrupt 2026",
            funding_round="Series A",
            source_url="https://techcrunch.com/2026/05/08/live-only-at-techcrunch-disrupt-2026-why-most-founders-are-already-behind-on-raising-a-series-a-in-2027/",
        )
        verified = verify_record(
            record,
            date(2026, 4, 1),
            date(2026, 5, 31),
            allow_url_date_fallback=True,
        )
        self.assertEqual(verified.verification_status, "rejected_invalid_company_name")


class FounderValidationTests(unittest.TestCase):
    def test_founder_needs_multiple_identity_signals(self) -> None:
        record = StartupRecord(
            company_name="Oxygen",
            source_url="https://example.com/2026/05/10/oxygen-raises-series-a/",
            article_date_verified=True,
            founders=[
                FounderProfile(
                    name="Ada Lovelace",
                    role="Co-founder",
                    linkedin_url="https://www.linkedin.com/in/ada-lovelace",
                )
            ],
        )
        [validated] = validate_founders([record])
        self.assertEqual(validated.founders[0].status, "verified")
        self.assertGreaterEqual(validated.founders[0].confidence, 75)


class ProviderRotationTests(unittest.TestCase):
    def test_env_keys_reads_base_through_ten(self) -> None:
        values = {"TAVILY_API_KEY": "key1"}
        values.update({f"TAVILY_API_KEY_{index}": f"key{index}" for index in range(2, 11)})
        with patch.dict(os.environ, values, clear=True):
            self.assertEqual(env_keys("TAVILY_API_KEY"), [f"key{index}" for index in range(1, 11)])


class PipelineTests(unittest.TestCase):
    def test_pipeline_generates_report_with_may_before_april(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = Path(tmp) / "seed.csv"
            with seed.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "date",
                        "startup",
                        "round_size",
                        "founder_name",
                        "founder_role",
                        "linkedin_profile",
                        "article",
                        "source",
                        "status",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "date": "2026-05-10",
                        "startup": "MayCo",
                        "round_size": "$10M Series A",
                        "founder_name": "Maya Founder",
                        "founder_role": "Founder",
                        "linkedin_profile": "https://www.linkedin.com/in/maya-founder",
                        "article": "https://example.com/2026/05/10/mayco-raises-10m/",
                        "source": "fixture",
                        "status": "fixture",
                    }
                )
                writer.writerow(
                    {
                        "date": "2026-04-07",
                        "startup": "AprilCo",
                        "round_size": "$6M Seed",
                        "founder_name": "April Founder",
                        "founder_role": "Co-founder",
                        "linkedin_profile": "https://www.linkedin.com/in/april-founder",
                        "article": "https://example.com/2026/04/07/aprilco-raises-6m/",
                        "source": "fixture",
                        "status": "fixture",
                    }
                )
            output_dir = Path(tmp) / "report"
            exit_code = main(
                [
                    "pipeline",
                    "--input",
                    str(seed),
                    "--output-dir",
                    str(output_dir),
                    "--allow-url-date-fallback",
                ]
            )
            self.assertEqual(exit_code, 0)
            html = (output_dir / "recently-funded-startups-may-april-2026.html").read_text(encoding="utf-8")
            self.assertLess(html.index("May 2026"), html.index("April 2026"))
            self.assertNotIn("...", html)


if __name__ == "__main__":
    unittest.main()
