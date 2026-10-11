"""robots.txt checks with a per-host cache."""

from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


class RobotsCache:
    def __init__(self, fetcher, user_agent: str) -> None:
        self._fetcher = fetcher
        self.user_agent = user_agent
        self._parsers: dict[str, RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        host = urlparse(url).netloc
        parser = self._parsers.get(host)
        if parser is None:
            parser = self._load(url)
            self._parsers[host] = parser
        return parser.can_fetch(self.user_agent, url)

    def _load(self, url: str) -> RobotFileParser:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            status, body, _headers = self._fetcher(robots_url)
            if status >= 400:
                parser.parse(["User-agent: *", "Allow: /"])
            else:
                parser.parse(body.decode("utf-8", errors="replace").splitlines())
        except OSError:
            parser.parse(["User-agent: *", "Allow: /"])
        return parser
