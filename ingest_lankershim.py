"""Acquire and audit a complete API section subset; never infer signal phases."""

import csv
import hashlib
import io
import json
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from lankershim_time import partition, track_key
from probe_lankershim import fetch_query


BASE = Path(__file__).resolve().parent
FILTER = "location='lankershim' AND direction='2' AND section_id='3'"
FIELDS = "vehicle_id,frame_id,global_time,local_x,local_y,v_vel,lane_id,movement,o_zone,d_zone,direction,section_id,int_id"
QUERY = f"SELECT {FIELDS} WHERE {FILTER} ORDER BY global_time,vehicle_id,frame_id LIMIT 1000000"
URL = "https://data.transportation.gov/resource/8ect-6jqj.csv?" + urllib.parse.urlencode({"$query": QUERY})


def audit_rows(rows):
    partitions = Counter()
    movements = Counter()
    keys = set()
    tracks = defaultdict(list)
    duplicates = 0
    negative_speeds = 0
    off_grid_gaps = 0
    count = 0
    for row in rows:
        count += 1
        group = partition(row)
        key = track_key(row)
        timestamp = int(row["global_time"])
        sample_key = key + (timestamp,)
        duplicates += sample_key in keys
        keys.add(sample_key)
        partitions[group] += 1
        movements[row["movement"]] += 1
        negative_speeds += float(row["v_vel"]) < 0
        tracks[key].append(timestamp)
    gaps = []
    for timestamps in tracks.values():
        timestamps.sort()
        for earlier, later in zip(timestamps, timestamps[1:]):
            delta = later - earlier
            if delta > 100:
                gaps.append(delta)
            if delta % 100:
                off_grid_gaps += 1
    return {
        "rows": count, "partitions": dict(partitions), "movement_row_counts": dict(movements),
        "track_keys": len(tracks), "duplicate_track_time_keys": duplicates,
        "negative_speed_rows": negative_speeds, "within_subset_gaps_over_100ms": len(gaps),
        "largest_within_subset_gap_ms": max(gaps, default=0), "off_grid_gaps": off_grid_gaps,
        "gap_caveat": "Subset gaps can be exits/reentries; not automatically missing source frames",
    }


def main():
    directory = BASE / "data" / "external"
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "lankershim_nb_section3.csv"
    if not destination.exists():
        partial = destination.with_suffix(".download")
        with urllib.request.urlopen(URL, timeout=120) as response, partial.open("wb") as output:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 64 * 1024 * 1024:
                    raise ValueError("Subset exceeds 64 MiB acquisition limit")
                output.write(chunk)
        partial.rename(destination)
    payload = destination.read_bytes()
    audit = audit_rows(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
    count_url, count_payload, counts = fetch_query(f"SELECT count(*) AS rows WHERE {FILTER}")
    expected = int(counts[0]["rows"])
    report = {
        "source_url": URL, "count_query_url": count_url,
        "count_response_sha256": hashlib.sha256(count_payload).hexdigest(),
        "inspected_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload),
        "expected_source_rows": expected, "count_matches": audit["rows"] == expected,
        "selection": "Northbound section 3, all lanes and movements; selected before fitting, not a verified stop-line approach",
        "audit": audit,
        "status": "Acquisition and QA only. Geometry and signal history still required for model validation.",
    }
    (BASE / "reports" / "lankershim_ingestion.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["count_matches"] or audit["duplicate_track_time_keys"]:
        raise SystemExit("Source count or uniqueness check failed")


if __name__ == "__main__":
    main()
