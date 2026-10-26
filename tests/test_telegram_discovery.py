import unittest
from scrape.telegram import extract_telegram_links


class TestTelegramDiscovery(unittest.TestCase):
    def test_extract_telegram_links(self):
        text = """
        Check our channels:
        - https://t.me/blumcrypto
        - https://t.me/joinchat/AAAAAFDmYaSwbC6U9dPLAA
        - https://t.me/+AbCdEfGh1234
        - https://t.me/invalid.png
        - https://tgstat.com/channel/@ProxyMTProto
        """
        links = extract_telegram_links(text)
        self.assertIn("https://t.me/blumcrypto", links)
        self.assertIn("https://t.me/joinchat/AAAAAFDmYaSwbC6U9dPLAA", links)
        self.assertIn("https://t.me/+AbCdEfGh1234", links)
        self.assertFalse(any(l.endswith(".png") for l in links))


if __name__ == "__main__":
    unittest.main()
