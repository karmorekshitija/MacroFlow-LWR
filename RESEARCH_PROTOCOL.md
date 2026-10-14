# Observed approach validation protocol

Status: protocol only; no observed validation completed. Established before fitting on 2026-10-14.

## Question

Can a simple CTM reproduce queue growth and discharge on a single measured signalized approach? What errors arise from lane aggregation, turning movements and boundary assumptions?

## Source choice and evidence

[FHWA Lankershim fact sheet](https://www.fhwa.dot.gov/publications/research/operations/07029/index.cfm) describes two 15-minute blocks, 08:30–08:45 and 08:45–09:00, and supporting signal timings. This makes it a candidate for arterial validation, subject to inspecting actual geometry and files.

[Official distribution catalog](https://catalog.data.gov/dataset/next-generation-simulation-ngsim-vehicle-trajectories-and-supporting-data) links dataset `8ect-6jqj`, its CSV export and attachments. It lists CC BY-SA 3.0; check attachment-specific terms before redistributing files or derived data.

[Official column metadata](https://data.transportation.gov/api/views/8ect-6jqj/columns.json) warns that repeated Vehicle_ID values are not associated. It defines Global_Time in milliseconds since the epoch and local coordinates in feet. Do not merge trajectories across collections or infer units from magnitudes alone.

Sources inspected live on 2026-10-14. A bounded trajectory API probe and official metadata PDF are now inspected; complete trajectory, geometry and signal files are not yet available. See `DATA_FEASIBILITY.md`. Coverage queries do not establish trajectory accuracy or completeness.

## Temporal split amendment, before fitting

The API has two frame-origin groups, computed as `global_time - 100*(frame_id-1)`: 1118935680000 and 1118936700000. The first contains 705,294 rows and ends at 1118936800600; the second contains 902,025 rows and starts at 1118936700000. Their time extents overlap by 100.6 seconds. No duplicate `(vehicle_id, global_time)` groups were returned by the dataset-wide duplicate query, but distinct identifiers do not establish distinct physical vehicles.

Use first-origin rows only in [08:30,08:45) Pacific daylight time for calibration, and second-origin rows only in [08:45,09:00) for evaluation on June 16, 2005. `lankershim_time.py` implements these half-open windows in epoch milliseconds, rejects unexpected frame origins and keys tracks by origin plus vehicle ID. Exclude the first group's tail after the split and the second group's tail after 09:00. This is chronological evaluation, not a claim of independent vehicles across the boundary. Recheck keys and source identity on complete ingestion.

The metadata's trajectory section explicitly describes 08:28 as the first collection start despite the 08:30 filename. It maps collection starts to RSM times 08:27:34 and 08:44:34, suggesting a 26-second clock offset. Confirm against actual RSM files before applying an alignment; do not estimate an offset by minimizing held-out queue error.

## Research positioning

[Su, Kurzhanskiy and Horowitz, Simulation of Arterial Traffic Using Cell Transmission Model (2013)](https://horowitz.me.berkeley.edu/Publications_files/All_papers_numbered/Su_TRB_2013_Simulation_of_Cell_Transmission_Model_Using_NGSIM_data.pdf) already studies CTM on Lankershim using trajectory and signal inputs. Position this project as reproducible replication with explicit temporal separation, matched baselines and failure analysis, not the first arterial CTM validation. An incremental contribution remains to be demonstrated.

## Freeze before evaluation

- Choose direction, approach bounds, lane/movement filters and stop line based on metadata and coverage, before evaluating accuracy.
- Fit on the first block; evaluate on the second. Document any coverage-driven split revision before scoring.
- Inputs: geometry, timing and measured boundary arrivals; initial state may be observed. Interior queue and discharge targets must not also be forced as boundary conditions.
- Queue definition: define speed threshold, spatial connectivity and aggregation interval from the observation protocol before scoring. Report sensitivity to that definition.
- Compare with a persistence or simple queue baseline matched to available inputs. A simulation driven by future measured boundaries is conditional reconstruction, not an autonomous forecast.
- Metrics: count/queue MAE, RMSE, signed bias, missing-bin counts and time-series plots. Queue distances in metres; discharge counts in vehicles per stated bin. Avoid treating correlated trajectory frames as independent samples.
- Keep poor fits and failed intervals in the report. Any post-evaluation tuning needs new evaluation data or an explicit exploratory label.

## Required artifacts

Original-file provenance/checksums; filtering audit; chronological split configuration; calibration output; aligned model/baseline/observation series; score JSON; observed-vs-model figure; residual figure; two-page report. No empirical CV claim until these artifacts exist.
