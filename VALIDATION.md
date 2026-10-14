# Transportation validation and next experiment

Priority confirmed on 2026-10-14: transportation, then hydraulics, then structures.

## Numerical evidence

### Prospective equal-budget experiment

A separate causal policy now chooses the green start at each cycle boundary using the current average density in the six cells ending at the stop bar. At or above critical density it starts immediately; otherwise it delays by up to 10 seconds, limited by the available red time. The decision stays fixed for that cycle. Both policies receive 48 seconds of green per 90-second cycle (the discretized 0.52 ratio). This rule was specified before running the three comparisons; it uses neither future demand nor the adaptive replay.

At demand multipliers 0.75, 1.0 and 1.25, causal-minus-fixed accumulated delay is respectively -0.0180, -0.0311 and -0.0496 vehicle-hours. These small deterministic scenario differences do not establish general superiority or statistical significance. Tests enforce identical realized green budgets and network conservation. Seven tests pass. The policy is an illustrative phase heuristic, with no cross-street or clearance model; it is not ready for deployment.

The observed-data subset is now acquired and audited; actual phase histories and stop-line geometry remain the next gate. Both the prospective experiment and retrospective replay are retained separately in the report. Historical test counts below describe earlier checkpoints; use the current parent validation summary.

### Equal-green diagnostic (2026-10-14)

The report now records actual green seconds in every cycle. A retrospective replay gives exactly that budget to a contiguous green phase at each cycle start. This isolates within-cycle placement from resource allocation; it uses the adaptive run's future outcomes and is not an independently deployable fixed-time controller. In the current default scenario, replay and adaptive accumulated delay are identical to report precision (difference 0.0000 vehicle-hours). These results provide no evidence of an advantage from within-cycle placement. Aggregate green fractions now measure actual discrete green steps rather than averages of requested ratios. All six tests pass.

The earlier fixed 0.42/0.62 scenarios still have different budgets. Their percentage reductions must not be interpreted as an equal-resource controller comparison. The prospective equal-budget comparison is implemented above; observed-data validation remains incomplete.

The shock check interpolates the midpoint-density crossing between cell centres. Its displacement over 120 seconds is compared with the Rankine-Hugoniot jump condition. The older excess-mass estimate remains a conservation diagnostic. It was computed from the simulated state, not assigned the analytical answer; the earlier review overstated that criticism. Agreement in that integral diagnostic does not establish front resolution.

The 40/80/160-cell study reports front-location errors, not a demonstrated formal convergence order. Position errors can depend on where the discontinuity falls within a cell. The nine synthetic sensitivity cases combine demand multipliers 0.75/1/1.25 with green ratios 0.42/0.52/0.62.

## Interpretation limits

- All corridor inputs are constructed. No observed traffic dataset has been calibrated or validated.
- Fixed-green comparisons are a discrete parameter sweep. No Webster formula is implemented.
- Delay integrates pre-update cell occupancy plus external-queue waiting minus cell-outflow distance divided by free-flow speed. Initial vehicles receive only the distance allowance actually traversed. Unfinished trips contribute only within the observation window. The mean divides by initial vehicles plus all arrivals, not completed trips.
- Arrivals are available at each step start. Residual external queue waits the full timestep and is retained in network conservation. Throughput divides exits by initial vehicles plus all arrivals.
- Adaptive control can use more green than fixed control. There is no simulated cross street. Compare equal green budgets before making a controller-superiority claim.
- The browser viewer is a separate implementation and has not been validated against these new checks.
- Older CV PDF/HTML/TeX exports and outreach drafts may contain obsolete percentages. They need regeneration and review before use.

## Reproduce

From this directory, run `python -B -m unittest discover -s tests -v`, then `python -B run_traffic_sim_and_tests.py`. The second command regenerates three CSVs and the JSON report. CSV timestamps now identify the post-update state, starting at 2 seconds.

## Next release gate

External-queue and finite-window distance accounting, comparable signal budgets, data acquisition and origin-aware temporal filtering are implemented. Recover actual signal phase histories and verify stop-line geometry before calibration. Then report held-out flow/queue errors against a matched baseline. See `RESEARCH_PROTOCOL.md` and `reports/lankershim_ingestion.json`. Do not treat passing synthetic checks or downloading trajectories as completion of this gate.

## Application wording supported now

Implemented a Python cell-transmission traffic model and checked shock-front propagation against the analytical jump condition at three grid resolutions; evaluated nine synthetic demand and signal scenarios. Observed-data validation remains pending.
