"""Save bounded official API coverage queries without fitting a model."""

import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent
ENDPOINT = "https://data.transportation.gov/resource/8ect-6jqj.json"
QUERIES = {
    "coverage": "SELECT location, count(*) AS rows, min(global_time) AS first_time, max(global_time) AS last_time WHERE location='lankershim' GROUP BY location",
    "movements": "SELECT direction, section_id, int_id, movement, count(*) AS rows, min(global_time) AS first_time, max(global_time) AS last_time WHERE location='lankershim' GROUP BY direction, section_id, int_id, movement ORDER BY direction, section_id, int_id, movement LIMIT 1000",
    "sample": "SELECT * WHERE location='lankershim' ORDER BY global_time, vehicle_id, frame_id LIMIT 100",
    "time_bins": "SELECT floor(global_time/60000) AS minute_bin, count(*) AS rows, min(global_time) AS first_time, max(global_time) AS last_time, min(frame_id) AS first_frame, max(frame_id) AS last_frame WHERE location='lankershim' GROUP BY minute_bin ORDER BY minute_bin LIMIT 1000",
    "duplicate_keys": "SELECT vehicle_id, global_time, count(*) AS copies WHERE location='lankershim' GROUP BY vehicle_id, global_time HAVING count(*) > 1 ORDER BY vehicle_id, global_time LIMIT 100",
    "frame_origins": "SELECT global_time - 100*(frame_id-1) AS frame_origin, count(*) AS rows, min(global_time) AS first_time, max(global_time) AS last_time WHERE location='lankershim' GROUP BY frame_origin ORDER BY frame_origin LIMIT 1000",
}


def fetch_query(query):
    url = ENDPOINT + "?" + urllib.parse.urlencode({"$query": query})
    with urllib.request.urlopen(url, timeout=90) as response:
        payload = response.read(2 * 1024 * 1024 + 1)
    if len(payload) > 2 * 1024 * 1024:
        raise ValueError("Probe response exceeds 2 MiB limit")
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise ValueError("Expected an API row list")
    return url, payload, rows


def main():
    directory = BASE / "data" / "external" / "lankershim_probe"
    directory.mkdir(parents=True, exist_ok=True)
    report = {
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Coverage and schema probe only; not complete trajectories or model validation",
        "license_note": "Catalog lists CC BY-SA 3.0; host metadata lists CC BY-SA 4.0. Resolve file-specific terms before redistribution.",
        "queries": {},
    }
    for name, query in QUERIES.items():
        url, payload, rows = fetch_query(query)
        (directory / (name + ".json")).write_bytes(payload)
        report["queries"][name] = {
            "url": url,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "returned_rows": len(rows),
            "results": rows if name != "sample" else None,
        }
    output = BASE / "reports" / "lankershim_api_probe.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({name: entry["returned_rows"] for name, entry in report["queries"].items()}))


if __name__ == "__main__":
    main()
