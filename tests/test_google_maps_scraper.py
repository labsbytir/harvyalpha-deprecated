import unittest

from scrape.client import ENDPOINT
from scrape.google_maps import extract, payload, validate_maps_url


class GoogleMapsScraperTests(unittest.TestCase):
    def test_unlimited_payload_targets_google_maps_page(self):
        self.assertTrue(ENDPOINT.endswith("/unlimited/scrape"))
        request = payload("https://www.google.com/maps/place/Example/")
        self.assertEqual(request["url"], "https://www.google.com/maps/place/Example/")
        self.assertTrue(request["return_json_data"])
        self.assertFalse(request["session"])

    def test_rejects_non_maps_and_credential_urls(self):
        for url in (
            "http://www.google.com/maps/place/Example",
            "https://www.google.com/search?q=place",
            "https://user:pass@www.google.com/maps/place/Example",
            "https://google.com.evil.example/maps/place/Example",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_maps_url(url)

    def test_normalizes_only_reviews_exposed_in_jsonld(self):
        page = {"status": 200, "metadata": {}, "links": [], "content": '''
        <script type="application/ld+json">{
          "@type":"LocalBusiness","name":"Example","telephone":"555-0100",
          "aggregateRating":{"ratingValue":"4.5","reviewCount":"1"},
          "review":{"@type":"Review","author":{"name":"Reviewer"},
            "reviewRating":{"ratingValue":"5"},"reviewBody":"Public review"}
        }</script>'''}
        result = extract(page, "https://www.google.com/maps/place/Example/")
        self.assertEqual(result["businesses"][0]["name"], "Example")
        self.assertEqual(result["review_count"], 1)
        self.assertEqual(result["reviews"][0]["text"], "Public review")
        self.assertFalse(result["complete"])


if __name__ == "__main__":
    unittest.main()
