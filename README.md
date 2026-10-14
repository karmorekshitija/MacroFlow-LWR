# Transportation: CTM verification and observed-data preparation

A standard-library Python cell-transmission model for a synthetic 2 km corridor, with triangular and Greenshields fundamental diagrams. It is the portfolio's flagship research-preparation study, not a completed observed-data validation.

## Evidence

- Analytical shock-front comparison at 40/80/160 cells: approximately 2.026%, 0.604% and 0.481% speed error.
- Conservation, external arrival queues and density bounds; diagram-specific capacity and queue thresholds.
- Nine synthetic fixed-signal scenarios and three causal-versus-fixed comparisons with matching realized green budgets. Differences are small and scenario-specific.
- Complete acquisition of 117,003 official northbound section-3 trajectory rows, with source-count and track-key checks. The origin-aware split excludes overlapping collection tails.

Actual signal histories and verified stop-line geometry are still missing. Raw files remain local and ignored pending license clarification. Collection metadata suggest a 26-second timing offset that must be checked against RSM files. The 100-row probe is not used as validation data.

## Reproduce

```text
python -B -m unittest discover -s tests -q
python -B run_traffic_sim_and_tests.py
```

Network-dependent acquisition is separate: `python -B ingest_lankershim.py`. Run the local `build_research_reports.py` to regenerate the report and figures.

Read `reports/RESEARCH_REPORT.md`, `RESEARCH_PROTOCOL.md`, `DATA_FEASIBILITY.md`, `VALIDATION.md` and `RESEARCH_OWNERSHIP.md`. Figures: `reports/shock_refinement.svg`, `reports/equal_budget_delay.svg`, `reports/demand_sensitivity.svg`.

Window delay is occupancy-time plus external waiting minus free-flow time for distance actually covered. It is not mean completed-trip delay. Queue extent counts high-density cells, not a necessarily connected stopped queue. No Webster formula, cross-street traffic, amber clearance or field controller evaluation is implemented. The legacy HTML viewer is a separate unverified implementation. Student ownership exercises remain pending.
