"""Local bounded observation storage."""

import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

from .core import summarize


class Inventory:
    def __init__(self, path: Path, retention_days: int = 7, max_records: int = 100_000):
        if not 1 <= retention_days <= 365 or not 1 <= max_records <= 1_000_000:
            raise ValueError("retention or record limit out of range")
        self.path = path
        self.retention_days = retention_days
        self.max_records = max_records
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, address TEXT NOT NULL, data TEXT NOT NULL)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_observations_ts ON observations(ts)")
        self.db.execute("CREATE TABLE IF NOT EXISTS authorized (address TEXT PRIMARY KEY, label TEXT NOT NULL)")
        self.db.commit()

    def add(self, record: dict) -> None:
        self.prune()
        self.db.execute("INSERT INTO observations(ts,address,data) VALUES(?,?,?)", (record["timestamp"], record["address"], json.dumps(record, sort_keys=True)))
        self.db.commit()
        self.prune()

    def prune(self) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        self.db.execute("DELETE FROM observations WHERE ts < ?", (cutoff,))
        self.db.execute("DELETE FROM observations WHERE id NOT IN (SELECT id FROM observations ORDER BY id DESC LIMIT ?)", (self.max_records,))
        self.db.commit()

    def records(self, limit: int = 10_000) -> list[dict]:
        if not 1 <= limit <= 100_000:
            raise ValueError("invalid query limit")
        self.prune()
        return [json.loads(row[0]) for row in self.db.execute("SELECT data FROM observations ORDER BY ts DESC LIMIT ?", (limit,))]

    def authorize(self, address: str, label: str) -> None:
        from .core import ADDRESS
        if not ADDRESS.fullmatch(address) or not 1 <= len(label) <= 128:
            raise ValueError("invalid authorized device")
        self.db.execute("INSERT OR REPLACE INTO authorized VALUES (?,?)", (address.upper(), label))
        self.db.commit()

    def devices(self) -> list[dict]:
        labels = dict(self.db.execute("SELECT address,label FROM authorized"))
        devices = summarize(self.records())
        for item in devices:
            item["authorized_label"] = labels.get(item["address"])
        return devices

    def export(self, path: Path, fmt: str) -> None:
        devices = self.devices()
        if fmt == "json":
            path.write_text(json.dumps(devices, indent=2) + "\n")
        elif fmt == "csv":
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(devices[0]) if devices else ["address"])
                writer.writeheader()
                for device in devices:
                    writer.writerow(device)
        else:
            raise ValueError("unsupported export format")

    def close(self) -> None:
        self.db.close()
