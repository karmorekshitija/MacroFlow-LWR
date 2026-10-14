import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validation_metrics import score_series


class ValidationMetricTests(unittest.TestCase):
    def test_hand_computed_errors(self):
        scores = score_series([1.0, 3.0], [2.0, 1.0])
        self.assertEqual(scores["count"], 2)
        self.assertEqual(scores["mae"], 1.5)
        self.assertAlmostEqual(scores["rmse"], 2.5 ** 0.5)
        self.assertEqual(scores["bias"], -0.5)

    def test_invalid_series_fail_instead_of_silent_filtering(self):
        for observed, predicted in (([], []), ([1], []), ([float("nan")], [1]), ([1], [float("inf")])):
            with self.subTest(observed=observed, predicted=predicted):
                with self.assertRaises(ValueError):
                    score_series(observed, predicted)
