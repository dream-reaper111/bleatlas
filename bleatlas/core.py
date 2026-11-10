"""Bounded BLE advertisement parsing and cautious inventory analysis."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
import re
from statistics import median
from typing import Any

ADDRESS = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
UUID = re.compile(r"^[0-9a-fA-F]{4}$|^[0-9a-fA-F]{8}$|^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
MAX_AD = 1650
MAX_RECORD = 8192
COMPANIES = {0x004C: "Apple", 0x0006: "Microsoft", 0x0059: "Nordic Semiconductor", 0x00E0: "Google"}


def timestamp(value: str | None = None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return dt.astimezone(timezone.utc).isoformat()


def uuid_text(value: str) -> str:
    if not isinstance(value, str) or not UUID.fullmatch(value):
        raise ValueError("invalid service UUID")
    return value.lower()


def address_type(address: str, declared: str | None = None) -> str:
    if declared not in (None, "public", "random", "unknown"):
        raise ValueError("invalid address type")
    if declared:
        return declared
    # An address alone does not establish whether it is public or random.
    return "unknown"


def parse_ad(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_AD:
        raise ValueError("advertisement exceeds limit")
    out: dict[str, Any] = {"service_uuids": [], "manufacturer_data": {}, "service_data": {}, "name": None, "tx_power": None, "unknown_types": []}
    offset = 0
    while offset < len(raw):
        length = raw[offset]
        offset += 1
        if length == 0:
            break
        if offset + length > len(raw):
            raise ValueError("truncated AD structure")
        ad_type = raw[offset]
        data = raw[offset + 1:offset + length]
        offset += length
        if ad_type in (0x08, 0x09):
            out["name"] = data.decode("utf-8", "replace")[:128]
        elif ad_type in (0x02, 0x03, 0x04, 0x05, 0x06, 0x07):
            width = {0x02: 2, 0x03: 2, 0x04: 4, 0x05: 4, 0x06: 16, 0x07: 16}[ad_type]
            if len(data) % width:
                raise ValueError("invalid UUID list length")
            for i in range(0, len(data), width):
                chunk = data[i:i + width]
                if width == 16:
                    h = chunk[::-1].hex()
                    value = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
                else:
                    value = chunk[::-1].hex()
                out["service_uuids"].append(value)
        elif ad_type == 0x0A:
            if len(data) != 1:
                raise ValueError("invalid TX power length")
            out["tx_power"] = int.from_bytes(data, "little", signed=True)
        elif ad_type == 0xFF:
            if len(data) < 2:
                raise ValueError("manufacturer data missing company ID")
            company = int.from_bytes(data[:2], "little")
            out["manufacturer_data"][str(company)] = data[2:].hex()
        elif ad_type in (0x16, 0x20, 0x21):
            width = {0x16: 2, 0x20: 4, 0x21: 16}[ad_type]
            if len(data) < width:
                raise ValueError("service data missing UUID")
            chunk = data[:width][::-1].hex()
            if width == 16:
                chunk = f"{chunk[:8]}-{chunk[8:12]}-{chunk[12:16]}-{chunk[16:20]}-{chunk[20:]}"
            out["service_data"][chunk] = data[width:].hex()
        else:
            out["unknown_types"].append(ad_type)
    return out


def normalize(record: dict[str, Any], source: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("observation must be an object")
    if len(json.dumps(record, default=str)) > MAX_RECORD:
        raise ValueError("record exceeds limit")
    addr = record.get("address")
    if not isinstance(addr, str) or not ADDRESS.fullmatch(addr):
        raise ValueError("invalid Bluetooth address")
    rssi = record.get("rssi")
    if rssi is not None and (isinstance(rssi, bool) or not isinstance(rssi, (int, float)) or not -127 <= rssi <= 20):
        raise ValueError("invalid RSSI")
    raw_hex = record.get("raw_ad_hex")
    if raw_hex is not None and not isinstance(raw_hex, str):
        raise ValueError("raw AD must be hex text")
    parsed = parse_ad(bytes.fromhex(raw_hex)) if raw_hex is not None else {}
    supplied_uuids = record.get("service_uuids", parsed.get("service_uuids", []))
    if not isinstance(supplied_uuids, list):
        raise ValueError("service UUIDs must be a list")
    uuids = [uuid_text(x) for x in supplied_uuids]
    mfg = record.get("manufacturer_data", parsed.get("manufacturer_data", {}))
    if not isinstance(mfg, dict):
        raise ValueError("manufacturer data must be an object")
    clean_mfg = {}
    for key, value in mfg.items():
        try:
            company = int(key)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid company ID") from exc
        if not 0 <= company <= 65535 or not isinstance(value, str) or len(value) > 1024:
            raise ValueError("invalid manufacturer data")
        bytes.fromhex(value)
        clean_mfg[str(company)] = value.lower()
    name = record.get("name", parsed.get("name"))
    if name is not None and (not isinstance(name, str) or len(name) > 128):
        raise ValueError("invalid name")
    tx_power = record.get("tx_power", parsed.get("tx_power"))
    if tx_power is not None and (not isinstance(tx_power, int) or not -127 <= tx_power <= 127):
        raise ValueError("invalid TX power")
    capture_kind = record.get("capture_kind", "advertisement_observation")
    if capture_kind not in ("advertisement_observation", "host_advertisement_event"):
        raise ValueError("unsupported capture kind")
    return {
        "timestamp": timestamp(record.get("timestamp")), "address": addr.upper(),
        "address_type": address_type(addr, record.get("address_type")),
        "name": name, "service_uuids": sorted(set(uuids)),
        "manufacturer_data": clean_mfg,
        "manufacturer_names": sorted({COMPANIES.get(int(k), f"Unknown company {k}") for k in clean_mfg}),
        "rssi": rssi, "tx_power": tx_power,
        "source": source[:256], "capture_kind": capture_kind,
    }


def summarize(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[(record["address"], record["address_type"])].append(record)
    results = []
    for (addr, kind), items in groups.items():
        items.sort(key=lambda x: x["timestamp"])
        intervals = []
        for a, b in zip(items, items[1:]):
            delta = (datetime.fromisoformat(b["timestamp"]) - datetime.fromisoformat(a["timestamp"])).total_seconds()
            if 0 < delta <= 3600:
                intervals.append(delta)
        fingerprints = {json.dumps([x["name"], x["service_uuids"], x["manufacturer_data"], x["tx_power"]], sort_keys=True) for x in items}
        rssis = [x["rssi"] for x in items if x["rssi"] is not None]
        results.append({"address": addr, "address_type": kind, "first_seen": items[0]["timestamp"],
                        "last_seen": items[-1]["timestamp"], "observations": len(items),
                        "name": items[-1]["name"], "service_uuids": items[-1]["service_uuids"],
                        "manufacturer_names": items[-1]["manufacturer_names"],
                        "rssi_median_dbm": median(rssis) if rssis else None,
                        "observed_gap_median_seconds": median(intervals) if intervals else None,
                        "advertisement_changed": len(fingerprints) > 1})
    return sorted(results, key=lambda x: x["last_seen"], reverse=True)
