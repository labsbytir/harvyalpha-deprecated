import unittest
from unittest.mock import patch

from search.client import SearchClient
from search.forms import discover_search_forms


class SearchFrameworkTests(unittest.TestCase):
    def test_discovers_get_form_and_preserves_hidden_fields(self):
        forms = discover_search_forms(
            '<form action="/find" method="get"><input type="hidden" name="scope" value="all">'
            '<input type="search" name="term"></form>',
            "https://example.test/home",
        )
        self.assertEqual(len(forms), 1)
        self.assertEqual(forms[0].request_url("Ada Lovelace"), "https://example.test/find?scope=all&term=Ada+Lovelace")

    def test_discovers_post_form(self):
        forms = discover_search_forms(
            '<form action="/search" method="post"><input name="query"></form>',
            "https://example.test/",
        )
        self.assertEqual(forms[0].method, "POST")
        self.assertEqual(forms[0].payload("records"), {"query": "records"})

    def test_client_submits_form_and_normalizes_result_links(self):
        class Response:
            status = 200
            headers = type("Headers", (), {"get_content_charset": lambda self: "utf-8"})()

            def __init__(self, url, body):
                self.url, self.body = url, body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return self.body.encode()

            def geturl(self):
                return self.url

        responses = iter([
            Response("https://example.test/", '<form action="/find"><input name="q"></form>'),
            Response("https://example.test/find?q=records", '<a href="/case">Case record</a>'),
        ])
        with patch("search.client.urlopen", side_effect=lambda *args, **kwargs: next(responses)):
            result = SearchClient().search("https://example.test/", "records")
        self.assertEqual(result.results[0].url, "https://example.test/case")


if __name__ == "__main__":
    unittest.main()
