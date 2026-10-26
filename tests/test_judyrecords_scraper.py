import json
import os
import unittest
from unittest.mock import MagicMock, patch

from scrape.judyrecords import (
    build_algorithmic_query,
    extract_candidate_terms,
    parse_case_page,
    search_judyrecords,
    _search_parameters,
)

SAMPLE_CASE_HTML = """<!doctype html>
<html>
<head>
    <title>Smith v. Jones - Gwinnett County, Georgia Court Record - judyrecords</title>
</head>
<body>
    <div id="caseInformationDiv" class="section">
        Case Information
        Case Number 2024-CV-12345
        Court Division Civil Division 2
        File Date 04/15/2024
        Case Type Breach of Contract
        Case Status Pending
    </div>
</body>
</html>
"""

OSCN_CASE_HTML = """<article class="record page"><div id="oscn-content">
<h2 class="styletop"><span class="styletop">In the District Court in and for Garfield County, Oklahoma</span></h2>
<table class="caseStyle"><tr><td>STATE OF OKLAHOMA,<br> Plaintiff,<br> v.<br> ANDY ANDY,<br> Defendant.</td>
<td><strong>No. CM-2020-260<br>(Criminal Misdemeanor)</strong><br>Filed: 04/22/2020<br>Closed: 09/17/2020</td></tr></table>
<h2 class="section party">Parties</h2><p>ANDY, Defendant<br>Enid Police Department, ARRESTING AGENCY<br>STATE OF OKLAHOMA, Plaintiff</p>
</div></article>"""


class JudyRecordsScraperTests(unittest.TestCase):
    def test_algorithmic_query_formatting(self):
        # Name with state
        q1 = build_algorithmic_query("", first_name="Jane", last_name="Doe", state="FL")
        self.assertEqual(q1, "Jane Doe,, fl")

        # Name without state
        q2 = build_algorithmic_query("", first_name="John", last_name="Smith")
        self.assertEqual(q2, "John Smith,,")

        # Plain search term with state
        q3 = build_algorithmic_query("Patent Infringement", state="DE")
        self.assertEqual(q3, "Patent Infringement de")

        # Plain search term without state
        q4 = build_algorithmic_query("Miranda v Arizona")
        self.assertEqual(q4, "Miranda v Arizona")

    def test_search_parameters_follow_homepage_search_form(self):
        html = '<form action="/" method="get"><input type="text" name="search"></form>'
        self.assertEqual(_search_parameters(html, "Smith"), {"search": "Smith"})

    def test_parse_case_page_extracts_structured_fields(self):
        case = parse_case_page(SAMPLE_CASE_HTML, "https://www.judyrecords.com/record/abc123")
        self.assertEqual(case["case_number"], "2024-CV-12345")
        self.assertEqual(case["division"], "Civil Division 2")
        self.assertEqual(case["file_date"], "04/15/2024")
        self.assertEqual(case["case_type"], "Breach of Contract")
        self.assertEqual(case["case_status"], "Pending")
        self.assertEqual(len(case["parties"]), 2)
        self.assertEqual(case["parties"][0]["name"], "Smith")
        self.assertEqual(case["parties"][0]["role"], "plaintiff")
        self.assertEqual(case["parties"][1]["name"], "Jones")
        self.assertEqual(case["parties"][1]["role"], "defendant")

    def test_parse_case_page_extracts_oscn_fields(self):
        case = parse_case_page(OSCN_CASE_HTML, "https://www.judyrecords.com/record/0dkk2dkd6452")
        self.assertEqual(case["case_number"], "CM-2020-260")
        self.assertEqual(case["court"], "Garfield County, Oklahoma District Court")
        self.assertEqual(case["case_type"], "Criminal Misdemeanor")
        self.assertEqual(case["case_status"], "Closed")
        self.assertEqual(case["parties"][0], {"name": "ANDY", "role": "defendant"})

    def test_extract_candidate_terms(self):
        cases = [
            {
                "title": "Acme Corp vs Global Logistics",
                "parties": [{"name": "Acme Corp", "role": "plaintiff"}, {"name": "Global Logistics", "role": "defendant"}],
            }
        ]
        candidates = extract_candidate_terms(cases)
        candidate_queries = [c["query"] for c in candidates]
        self.assertIn("Acme Corp", candidate_queries)
        self.assertIn("Global Logistics", candidate_queries)
        # Verify legal stopwords excluded
        self.assertNotIn("court", [c.lower() for c in candidate_queries])
        self.assertNotIn("vs", [c.lower() for c in candidate_queries])

    def test_offline_search_judyrecords_mock(self):
        mock_opener = MagicMock()

        def make_cm(payload):
            cm = MagicMock()
            cm.__enter__.return_value = cm
            cm.read.return_value = payload
            cm.status = 200
            return cm

        mock_opener.open.side_effect = [
            make_cm(b"<html>Home</html>"),
            make_cm(json.dumps({"status": "succeeded"}).encode()),
            make_cm(b'<html><a href="/record/rec1">Case 1</a></html>'),
            make_cm(SAMPLE_CASE_HTML.encode()),
        ]

        with patch("scrape.judyrecords.create_opener", return_value=mock_opener), \
             patch("time.sleep", return_value=None):
            result = search_judyrecords("breach of contract", max_records=1, proxy_url="http://test-proxy:8080")
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["result_count"], 1)
            self.assertEqual(result["cases"][0]["case_number"], "2024-CV-12345")
            self.assertTrue(len(result["candidate_terms"]) > 0)


if __name__ == "__main__":
    unittest.main()
