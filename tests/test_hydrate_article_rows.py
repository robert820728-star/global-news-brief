import unittest

from scripts.hydrate_article_rows import extract_article_timestamp


class HydrateArticleRowsTests(unittest.TestCase):
    def test_extracts_jsonld_date_published(self):
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type":"NewsArticle","datePublished":"2026-09-06T04:59:00+08:00"}
        </script>
        </head><body>新聞正文</body></html>
        """
        published, evidence = extract_article_timestamp(html)
        self.assertIsNotNone(published)
        self.assertEqual("2026-09-06T04:59:00+08:00", published.isoformat())
        self.assertIn("datePublished", evidence)

    def test_extracts_cna_style_header_time(self):
        html = """
        <html><body>
        <div>規範致命自主武器邁出重要一步</div>
        <div>發稿時間：2026/09/06 04:59</div>
        <p>正文內容</p>
        </body></html>
        """
        published, evidence = extract_article_timestamp(html)
        self.assertEqual("2026-09-06T04:59:00+08:00", published.isoformat())
        self.assertIn("發稿時間", evidence)

    def test_extracts_chinanews_style_header_time(self):
        html = """
        <html><body>
        <h1>测试新闻</h1>
        <div>2026年09月05日 21:08 来源：中国新闻网</div>
        <p>正文内容</p>
        </body></html>
        """
        published, evidence = extract_article_timestamp(html)
        self.assertEqual("2026-09-05T21:08:00+08:00", published.isoformat())
        self.assertIn("header", evidence)

    def test_missing_timestamp_returns_none(self):
        published, evidence = extract_article_timestamp("<html><body>正文但没有时间</body></html>")
        self.assertIsNone(published)
        self.assertIsNone(evidence)


if __name__ == "__main__":
    unittest.main()
