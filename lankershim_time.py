"""Explicit temporal partitioning for the inspected Lankershim API export."""

from decimal import Decimal, InvalidOperation


FRAME_INTERVAL_MS = 100
CALIBRATION_ORIGIN_MS = 1118935680000
EVALUATION_ORIGIN_MS = 1118936700000
CALIBRATION_START_MS = 1118935800000
SPLIT_MS = 1118936700000
EVALUATION_END_MS = 1118937600000


def integer_field(row, field):
    try:
        value = Decimal(str(row[field]))
    except (KeyError, InvalidOperation) as error:
        raise ValueError(f"Missing or invalid {field}") from error
    if not value.is_finite() or value != value.to_integral_value():
        raise ValueError(f"Expected finite integer {field}")
    return int(value)


def frame_origin(row):
    timestamp = integer_field(row, "global_time")
    frame = integer_field(row, "frame_id")
    if frame < 1:
        raise ValueError("Frame numbering must start at one")
    origin = timestamp - FRAME_INTERVAL_MS * (frame - 1)
    if origin not in (CALIBRATION_ORIGIN_MS, EVALUATION_ORIGIN_MS):
        raise ValueError("Unrecognized frame origin; re-audit source before ingestion")
    return origin


def track_key(row):
    return frame_origin(row), integer_field(row, "vehicle_id")


def partition(row):
    origin = frame_origin(row)
    timestamp = integer_field(row, "global_time")
    if origin == CALIBRATION_ORIGIN_MS and CALIBRATION_START_MS <= timestamp < SPLIT_MS:
        return "calibration"
    if origin == EVALUATION_ORIGIN_MS and SPLIT_MS <= timestamp < EVALUATION_END_MS:
        return "evaluation"
    return "excluded"
