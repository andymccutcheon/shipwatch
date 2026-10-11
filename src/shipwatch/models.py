"""Shared domain types."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceKind(str, Enum):
    RSS = "rss"
    HTML = "html"
    GITHUB = "github"
    SITEMAP = "sitemap"


class ItemKind(str, Enum):
    LAUNCH = "launch"
    MODEL_RELEASE = "model_release"
    PRICING_CHANGE = "pricing_change"
    DEPRECATION = "deprecation"
    API_CHANGE = "api_change"
    AVAILABILITY = "availability"
    SECURITY = "security"
    OTHER = "other"


class SourceSpec(BaseModel):
    id: str
    name: str
    kind: SourceKind
    url: str | None = None
    repo: str | None = None
    selector: str | None = None
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None

    def target(self) -> str:
        if self.kind is SourceKind.GITHUB:
            if not self.repo:
                raise ValueError(f"source {self.id} is github but has no repo")
            return f"https://api.github.com/repos/{self.repo}/releases?per_page=30"
        if not self.url:
            raise ValueError(f"source {self.id} is {self.kind.value} but has no url")
        return self.url


class RawItem(BaseModel):
    source_id: str
    source_name: str
    url: str
    title: str
    published_at: datetime | None = None
    content: str = ""
    summary: str = ""
    tags: list[str] = Field(default_factory=list)


class Item(BaseModel):
    id: str
    source_id: str
    source_name: str
    url: str
    title: str
    published_at: datetime | None = None
    content: str = ""
    summary: str = ""
    kind: ItemKind = ItemKind.OTHER
    tags: list[str] = Field(default_factory=list)
    cluster_id: str | None = None
    score: float = 0.0
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    duplicate_of: str | None = None


class Fact(BaseModel):
    id: str
    item_id: str
    text: str
    kind: ItemKind = ItemKind.OTHER
    evidence: str = ""


class Cluster(BaseModel):
    id: str
    topic: str
    item_ids: list[str] = Field(default_factory=list)
    score: float = 0.0


class Claim(BaseModel):
    text: str
    source_item_ids: list[str] = Field(default_factory=list)
    supported: bool = True
    status: str = "supported"  # supported | flagged | dropped
    evidence: list[str] = Field(default_factory=list)
    note: str | None = None


class BriefingSection(BaseModel):
    heading: str
    score: float = 0.0
    item_ids: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)


class ClaimCoverage(BaseModel):
    total_claims: int = 0
    supported: int = 0
    flagged: int = 0
    dropped: int = 0

    @property
    def coverage_ratio(self) -> float:
        if self.total_claims == 0:
            return 0.0
        return (self.supported + self.flagged) / self.total_claims


class Briefing(BaseModel):
    id: str
    title: str
    generated_at: datetime
    since: str
    window_start: datetime
    mode: str = "heuristic"
    sections: list[BriefingSection] = Field(default_factory=list)
    coverage: ClaimCoverage = Field(default_factory=ClaimCoverage)
    selected_item_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    def kept_claims(self) -> list[Claim]:
        return [c for s in self.sections for c in s.claims if c.status != "dropped"]


class FetchOutcome(BaseModel):
    source_id: str
    status: str
    http_status: int | None = None
    items: int = 0
    new_items: int = 0
    detail: str = ""


class RunStats(BaseModel):
    fetched: int = 0
    items_considered: int = 0
    items_new: int = 0
    facts: int = 0
    clusters: int = 0
    selected: int = 0
    outcomes: list[FetchOutcome] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)
