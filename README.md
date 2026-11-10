# BLEAtlas

BLEAtlas inventories BLE advertisement observations for authorized research. It works offline from bounded JSONL input and can scan through Bleak/BlueZ when adapter access is available. The loopback dashboard displays inventory and change indicators. Observed gaps between events are **not** verified advertising intervals, and RSSI is **not** a distance estimate.

## Quick start

Python 3.12 is required. From this directory:

```sh
python3 -m bleatlas.cli hardware
python3 -m bleatlas.cli --db inventory.sqlite3 import authorized-observations.jsonl
python3 -m bleatlas.cli --db inventory.sqlite3 devices
python3 -m bleatlas.cli --db inventory.sqlite3 export csv inventory.csv
```

Optional live scan: install `pip install -e '.[live]'`, then run `python3 -m bleatlas.cli --db inventory.sqlite3 scan --seconds 30`. Optional dashboard: install `pip install -e '.[dashboard]'`, then run `python3 -m bleatlas.cli --db inventory.sqlite3 serve` and open `http://127.0.0.1:8080`. Scans are limited to 300 seconds. The dashboard binds only to loopback.

One input line is a JSON object such as `{"timestamp":"2026-11-09T12:00:00Z","address":"AA:BB:CC:DD:EE:FF","address_type":"unknown","rssi":-55,"raw_ad_hex":"02010603030d18"}`. Alternatively supply `name`, `service_uuids`, `manufacturer_data` (company ID to hex bytes), and `tx_power`. Input is capped at 25 MB and 8192 characters per line. An import stores the input SHA-256 in each observation's provenance. Exported reports include addresses; handle them as sensitive data.

Default retention is seven days and 100,000 observations. Set `--retention-days` and `--max-records` before the subcommand. `authorize ADDRESS LABEL` adds a locally approved label. It does not grant wireless access or infer ownership. Each scan should be scoped to an authorized location and purpose. Random addresses are recorded as observed; BLEAtlas does not link them to identities.

See [ARCHITECTURE.md](ARCHITECTURE.md), [SECURITY.md](SECURITY.md), [HARDWARE.md](HARDWARE.md), [DEPENDENCIES.md](DEPENDENCIES.md), and [VALIDATION_REPORT.md](VALIDATION_REPORT.md).
