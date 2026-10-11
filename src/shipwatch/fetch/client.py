"""Polite HTTP client: UA, robots, rate limits, conditional GET."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from shipwatch.config import FetchSettings
from shipwatch.dates import now_utc
from shipwatch.fetch.robots import RobotsCache
from shipwatch.models import SourceKind, SourceSpec
from shipwatch.storage import Store


@dataclass
class HttpResponse:
    status_code: int
    url: str
    content: bytes
    headers: dict[str, str]
    not_modified: bool = False


Transport = Callable[[str, dict[str, str]], HttpResponse]


class PoliteClient:
    def __init__(
        self,
        settings: FetchSettings,
        store: Store | None = None,
        *,
        transport: Transport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self.store = store
        self.transport = transport
        self._sleep = sleep
        self._last_host: dict[str, float] = {}
        self._http: httpx.Client | None = None
        self.robots = RobotsCache(self._plain_get, settings.user_agent)

    def close(self) -> None:
        if self._http is not None:
            self._http.close()

    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(
                headers={"User-Agent": self.settings.user_agent, "Accept": "*/*"},
                timeout=self.settings.timeout_seconds,
                follow_redirects=True,
            )
        return self._http

    def _plain_get(self, url: str) -> tuple[int, bytes, dict[str, str]]:
        if self.transport is not None:
            resp = self.transport(url, {"User-Agent": self.settings.user_agent})
            return resp.status_code, resp.content, resp.headers
        response = self._client().get(url)
        return (
            response.status_code,
            response.content,
            {k.lower(): v for k, v in response.headers.items()},
        )

    def _pace(self, url: str) -> None:
        host = httpx.URL(url).host or ""
        last = self._last_host.get(host)
        now = time.monotonic()
        if last is not None:
            wait = self.settings.min_interval_seconds - (now - last)
            if wait > 0:
                self._sleep(wait)
        self._last_host[host] = time.monotonic()

    def get(
        self,
        url: str,
        *,
        source: SourceSpec | None = None,
        conditional: bool = True,
        extra_headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        if self.settings.respect_robots and not self.robots.allowed(url):
            raise PermissionError(f"robots.txt disallows {url}")
        headers = {"User-Agent": self.settings.user_agent, "Accept": "*/*"}
        if extra_headers:
            headers.update(extra_headers)
        if conditional and source and self.store:
            state = self.store.get_fetch_state(source.id)
            if state.get("etag"):
                headers["If-None-Match"] = state["etag"]
            if state.get("last_modified"):
                headers["If-Modified-Since"] = state["last_modified"]
        if source and source.kind is SourceKind.GITHUB:
            headers["Accept"] = "application/vnd.github+json"
            token = os.environ.get(self.settings.github_token_env, "").strip()
            if token:
                headers["Authorization"] = f"Bearer {token}"
        self._pace(url)
        if self.transport is not None:
            resp = self.transport(url, headers)
        else:
            response = self._client().get(url, headers=headers)
            resp = HttpResponse(
                status_code=response.status_code,
                url=str(response.url),
                content=response.content,
                headers={k.lower(): v for k, v in response.headers.items()},
            )
        resp.not_modified = resp.status_code == 304
        if source and self.store:
            fetched_at = now_utc()
            self.store.set_fetch_state(
                source.id,
                etag=resp.headers.get("etag") or resp.headers.get("ETag"),
                last_modified=resp.headers.get("last-modified")
                or resp.headers.get("Last-Modified"),
                last_fetch=fetched_at,
                last_status=resp.status_code,
                last_error=None if resp.status_code < 400 else f"HTTP {resp.status_code}",
            )
        return resp

    def record_error(self, source: SourceSpec, error: str, status: int | None = None) -> None:
        if self.store:
            self.store.set_fetch_state(
                source.id,
                last_fetch=now_utc(),
                last_status=status,
                last_error=error,
            )


def headers_lower(headers: dict[str, str]) -> dict[str, str]:
    return {k.lower(): v for k, v in headers.items()}


def check_url(client: PoliteClient, url: str) -> dict[str, Any]:
    """Live reachability probe used by ``shipwatch sources check --live``."""
    try:
        allowed = client.robots.allowed(url) if client.settings.respect_robots else True
        if not allowed:
            return {
                "url": url,
                "ok": False,
                "status": None,
                "detail": "robots.txt disallows this URL",
            }
        resp = client.get(url, conditional=False)
        return {
            "url": str(resp.url),
            "ok": 200 <= resp.status_code < 400,
            "status": resp.status_code,
            "detail": f"{len(resp.content)} bytes",
        }
    except Exception as exc:  # noqa: BLE001 - report any probe failure
        return {"url": url, "ok": False, "status": None, "detail": f"{type(exc).__name__}: {exc}"}
