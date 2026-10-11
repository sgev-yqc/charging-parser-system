"""Order persistence checks that do not start Streamlit."""

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from charging_parser.config import get_data_dir
from charging_parser.storage import OrderStore, extract_order_id


class StorageTest(unittest.TestCase):
    def test_replacement_keeps_previous_order_when_parsing_fails(self):
        sample = b"2026-01-01 00:00:00.000 1826f456 01 02 03\n"
        with TemporaryDirectory() as temporary:
            store = OrderStore(Path(temporary) / "orders")
            original = store.add_order("sample", "first.txt", sample)
            with patch("charging_parser.storage.parse_file_content", side_effect=ValueError("bad frame")):
                with self.assertRaises(ValueError):
                    store.add_order("sample", "replacement.txt", b"invalid")
            self.assertEqual(store.load_orders()["sample"], original)
            self.assertEqual(Path(original["original_file"]).read_bytes(), sample)

            replacement = store.add_order("sample", "replacement.txt", sample)
            self.assertEqual(Path(replacement["original_file"]).read_bytes(), sample)
            self.assertFalse(Path(original["original_file"]).exists())

    def test_configured_directory_and_order_lifecycle(self):
        sample = b"2026-01-01 00:00:00.000 1826f456 01 02 03\n"
        with TemporaryDirectory() as temporary:
            data_dir = Path(temporary) / "orders"
            with patch.dict(os.environ, {"CHARGING_PARSER_DATA_DIR": str(data_dir)}):
                store = OrderStore(get_data_dir())
            self.assertFalse(data_dir.exists())
            self.assertEqual(extract_order_id("BMS_20260101_sample.2.txt"), "sample")
            self.assertEqual(extract_order_id("37417900000036460025010502684421.3_corrected.txt"), "37417900000036460025010502684421.3_corrected.txt")
            self.assertEqual(extract_order_id("37417900000036460025010502684421.3.txt"), "37417900000036460025010502684421.3.txt")
            self.assertEqual(extract_order_id("3741790000000329_1_26.3_corrected.txt"), "3741790000000329_1_26.3_corrected.txt")
            self.assertEqual(extract_order_id("BMS_20260101_.txt"), "BMS_20260101_.txt")

            order = store.add_order("sample", "sample.txt", sample)
            self.assertEqual(order["message_count"], 1)
            self.assertEqual(store.load_orders()["sample"], order)
            self.assertEqual(Path(order["original_file"]).read_bytes(), sample)
            results = json.loads(Path(order["result_file"]).read_text(encoding="utf-8"))
            self.assertEqual(results[0]["name"], "CHM")

            self.assertTrue(store.delete_order("sample"))
            self.assertEqual(store.load_orders(), {})
            self.assertFalse(Path(order["original_file"]).exists())
            self.assertFalse(store.delete_order("sample"))


if __name__ == "__main__":
    unittest.main()
