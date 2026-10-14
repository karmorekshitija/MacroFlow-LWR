import unittest

from ingest_lankershim import audit_rows
from lankershim_time import CALIBRATION_ORIGIN_MS, CALIBRATION_START_MS


class IngestionTests(unittest.TestCase):
    def test_counts_duplicate_keys_and_gaps(self):
        def row(timestamp):
            return {"vehicle_id": "1", "global_time": str(timestamp),
                    "frame_id": str((timestamp-CALIBRATION_ORIGIN_MS)//100+1),
                    "movement": "1", "v_vel": "0"}
        result = audit_rows([row(CALIBRATION_START_MS), row(CALIBRATION_START_MS), row(CALIBRATION_START_MS+300)])
        self.assertEqual(result["rows"], 3)
        self.assertEqual(result["duplicate_track_time_keys"], 1)
        self.assertEqual(result["within_subset_gaps_over_100ms"], 1)
        self.assertEqual(result["partitions"], {"calibration": 3})
