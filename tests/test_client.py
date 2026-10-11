from __future__ import annotations

from shipwatch.config import FetchSettings
from shipwatch.fetch.client import HttpResponse, PoliteClient
from shipwatch.models import SourceKind, SourceSpec


def test_robots_block() -> None:
    def transport(url: str, headers: dict[str, str]) -> HttpResponse:
        if url.endswith("/robots.txt"):
            return HttpResponse(200, url, b"User-agent: *\nDisallow: /\n", {})
        return HttpResponse(200, url, b"hi", {})

    client = PoliteClient(
        FetchSettings(respect_robots=True, min_interval_seconds=0),
        transport=transport,
        sleep=lambda _s: None,
    )
    source = SourceSpec(id="x", name="X", kind=SourceKind.HTML, url="https://blocked.example/page")
    try:
        try:
            client.get(source.url or "", source=source, conditional=False)
            raise AssertionError("expected robots block")
        except PermissionError:
            pass
    finally:
        client.close()


def test_conditional_and_rate_limit() -> None:
    calls = {"n": 0, "slept": 0.0}

    def transport(url: str, headers: dict[str, str]) -> HttpResponse:
        calls["n"] += 1
        if url.endswith("/robots.txt"):
            return HttpResponse(200, url, b"User-agent: *\nAllow: /\n", {})
        if headers.get("If-None-Match") == "abc":
            return HttpResponse(304, url, b"", {"etag": "abc"}, not_modified=True)
        return HttpResponse(200, url, b"body", {"etag": "abc"})

    def sleep(seconds: float) -> None:
        calls["slept"] += seconds

    settings = FetchSettings(respect_robots=True, min_interval_seconds=0.5)
    client = PoliteClient(settings, transport=transport, sleep=sleep)
    url = "https://pace.example/feed"
    source = SourceSpec(id="p", name="P", kind=SourceKind.RSS, url=url)
    first = client.get(url, source=source, conditional=False)
    assert first.status_code == 200
    client.get(url, source=source, conditional=True)
    # store is None so conditional headers are not applied; still paced.
    assert calls["slept"] > 0
    client.close()
