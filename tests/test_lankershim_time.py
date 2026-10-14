import unittest

from lankershim_time import (
    CALIBRATION_ORIGIN_MS, CALIBRATION_START_MS, EVALUATION_END_MS,
    EVALUATION_ORIGIN_MS, SPLIT_MS, frame_origin, partition, track_key,
)


def make_row(origin, timestamp, vehicle=1):
    return {"global_time": str(timestamp), "frame_id": str((timestamp-origin)//100+1), "vehicle_id": str(vehicle)}


class TemporalPartitionTests(unittest.TestCase):
    def test_half_open_boundaries(self):
        for timestamp, expected in [(CALIBRATION_START_MS-100, "excluded"), (CALIBRATION_START_MS, "calibration"), (SPLIT_MS-100, "calibration"), (SPLIT_MS, "excluded")]:
            self.assertEqual(partition(make_row(CALIBRATION_ORIGIN_MS, timestamp)), expected)
        self.assertEqual(partition(make_row(EVALUATION_ORIGIN_MS, SPLIT_MS)), "evaluation")
        self.assertEqual(partition(make_row(EVALUATION_ORIGIN_MS, EVALUATION_END_MS)), "excluded")

    def test_overlapping_groups_are_not_mixed(self):
        earlier = make_row(CALIBRATION_ORIGIN_MS, SPLIT_MS+100)
        later = make_row(EVALUATION_ORIGIN_MS, SPLIT_MS+100)
        self.assertEqual(partition(earlier), "excluded")
        self.assertEqual(partition(later), "evaluation")
        self.assertNotEqual(track_key(earlier), track_key(later))

    def test_invalid_frames_and_unknown_origins_fail_closed(self):
        for frame in ("0", "1.5", "NaN", "Infinity", "bad"):
            with self.subTest(frame=frame), self.assertRaises(ValueError):
                frame_origin({"global_time": str(SPLIT_MS), "frame_id": frame})
        with self.assertRaises(ValueError):
            frame_origin(make_row(EVALUATION_ORIGIN_MS+1, SPLIT_MS+1))
