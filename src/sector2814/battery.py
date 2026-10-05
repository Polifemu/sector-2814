"""The Central Battery: findings store and round history (SQLite, stdlib only)."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEVERITIES = ("green", "yellow", "red", "black")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Finding:
    plugin: str
    severity: str
    title: str
    detail: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    subject: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    round_id: str = ""
    ts: str = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Battery:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS findings (
                id       TEXT PRIMARY KEY,
                round_id TEXT NOT NULL,
                ts       TEXT NOT NULL,
                plugin   TEXT NOT NULL,
                severity TEXT NOT NULL,
                title    TEXT NOT NULL,
                detail   TEXT NOT NULL DEFAULT '',
                evidence TEXT NOT NULL DEFAULT '{}',
                subject  TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS rounds (
                round_id TEXT PRIMARY KEY,
                started  TEXT NOT NULL,
                finished TEXT,
                severity TEXT NOT NULL DEFAULT 'green',
                summary  TEXT NOT NULL DEFAULT ''
            );
            """
        )
        self.conn.commit()

    def start_round(self, round_id: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO rounds (round_id, started) VALUES (?, ?)",
            (round_id, utcnow()),
        )
        self.conn.commit()

    def finish_round(self, round_id: str, severity: str, summary: str) -> None:
        self.conn.execute(
            "UPDATE rounds SET finished = ?, severity = ?, summary = ? WHERE round_id = ?",
            (utcnow(), severity, summary, round_id),
        )
        self.conn.commit()

    def add_finding(self, finding: Finding) -> None:
        self.conn.execute(
            """
            INSERT INTO findings
                (id, round_id, ts, plugin, severity, title, detail, evidence, subject)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                finding.id,
                finding.round_id,
                finding.ts,
                finding.plugin,
                finding.severity,
                finding.title,
                finding.detail,
                json.dumps(finding.evidence, ensure_ascii=False),
                json.dumps(finding.subject, ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM findings ORDER BY ts DESC, rowid DESC LIMIT ?", (limit,)
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["evidence"] = json.loads(item["evidence"])
            item["subject"] = json.loads(item["subject"])
            out.append(item)
        return out
