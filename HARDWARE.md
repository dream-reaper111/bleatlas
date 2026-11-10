# Hardware support

Run `python3 -m bleatlas.cli hardware` for current capability reporting. A Linux HCI adapter plus accessible BlueZ D-Bus and optional Bleak are required for live scanning. Adapter enumeration through `/sys/class/bluetooth` does not prove that scanning is permitted. The scan command reports errors if BlueZ is unavailable or access is denied. USB adapters supported by BlueZ may work through the same interface, but none was validated in this environment. Nordic nRF52840 sniffers and SDR devices are not integrated into BLEAtlas. Offline JSONL import requires no wireless hardware.

Reported adapter frequency range describes the BLE band, not measured receiver tuning limits. No sample rate applies to the HCI adapter. BLEAtlas does not treat HCI monitoring as over-the-air capture. RTL-SDR is not presumed capable of BLE reception at 2.4 GHz.
