"""Download the official support archive and inventory it without extraction."""

import hashlib
import json
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent
URL = "https://data.transportation.gov/api/views/8ect-6jqj/files/62273322-a1e9-48fc-8692-b4c576bafc20?download=true&filename=Lankershim-Boulevard-LosAngeles-CA.zip"


def main():
    destination = BASE / "data" / "external" / "Lankershim-Boulevard-LosAngeles-CA.zip"
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(".partial")
    if not destination.exists() and not partial.exists():
        with urllib.request.urlopen(URL, timeout=60) as response, partial.open("wb") as output:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 100 * 1024 * 1024:
                    raise ValueError("Archive exceeds the 100 MiB download limit")
                output.write(chunk)
    candidate = destination if destination.exists() else partial
    digest = hashlib.sha256()
    with candidate.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    try:
        with zipfile.ZipFile(candidate) as archive:
            members = [{"name": entry.filename, "bytes": entry.file_size, "compressed_bytes": entry.compress_size} for entry in archive.infolist()]
        status, error = "inventory_readable", None
    except zipfile.BadZipFile as failure:
        members = []
        status, error = "invalid_archive", str(failure)
    result = {
        "source_url": URL,
        "inspected_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": digest.hexdigest(),
        "bytes": candidate.stat().st_size,
        "status": status,
        "error": error,
        "cache_policy": "Reuse existing partial for inspection; never automatically redownload it",
        "members": members,
        "scope": "Archive inventory only; not model validation",
    }
    report = BASE / "reports" / "lankershim_archive_inventory.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if error:
        raise SystemExit(1)
    if candidate == partial:
        partial.rename(destination)


if __name__ == "__main__":
    main()
