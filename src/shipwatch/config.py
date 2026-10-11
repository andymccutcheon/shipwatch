"""YAML config, defaults, and the bundled source pack."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from shipwatch._version import __version__
from shipwatch.models import SourceKind, SourceSpec

DEFAULT_USER_AGENT = f"shipwatch/{__version__} (+https://github.com/andymccutcheon/shipwatch)"
DEFAULT_FREEWHIRR_BASE = "http://127.0.0.1:8787/v1"
DEFAULT_FREEWHIRR_MODEL = "freewhirr"


@dataclass
class LLMSettings:
    base_url: str = DEFAULT_FREEWHIRR_BASE
    model: str = DEFAULT_FREEWHIRR_MODEL
    api_key_env: str = "SHIPWATCH_API_KEY"
    timeout_seconds: float = 60.0
    retries: int = 2
    temperature: float = 0.2

    def api_key(self) -> str:
        for name in (self.api_key_env, "OPENROUTER_API_KEY", "OPENAI_API_KEY"):
            value = os.environ.get(name, "").strip()
            if value:
                return value
        return "not-used"


@dataclass
class ScoringSettings:
    novelty: float = 0.25
    impact: float = 0.30
    breadth: float = 0.20
    recency: float = 0.25
    pricing_boost: float = 0.15
    deprecation_boost: float = 0.15
    security_boost: float = 0.10
    recency_half_life_days: float = 7.0
    near_dup_threshold: float = 0.62
    cluster_threshold: float = 0.28


@dataclass
class BriefSettings:
    top_n: int = 12
    since: str = "7d"
    output_dir: Path = Path("out")
    html: bool = False


@dataclass
class FetchSettings:
    user_agent: str = DEFAULT_USER_AGENT
    timeout_seconds: float = 30.0
    respect_robots: bool = True
    min_interval_seconds: float = 1.0
    max_items_per_source: int = 40
    github_token_env: str = "GITHUB_TOKEN"


@dataclass
class AppConfig:
    config_path: Path | None = None
    data_dir: Path = Path(".shipwatch")
    sources_file: Path | None = None
    sources: list[SourceSpec] = field(default_factory=list)
    llm: LLMSettings = field(default_factory=LLMSettings)
    scoring: ScoringSettings = field(default_factory=ScoringSettings)
    brief: BriefSettings = field(default_factory=BriefSettings)
    fetch: FetchSettings = field(default_factory=FetchSettings)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "shipwatch.db"

    def enabled_sources(self) -> list[SourceSpec]:
        return [s for s in self.sources if s.enabled]


def bundled_sources_path() -> Path:
    ref = resources.files("shipwatch").joinpath("data/sources.yaml")
    return Path(str(ref))


def default_config_text() -> str:
    return f"""# shipwatch.yaml
# Know what AI companies actually shipped this week.

data_dir: .shipwatch
sources_file: sources.yaml

llm:
  # Default: Andy's free-first OpenRouter router (https://github.com/andymccutcheon/freewhirr)
  #   pip install freewhirr && freewhirr serve --port 8787
  base_url: {DEFAULT_FREEWHIRR_BASE}
  model: {DEFAULT_FREEWHIRR_MODEL}
  api_key_env: SHIPWATCH_API_KEY
  # OpenRouter (direct):
  #   base_url: https://openrouter.ai/api/v1
  #   model: meta-llama/llama-3.3-70b-instruct:free
  #   api_key_env: OPENROUTER_API_KEY
  # OpenAI:
  #   base_url: https://api.openai.com/v1
  #   model: gpt-4o-mini
  #   api_key_env: OPENAI_API_KEY
  retries: 2
  temperature: 0.2

scoring:
  weights:
    novelty: 0.25
    impact: 0.30
    breadth: 0.20
    recency: 0.25
  boosts:
    pricing_change: 0.15
    deprecation: 0.15
    security: 0.10
  recency_half_life_days: 7
  near_dup_threshold: 0.62
  cluster_threshold: 0.28

brief:
  top_n: 12
  since: 7d
  output_dir: out
  html: false

fetch:
  user_agent: "{DEFAULT_USER_AGENT}"
  timeout_seconds: 30
  respect_robots: true
  min_interval_seconds: 1.0
  max_items_per_source: 40
"""


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def parse_sources(payload: Any) -> list[SourceSpec]:
    rows = payload.get("sources", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("sources file must be a list or a mapping with a 'sources' key")
    sources: list[SourceSpec] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each source must be a mapping")
        sources.append(
            SourceSpec(
                id=str(row["id"]),
                name=str(row.get("name") or row["id"]),
                kind=SourceKind(str(row["kind"])),
                url=row.get("url"),
                repo=row.get("repo"),
                selector=row.get("selector"),
                enabled=bool(row.get("enabled", True)),
                tags=list(row.get("tags") or []),
                notes=row.get("notes"),
            )
        )
    return sources


def _weights(raw: dict[str, Any]) -> ScoringSettings:
    weights = raw.get("weights") or {}
    boosts = raw.get("boosts") or {}
    return ScoringSettings(
        novelty=float(weights.get("novelty", 0.25)),
        impact=float(weights.get("impact", 0.30)),
        breadth=float(weights.get("breadth", 0.20)),
        recency=float(weights.get("recency", 0.25)),
        pricing_boost=float(boosts.get("pricing_change", 0.15)),
        deprecation_boost=float(boosts.get("deprecation", 0.15)),
        security_boost=float(boosts.get("security", 0.10)),
        recency_half_life_days=float(raw.get("recency_half_life_days", 7)),
        near_dup_threshold=float(raw.get("near_dup_threshold", 0.62)),
        cluster_threshold=float(raw.get("cluster_threshold", 0.28)),
    )


def load_config(path: Path | None) -> AppConfig:
    cfg = AppConfig(config_path=path)
    data: dict[str, Any] = {}
    if path and path.exists():
        data = load_yaml(path)
        root = path.parent
    else:
        root = Path.cwd()

    cfg.data_dir = Path(
        data.get("data_dir") or os.environ.get("SHIPWATCH_DATA_DIR") or cfg.data_dir
    )
    if not cfg.data_dir.is_absolute():
        cfg.data_dir = (root / cfg.data_dir).resolve() if path else Path.cwd() / cfg.data_dir

    sources_file = data.get("sources_file")
    inline = data.get("sources")
    if sources_file:
        src_path = Path(sources_file)
        if not src_path.is_absolute():
            src_path = root / src_path
        cfg.sources_file = src_path
        cfg.sources = parse_sources(load_yaml(src_path))
    elif inline:
        cfg.sources = parse_sources(inline)
    else:
        cfg.sources = parse_sources(load_yaml(bundled_sources_path()))

    llm = data.get("llm") or {}
    cfg.llm = LLMSettings(
        base_url=os.environ.get("SHIPWATCH_BASE_URL")
        or llm.get("base_url")
        or DEFAULT_FREEWHIRR_BASE,
        model=os.environ.get("SHIPWATCH_MODEL") or llm.get("model") or DEFAULT_FREEWHIRR_MODEL,
        api_key_env=llm.get("api_key_env") or "SHIPWATCH_API_KEY",
        timeout_seconds=float(llm.get("timeout_seconds", 60)),
        retries=int(llm.get("retries", 2)),
        temperature=float(llm.get("temperature", 0.2)),
    )
    cfg.scoring = _weights(data.get("scoring") or {})
    brief = data.get("brief") or {}
    cfg.brief = BriefSettings(
        top_n=int(brief.get("top_n", 12)),
        since=str(brief.get("since", "7d")),
        output_dir=Path(brief.get("output_dir") or "out"),
        html=bool(brief.get("html", False)),
    )
    if not cfg.brief.output_dir.is_absolute():
        cfg.brief.output_dir = (
            (root / cfg.brief.output_dir).resolve() if path else Path.cwd() / cfg.brief.output_dir
        )
    fetch = data.get("fetch") or {}
    cfg.fetch = FetchSettings(
        user_agent=fetch.get("user_agent") or DEFAULT_USER_AGENT,
        timeout_seconds=float(fetch.get("timeout_seconds", 30)),
        respect_robots=bool(fetch.get("respect_robots", True)),
        min_interval_seconds=float(fetch.get("min_interval_seconds", 1.0)),
        max_items_per_source=int(fetch.get("max_items_per_source", 40)),
        github_token_env=fetch.get("github_token_env") or "GITHUB_TOKEN",
    )
    return cfg


def write_init_files(directory: Path, *, force: bool = False) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    config_path = directory / "shipwatch.yaml"
    sources_path = directory / "sources.yaml"
    if config_path.exists() and not force:
        raise FileExistsError(f"{config_path} already exists (pass --force to overwrite)")
    config_path.write_text(default_config_text(), encoding="utf-8")
    written.append(config_path)
    pack = bundled_sources_path().read_text(encoding="utf-8")
    if sources_path.exists() and not force:
        raise FileExistsError(f"{sources_path} already exists (pass --force to overwrite)")
    sources_path.write_text(pack, encoding="utf-8")
    written.append(sources_path)
    return written
