# Lankershim data feasibility

## Current evidence

The official support ZIP downloaded as 80,179,421 bytes but cannot be opened by Python's ZIP reader. This is an acquisition failure, not proof that the underlying research data are invalid. `reports/lankershim_archive_inventory.json` records the local checksum and error. `inspect_lankershim.py` reuses the failed partial rather than repeatedly downloading it. An inventory-readable ZIP is not a full CRC verification.

The official Socrata trajectory API is accessible. `probe_lankershim.py` saves six bounded responses under ignored `data/external/lankershim_probe/`, with query URLs and response checksums in `reports/lankershim_api_probe.json`:

- Coverage: 1,607,319 trajectory rows (not unique vehicles).
- Global-time range: 1118935680200 to 1118937747000; elapsed span 2066.8 seconds. Do not infer continuous coverage or the documented 15-minute split from these endpoints.
- Movement coverage: 75 grouped combinations of direction, section, intersection and movement. Numeric direction codes remain uninterpreted until checked against documentation.
- Sample: first 100 ordered rows, for schema inspection only. It is neither a complete vehicle set nor a validation dataset.

The catalog lists CC BY-SA 3.0 while host metadata lists CC BY-SA 4.0. File-specific terms remain unresolved. Raw downloaded responses are kept outside version control; do not redistribute them as cleared data.

## Next gate before calibration

1. Recover authoritative geometry and signal-phase timing independently of model residuals. Do not estimate signal timings from held-out queues and call those same queues independent validation.
2. Verify documented collection windows against observed timestamps; inspect gaps and identifier resets before declaring track keys or train/evaluation boundaries.
3. Choose one approach and movements based on physical coverage, not best model fit. Acquire its complete rows using deterministic pagination and verify counts and duplicate keys.
4. Check missing frames, lanes, unit conversions and turning movements. Define stopped-vehicle and queue measures before scoring.
5. Record measured initial/boundary inputs separately from validation targets. Only then implement geometry-specific simulation and calibration.

No observed queue accuracy, controller superiority or research novelty is established by this probe.

## Metadata and temporal audit update

Retrieved the [official Lankershim metadata PDF](https://data.transportation.gov/api/views/8ect-6jqj/files/38de7132-edbb-44ea-b9c5-c53b33317ee5?download=true) (491,613 bytes; SHA256 `1d4673badd8249767b135938763deb77109db2119262616749db376dc0e1d8b3`). The cached PDF and text extraction remain under ignored `data/external/`.

- Direction codes are 1 east, 2 north, 3 west, 4 south; movement codes are 1 through, 2 left, 3 right. Local Y starts at the southern boundary and represents vehicle front-centre position along the median. Speed is feet/second. These definitions do not supply stop-line coordinates.
- The trajectory section describes starts at 08:28 and 08:45 and corresponding RSM starts at 08:27:34 and 08:44:34. The inferred 26-second clock correction still requires confirmation against the actual timing files.
- Required timing assets include controller sheets `int087.pdf` through `int090.pdf` and real-time split monitor files `RSM087-061605` through `RSM090-061605`; exact phase/approach mapping remains pending. Static controller settings alone are not observed actuated phase histories.
- The PDF prefers original TXT trajectories over converted CSV and includes legacy redistribution restrictions. This adds to the licensing ambiguity; retain local-only raw files and resolve terms before publishing them.
- Six API queries now include 35 minute bins, zero returned duplicate vehicle/time groups, and two frame-origin groups. Their extents overlap by 100.6 seconds. There are rows in every minute bin, but sub-minute gaps and track completeness have not been checked.
- The pre-fit split now uses both frame origin and timestamp. Tests cover overlap exclusion, half-open boundaries, separate track keys and rejection of unknown frame origins. This helper is not yet a complete ingestion pipeline.

The official metadata and API endpoints reconcile the early 08:28 start, but do not explain all late tails. Keep those tails excluded under the declared evaluation windows rather than silently changing timestamps.

## Reproduction

### Complete section subset acquired

`ingest_lankershim.py` acquired 117,003 northbound section-3 rows (10,246,561 bytes), matching an independent official count query. The pre-fit filter retains 45,310 calibration rows and 60,465 evaluation rows; 11,228 are excluded. Among 773 origin/vehicle track keys there are no duplicate track/time pairs or negative speed rows, and four gaps over 100 ms (largest 14.1 seconds). These are gaps within a spatial subset, not proof of missing source frames. All lanes and movements were retained; a verified stop-line approach has not yet been defined. Checksums, selection and query URLs are in `reports/lankershim_ingestion.json`.

This completes bounded subset acquisition, not model adaptation or observed validation. Original-file comparison, precise spatial boundaries, clock alignment and phase histories remain unverified.

Run `python -B inspect_lankershim.py` to inspect the cached archive; invalid archives intentionally return exit code 1 after writing the report. Run `python -B probe_lankershim.py` with network access to refresh the bounded API probe. Run `python -B -m unittest discover -s tests -q` for local tests; these do not access the network.
