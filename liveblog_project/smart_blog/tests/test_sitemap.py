"""Tests for public sitemap index and robots.txt."""
from django.test import Client, TestCase
from django.urls import reverse


class PublicSitemapTests(TestCase):
    def test_sitemap_index_200(self):
        r = Client().get("/sitemap.xml")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"sitemapindex", r.content)

    def test_robots_txt_contains_sitemap(self):
        r = Client().get("/robots.txt")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Sitemap:", r.content)
        self.assertIn(b"sitemap.xml", r.content)

    def test_html_sitemap_200(self):
        url = reverse("pages:sitemap_page")
        self.assertEqual(url, "/sitemap/")
        r = Client().get(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'sitemap-page', r.content)
        self.assertIn(b"sitemap.xml", r.content)

    def test_static_sitemap_entries_include_pages_sitemap(self):
        from smart_blog.sitemaps import static_sitemap_entries

        names = [e[1] for e in static_sitemap_entries()]
        self.assertIn("pages:sitemap_page", names)
