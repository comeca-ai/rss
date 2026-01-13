import unittest

import httpx

from rss_br.discover import discover_candidates, validate_feed


class DiscoverTests(unittest.TestCase):
    def test_discover_candidates_from_link_alternate(self) -> None:
        html = """
        <html><head>
          <link rel="alternate" type="application/rss+xml" href="/rss.xml" />
        </head><body></body></html>
        """
        cands = discover_candidates("https://example.com/", html)
        self.assertIn("https://example.com/rss.xml", cands)

    def test_validate_feed_parses_rss_and_topics(self) -> None:
        rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Exemplo</title>
            <link>https://example.com/</link>
            <item>
              <title>Notícia</title>
              <category>Brasil</category>
            </item>
          </channel>
        </rss>
        """

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"content-type": "application/rss+xml; charset=utf-8"},
                content=rss.encode("utf-8"),
            )

        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as client:
            rec = validate_feed(client, "https://example.com/rss.xml")
            self.assertIsNone(rec.error)
            self.assertEqual(rec.kind, "rss")
            self.assertEqual(rec.title, "Exemplo")
            self.assertIn("Brasil", rec.topics)


if __name__ == "__main__":
    unittest.main()

