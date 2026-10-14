# Transportation research report

## Question and positioning
Can a compact CTM reproduce queue growth and discharge on an observed approach? The implemented numerical study is a synthetic precursor; observed calibration is not completed. Earlier CTM/Lankershim work means the defensible direction is replication and failure analysis, not a new model.

## Method
The current synthetic corridor uses 40 cells over 2 km, a 2-second step and a 90-second signal cycle. Supply-demand fluxes conserve vehicles; rejected arrivals remain in an external queue. Queue extent is the summed length of cells above 1.15 times diagram-specific critical density, not necessarily one connected stopped queue. Greenshields uses its own capacity and critical density. Equal-budget comparisons give both policies the same realized green seconds. No cross-street, amber, turning or spillback model is validated.

Window delay is occupancy-time plus external waiting minus free-flow time for distance actually covered. It is not completed-trip delay. The historical adaptive-versus-fixed percentage improvements spend different green budgets and must not be used as fair controller-performance claims.

## Results
- Tracked shock-speed errors for 40/80/160 cells: 2.026065%, 0.604091%, 0.481133%. This supports numerical refinement, not a claimed formal convergence order.
- Causal-minus-fixed delay at demand 0.75/1/1.25: -0.0180, -0.0311, -0.0496 vehicle-hours. These are small scenario-specific differences, not evidence of general superiority.
- Acquired 117,003 northbound section-3 records and verified the official count. Temporal filtering retains 45,310 calibration rows and 60,465 evaluation rows, excluding 11,228. There are 0 duplicate track/time keys and 4 within-subset gaps over 100 ms. Gaps may reflect leaving/re-entering the section; completeness is not established by counts alone.

## Unfinished observed-data gate
The official support archive is unreadable. Exact stop-line geometry and actual RSM phase histories remain unavailable. The metadata suggests a 26-second clock offset, not yet checked against timing files. No signal schedule is invented from held-out queues. The selected section is an ingestion candidate, not a verified full approach. Calibration, baseline scoring, observed residual plots and empirical conclusions are blocked by these inputs. File-specific licensing remains unresolved; raw data stay ignored and local.

## Reproduce and inspect
Run `python -B run_traffic_sim_and_tests.py`, `python -B -m unittest discover -s tests -q`, and from this folder `python -B build_research_reports.py`. Network acquisition is a separate `python -B ingest_lankershim.py` command. See `lankershim_ingestion.json`, `RESEARCH_PROTOCOL.md`, `DATA_FEASIBILITY.md` and `RESEARCH_OWNERSHIP.md`.

Figures: `shock_refinement.svg`, `equal_budget_delay.svg`, `demand_sensitivity.svg`. These show analytical/synthetic evidence only.

## Reference and contribution boundary
[Su, Kurzhanskiy and Horowitz (2013)](https://horowitz.me.berkeley.edu/Publications_files/All_papers_numbered/Su_TRB_2013_Simulation_of_Cell_Transmission_Model_Using_NGSIM_data.pdf) motivates replication. [FHWA source description](https://www.fhwa.dot.gov/publications/research/operations/07029/index.cfm) identifies supporting data. The agent implemented substantial changes; student derivation, reproduction and interpretation exercises remain unconfirmed. Do not present this as independently completed student research yet.
