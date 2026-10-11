"""Source fetchers: RSS/Atom, HTML changelogs, GitHub releases, sitemaps."""

from shipwatch.fetch.client import PoliteClient
from shipwatch.fetch.github import parse_github_releases
from shipwatch.fetch.html import parse_html
from shipwatch.fetch.rss import parse_rss
from shipwatch.fetch.sitemap import parse_sitemap

__all__ = [
    "PoliteClient",
    "parse_github_releases",
    "parse_html",
    "parse_rss",
    "parse_sitemap",
]
