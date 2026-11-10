"""Truthful capability discovery for the local environment."""

from pathlib import Path
import socket


def capabilities() -> list[dict]:
    result = []
    for path in sorted(Path("/sys/class/bluetooth").glob("hci*")):
        usable = False
        detail = "HCI socket unavailable"
        try:
            sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI)
            sock.close()
            usable = True
            detail = "HCI socket accessible; BlueZ scan requires separate verification"
        except (OSError, AttributeError):
            pass
        result.append({"device": path.name, "kind": "local_ble_adapter", "available": usable,
                       "detail": detail, "frequency_range_hz": [2400000000, 2483500000],
                       "sample_rate_limits": None, "operations": ["BLE scan via BlueZ/Bleak"] if usable else [],
                       "required_permissions": ["BlueZ D-Bus scan access"], "driver_dependencies": ["BlueZ", "Bleak"]})
    if not result:
        result.append({"device": None, "kind": "local_ble_adapter", "available": False,
                       "detail": "no HCI adapter found", "frequency_range_hz": None, "sample_rate_limits": None,
                       "operations": [], "required_permissions": ["BlueZ D-Bus scan access"], "driver_dependencies": ["BlueZ", "Bleak"]})
    result.append({"device": None, "kind": "dedicated_ble_sniffer", "available": False,
                   "detail": "BLEAtlas has no over-the-air sniffer integration", "frequency_range_hz": None,
                   "sample_rate_limits": None, "operations": [], "required_permissions": [], "driver_dependencies": []})
    result.append({"device": None, "kind": "receive_only_sdr", "available": False,
                   "detail": "not a BLEAtlas input", "frequency_range_hz": None, "sample_rate_limits": None,
                   "operations": [], "required_permissions": [], "driver_dependencies": []})
    result.append({"device": "JSONL", "kind": "offline_capture_import", "available": True,
                   "detail": "bounded advertisement observation JSONL", "frequency_range_hz": None,
                   "sample_rate_limits": None, "operations": ["import", "analyze"], "required_permissions": ["file read"], "driver_dependencies": []})
    return result
