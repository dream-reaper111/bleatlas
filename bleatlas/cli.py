"""BLEAtlas command line interface."""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys

from .core import normalize
from .hardware import capabilities
from .live import scan
from .storage import Inventory


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="bleatlas")
    parser.add_argument("--db", type=Path, default=Path("bleatlas.sqlite3"))
    parser.add_argument("--retention-days", type=int, default=7)
    parser.add_argument("--max-records", type=int, default=100_000)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("hardware")
    imp = sub.add_parser("import")
    imp.add_argument("path", type=Path)
    sub.add_parser("devices")
    auth = sub.add_parser("authorize")
    auth.add_argument("address")
    auth.add_argument("label")
    exp = sub.add_parser("export")
    exp.add_argument("format", choices=["json", "csv"])
    exp.add_argument("path", type=Path)
    live = sub.add_parser("scan")
    live.add_argument("--seconds", type=int, default=30)
    live.add_argument("--adapter")
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    if args.cmd == "hardware":
        print(json.dumps(capabilities(), indent=2))
        return 0
    try:
        db = Inventory(args.db, args.retention_days, args.max_records)
        if args.cmd == "import":
            if args.path.stat().st_size > 25_000_000:
                raise ValueError("input exceeds 25 MB")
            digest = hashlib.sha256(args.path.read_bytes()).hexdigest()
            count = 0
            with args.path.open() as stream:
                for line_no, line in enumerate(stream, 1):
                    if len(line) > 8192:
                        raise ValueError(f"line {line_no} exceeds limit")
                    if not line.strip():
                        continue
                    db.add(normalize(json.loads(line), f"{args.path.name}:sha256:{digest}"))
                    count += 1
            print(json.dumps({"imported": count, "sha256": digest}))
        elif args.cmd == "devices":
            print(json.dumps(db.devices(), indent=2))
        elif args.cmd == "authorize":
            db.authorize(args.address, args.label)
        elif args.cmd == "export":
            db.export(args.path, args.format)
        elif args.cmd == "scan":
            print(json.dumps({"observations": asyncio.run(scan(args.seconds, db, args.adapter))}))
        elif args.cmd == "serve":
            if args.host not in ("127.0.0.1", "::1", "localhost"):
                raise ValueError("dashboard is restricted to loopback")
            import uvicorn
            from .api import create_app
            uvicorn.run(create_app(args.db, args.retention_days, args.max_records), host=args.host, port=args.port)
        db.close()
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(f"bleatlas: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
