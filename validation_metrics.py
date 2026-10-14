"""Score already aligned observation/model series; does not establish data provenance."""

import math


def score_series(observed, predicted):
    if len(observed) != len(predicted) or not observed:
        raise ValueError("Require nonempty, equally sized aligned series")
    if any(not math.isfinite(value) for value in (*observed, *predicted)):
        raise ValueError("Missing or nonfinite values require explicit preprocessing")
    residuals = [estimate - reference for reference, estimate in zip(observed, predicted)]
    count = len(residuals)
    return {
        "count": count,
        "mae": sum(abs(value) for value in residuals) / count,
        "rmse": math.sqrt(sum(value * value for value in residuals) / count),
        "bias": sum(residuals) / count,
    }
