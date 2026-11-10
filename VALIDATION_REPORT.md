# Validation report

Date: 2026-11-09. Python 3.12.3. `compileall` passed. `unittest` passed 5 tests, 0 failed, 0 skipped: AD parsing, malformed AD/UUID handling, storage bounds and change analysis, hardware capability shape, offline CLI import/export, and unavailable Bleak behavior. Ruff could not run because it is not installed. Bleak is unavailable, so live scanning was not tested. FastAPI is installed, but no process-level dashboard test has been run.

Hardware discovery: `/sys/class/bluetooth/hci0` exists, but HCI socket and management socket access were denied; `bluetoothctl list` could not connect to D-Bus. `lsusb` could not initialize libusb. No SDR or rtl_433 command was found. Therefore no BLE or RF hardware is verified usable. No live capture or simulated capture was claimed.

Known limits: offline JSONL is a normalized observation format, not a native capture parser; manufacturer company names are a small static map; BlueZ/Bleak may not reveal address type; capture gaps are not advertising interval measurements; SQLite is single-user; the dashboard is local only; no live adapter disconnection test was possible. Next: validate with an authorized adapter and sanitized real observations, expand company registry coverage, and add a measured event stream test for disconnect behavior.
