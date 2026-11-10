"""Optional Bleak/BlueZ live scanning; advertisement events are not OTA captures."""

import asyncio
from datetime import datetime, timezone

from .core import normalize


async def scan(seconds: int, inventory, adapter: str | None = None) -> int:
    if not 1 <= seconds <= 300:
        raise ValueError("scan duration must be 1 to 300 seconds")
    try:
        from bleak import BleakScanner
    except ImportError as exc:
        raise RuntimeError("live scanning requires bleak") from exc
    count = 0

    def callback(device, advertisement):
        nonlocal count
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "address": device.address,
                  "address_type": "unknown", "name": advertisement.local_name or device.name,
                  "service_uuids": advertisement.service_uuids or [],
                  "manufacturer_data": {str(k): v.hex() for k, v in advertisement.manufacturer_data.items()},
                  "rssi": advertisement.rssi, "tx_power": advertisement.tx_power,
                  "capture_kind": "host_advertisement_event"}
        try:
            inventory.add(normalize(record, "Bleak/BlueZ"))
            count += 1
        except ValueError:
            pass

    scanner = BleakScanner(detection_callback=callback, adapter=adapter) if adapter else BleakScanner(detection_callback=callback)
    try:
        async with scanner:
            await asyncio.sleep(seconds)
    except Exception as exc:
        raise RuntimeError(f"BlueZ scan failed: {exc}") from exc
    return count
