"""SQLite archive for items, facts, clusters, briefings, and fetch state."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from shipwatch.dates import isoformat, parse_datetime
from shipwatch.models import Briefing, Cluster, Fact, Item, ItemKind

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    published_at TEXT,
    content TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'other',
    tags TEXT NOT NULL DEFAULT '[]',
    cluster_id TEXT,
    score REAL NOT NULL DEFAULT 0,
    score_breakdown TEXT NOT NULL DEFAULT '{}',
    duplicate_of TEXT,
    fetched_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_source ON items(source_id);
CREATE INDEX IF NOT EXISTS idx_items_published ON items(published_at);

CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    text TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'other',
    evidence TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(item_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS clusters (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    item_ids TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS briefings (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    since_label TEXT NOT NULL,
    window_start TEXT NOT NULL,
    mode TEXT NOT NULL,
    payload TEXT NOT NULL,
    coverage TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fetch_state (
    source_id TEXT PRIMARY KEY,
    etag TEXT,
    last_modified TEXT,
    last_fetch TEXT,
    last_status INTEGER,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS seen_urls (
    source_id TEXT NOT NULL,
    url TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    PRIMARY KEY (source_id, url)
);
"""


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def upsert_item(self, item: Item, *, fetched_at: datetime) -> bool:
        existing = self.conn.execute("SELECT id FROM items WHERE id = ?", (item.id,)).fetchone()
        self.conn.execute(
            """
            INSERT INTO items (
                id, source_id, source_name, url, title, published_at, content, summary,
                kind, tags, cluster_id, score, score_breakdown, duplicate_of, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                published_at = excluded.published_at,
                content = excluded.content,
                summary = excluded.summary,
                kind = excluded.kind,
                tags = excluded.tags,
                cluster_id = excluded.cluster_id,
                score = excluded.score,
                score_breakdown = excluded.score_breakdown,
                duplicate_of = excluded.duplicate_of,
                fetched_at = excluded.fetched_at
            """,
            (
                item.id,
                item.source_id,
                item.source_name,
                item.url,
                item.title,
                isoformat(item.published_at),
                item.content,
                item.summary,
                item.kind.value,
                json.dumps(item.tags),
                item.cluster_id,
                item.score,
                json.dumps(item.score_breakdown),
                item.duplicate_of,
                isoformat(fetched_at),
            ),
        )
        self.conn.commit()
        return existing is None

    def update_item(self, item: Item) -> None:
        self.upsert_item(
            item, fetched_at=parse_datetime(self._fetched_at(item.id)) or datetime.now()
        )

    def _fetched_at(self, item_id: str) -> str | None:
        row = self.conn.execute("SELECT fetched_at FROM items WHERE id = ?", (item_id,)).fetchone()
        return row["fetched_at"] if row else None

    def get_item(self, item_id: str) -> Item | None:
        row = self.conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return _item_from_row(row) if row else None

    def items_since(
        self,
        start: datetime,
        *,
        until: datetime | None = None,
        include_duplicates: bool = False,
    ) -> list[Item]:
        rows = self.conn.execute(
            """
            SELECT * FROM items
            WHERE published_at IS NOT NULL
              AND published_at >= ?
              AND (? IS NULL OR published_at <= ?)
            ORDER BY published_at DESC
            """,
            (isoformat(start), isoformat(until), isoformat(until)),
        ).fetchall()
        items = [_item_from_row(r) for r in rows]
        if include_duplicates:
            return items
        return [i for i in items if not i.duplicate_of]

    def replace_facts(self, item_id: str, facts: list[Fact]) -> None:
        self.conn.execute("DELETE FROM facts WHERE item_id = ?", (item_id,))
        for fact in facts:
            self.conn.execute(
                "INSERT INTO facts (id, item_id, text, kind, evidence) VALUES (?, ?, ?, ?, ?)",
                (fact.id, fact.item_id, fact.text, fact.kind.value, fact.evidence),
            )
        self.conn.commit()

    def facts_for(self, item_ids: list[str]) -> list[Fact]:
        if not item_ids:
            return []
        placeholders = ",".join("?" * len(item_ids))
        rows = self.conn.execute(
            f"SELECT * FROM facts WHERE item_id IN ({placeholders})",
            item_ids,
        ).fetchall()
        return [
            Fact(
                id=r["id"],
                item_id=r["item_id"],
                text=r["text"],
                kind=ItemKind(r["kind"]),
                evidence=r["evidence"],
            )
            for r in rows
        ]

    def replace_clusters(self, clusters: list[Cluster], *, created_at: datetime) -> None:
        self.conn.execute("DELETE FROM clusters")
        for cluster in clusters:
            self.conn.execute(
                """INSERT INTO clusters (id, topic, item_ids, score, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    cluster.id,
                    cluster.topic,
                    json.dumps(cluster.item_ids),
                    cluster.score,
                    isoformat(created_at),
                ),
            )
        self.conn.commit()

    def save_briefing(self, briefing: Briefing) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO briefings (
                id, title, generated_at, since_label, window_start, mode, payload, coverage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                briefing.id,
                briefing.title,
                isoformat(briefing.generated_at),
                briefing.since,
                isoformat(briefing.window_start),
                briefing.mode,
                briefing.model_dump_json(),
                briefing.coverage.model_dump_json(),
            ),
        )
        self.conn.commit()

    def list_briefings(self, limit: int = 20) -> list[Briefing]:
        rows = self.conn.execute(
            "SELECT payload FROM briefings ORDER BY generated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [Briefing.model_validate_json(r["payload"]) for r in rows]

    def latest_briefing(self) -> Briefing | None:
        rows = self.list_briefings(limit=1)
        return rows[0] if rows else None

    def get_fetch_state(self, source_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM fetch_state WHERE source_id = ?", (source_id,)
        ).fetchone()
        return dict(row) if row else {}

    def set_fetch_state(
        self,
        source_id: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
        last_fetch: datetime | None = None,
        last_status: int | None = None,
        last_error: str | None = None,
    ) -> None:
        prev = self.get_fetch_state(source_id)
        self.conn.execute(
            """
            INSERT INTO fetch_state (
                source_id, etag, last_modified, last_fetch, last_status, last_error
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                etag = excluded.etag,
                last_modified = excluded.last_modified,
                last_fetch = excluded.last_fetch,
                last_status = excluded.last_status,
                last_error = excluded.last_error
            """,
            (
                source_id,
                etag if etag is not None else prev.get("etag"),
                last_modified if last_modified is not None else prev.get("last_modified"),
                isoformat(last_fetch) if last_fetch else prev.get("last_fetch"),
                last_status if last_status is not None else prev.get("last_status"),
                last_error,
            ),
        )
        self.conn.commit()

    def seen_urls(self, source_id: str) -> set[str]:
        rows = self.conn.execute(
            "SELECT url FROM seen_urls WHERE source_id = ?", (source_id,)
        ).fetchall()
        return {r["url"] for r in rows}

    def mark_seen(self, source_id: str, urls: list[str], *, first_seen: datetime) -> None:
        for url in urls:
            self.conn.execute(
                "INSERT OR IGNORE INTO seen_urls (source_id, url, first_seen) VALUES (?, ?, ?)",
                (source_id, url, isoformat(first_seen)),
            )
        self.conn.commit()

    def stats(self) -> dict[str, Any]:
        item_count = self.conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        fact_count = self.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        briefing_count = self.conn.execute("SELECT COUNT(*) FROM briefings").fetchone()[0]
        sources = self.conn.execute(
            "SELECT source_id, COUNT(*) AS n FROM items GROUP BY source_id ORDER BY n DESC"
        ).fetchall()
        latest = self.latest_briefing()
        return {
            "items": item_count,
            "facts": fact_count,
            "briefings": briefing_count,
            "by_source": {r["source_id"]: r["n"] for r in sources},
            "latest_briefing": latest.id if latest else None,
            "latest_coverage": latest.coverage.model_dump() if latest else None,
        }


def _item_from_row(row: sqlite3.Row) -> Item:
    return Item(
        id=row["id"],
        source_id=row["source_id"],
        source_name=row["source_name"],
        url=row["url"],
        title=row["title"],
        published_at=parse_datetime(row["published_at"]),
        content=row["content"],
        summary=row["summary"],
        kind=ItemKind(row["kind"]),
        tags=json.loads(row["tags"] or "[]"),
        cluster_id=row["cluster_id"],
        score=row["score"] or 0.0,
        score_breakdown=json.loads(row["score_breakdown"] or "{}"),
        duplicate_of=row["duplicate_of"],
    )
