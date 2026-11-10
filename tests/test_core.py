import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import asyncio

from bleatlas.core import normalize, parse_ad, summarize
from bleatlas.storage import Inventory
from bleatlas.hardware import capabilities
from bleatlas.cli import main
from bleatlas.live import scan


ADDRESS = "AA:BB:CC:DD:EE:FF"


class BLEAtlasTests(unittest.TestCase):
    def test_parse_ad(self):
        raw = bytes.fromhex("02010603030d1805095465737405ff4c000102020afc")
        parsed = parse_ad(raw)
        self.assertEqual(parsed["service_uuids"], ["180d"])
        self.assertEqual(parsed["name"], "Test")
        self.assertEqual(parsed["manufacturer_data"], {"76": "0102"})
        self.assertEqual(parsed["tx_power"], -4)

    def test_malformed(self):
        for raw in (b"\x05\x09x", b"\x02\xff\x01", b"\x02\x0a"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_ad(raw)
        with self.assertRaises(ValueError):
            normalize({"address": ADDRESS, "service_uuids": ["bogus"]}, "fixture")
        with self.assertRaises(ValueError):
            normalize({"address": ADDRESS, "raw_ad_hex": "xyz"}, "fixture")

    def test_summary_and_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Inventory(Path(directory) / "db.sqlite", max_records=2)
            one = normalize({"address": ADDRESS, "timestamp": "2026-11-09T12:00:00Z", "name": "A", "rssi": -60}, "fixture")
            two = normalize({"address": ADDRESS, "timestamp": "2026-11-09T12:00:01Z", "name": "B", "rssi": -70}, "fixture")
            # Fixed old timestamps are valid parser fixtures, but retention prunes them.
            report = summarize([one, two])[0]
            self.assertTrue(report["advertisement_changed"])
            self.assertEqual(report["observed_gap_median_seconds"], 1)
            for name in ("A", "B", "C"):
                db.add(normalize({"address": ADDRESS, "name": name}, "fixture"))
            self.assertEqual(len(db.records()), 2)
            db.authorize(ADDRESS, "Lab sensor")
            self.assertEqual(db.devices()[0]["authorized_label"], "Lab sensor")
            db.export(Path(directory) / "out.csv", "csv")
            self.assertIn("Lab sensor", (Path(directory) / "out.csv").read_text())
            db.close()

    def test_hardware_and_offline_cli(self):
        self.assertTrue(any(x["kind"] == "offline_capture_import" and x["available"] for x in capabilities()))
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            source = p / "observations.jsonl"
            source.write_text(json.dumps({"address": ADDRESS, "rssi": -55}) + "\n")
            self.assertEqual(main(["--db", str(p / "db.sqlite"), "import", str(source)]), 0)
            self.assertEqual(main(["--db", str(p / "db.sqlite"), "export", "json", str(p / "out.json")]), 0)
            self.assertEqual(json.loads((p / "out.json").read_text())[0]["address"], ADDRESS)

    def test_live_unavailable_and_bounds(self):
        with self.assertRaisesRegex(ValueError, "duration"):
            asyncio.run(scan(301, None))
        with patch.dict("sys.modules", {"bleak": None}):
            with self.assertRaisesRegex(RuntimeError, "requires bleak"):
                asyncio.run(scan(1, None))
        with self.assertRaises(ValueError):
            normalize([1, 2], "fixture")


if __name__ == "__main__":
    unittest.main()
