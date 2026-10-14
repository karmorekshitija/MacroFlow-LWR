import io
import unittest
from unittest.mock import patch

from probe_lankershim import fetch_query


class DataProbeTests(unittest.TestCase):
    def test_preserves_payload_and_encodes_query(self):
        payload = b'[{"vehicle_id":"1"}]'
        with patch("probe_lankershim.urllib.request.urlopen", return_value=io.BytesIO(payload)):
            url, actual, rows = fetch_query("SELECT * LIMIT 1")
        self.assertIn("%24query=SELECT", url)
        self.assertEqual(actual, payload)
        self.assertEqual(rows, [{"vehicle_id": "1"}])

    def test_rejects_non_list_and_oversized_payloads(self):
        for payload in (b'{"error":"invalid query"}', b" " * (2 * 1024 * 1024 + 1)):
            with self.subTest(size=len(payload)):
                with patch("probe_lankershim.urllib.request.urlopen", return_value=io.BytesIO(payload)):
                    with self.assertRaises(ValueError):
                        fetch_query("SELECT * LIMIT 1")
