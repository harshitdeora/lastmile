# Verification evidence

Verified on Windows on October 16, 2026. No external deployment or live LLM execution is claimed.

## Commands actually run

| Command (from repository root unless noted) | Result |
| --- | --- |
| `docker info --format '{{.ServerVersion}}'` | Docker 29.2.1 after starting Docker Desktop. |
| `docker pull falkordb/falkordb:v4.16.0` | Pulled and recorded immutable digest used in Compose. |
| `.venv\Scripts\python.exe -m pip install -r backend\requirements.txt` | Installed in Python 3.12.14; exact resolved versions frozen in lockfile. |
| `docker compose up -d falkordb` | Real FalkorDB started at localhost:6380. Port 6379 was already used by another project and was preserved. |
| `$env:PYTHONPATH='backend'; .venv\Scripts\python.exe -m pytest backend\tests -q` | **24 passed** in 69.67 seconds. One upstream Starlette/AnyIO deprecation warning; no failed checks. |
| `npm install --no-audit --no-fund` in `frontend` | Installed pinned packages and generated package-lock.json. |
| `npm run build` in `frontend` | TypeScript and Vite production build passed. |
| `npm install --save-dev --save-exact vite@6.4.4 @playwright/test@1.64.1` then `npm audit --audit-level=low` | Patched the development-tool advisories discovered during container installation; **0 npm vulnerabilities** in the final lockfile. Production builds repeated successfully. |
| `npx playwright install chromium` in `frontend` | Installed actual Chromium for browser verification. |
| `npm run test:browser` in `frontend` | Actual load → investigate → inspect → preview → commit → execute → explain → replay journey passed; screenshots saved. Repeated against the production Compose UI. |
| `$env:PYTHONPATH='backend'; .venv\Scripts\python.exe -m app.evaluation` | Completed 30 real-graph runs, generated actual JSON/CSV; deterministic policies only. |
| `docker compose exec backend python -m app.evaluation` | Repeated the entire 30-run suite inside Linux Docker. Same per-world utilities and aggregate results; copied final JSON/CSV to the repository. |
| `docker compose build` | Both Linux backend and frontend images built; OR-Tools installed and frontend production assets compiled inside Docker. |
| `docker compose up -d --wait` | All LastMile services started; frontend HTTP 200 and graph-capable backend health passed. |
| `.venv\Scripts\python.exe scripts\verify_restart.py` | Real backend restart, real DB outage, DB restart and private-checkpoint continuation checks passed. |
| `docker exec lastmile-falkordb-1 redis-cli CONFIG GET dir appendonly appendfsync save` | Confirmed `/var/lib/falkordb/data`, `yes`, `everysec`, `60 1`. |
| `docker exec lastmile-falkordb-1 redis-cli INFO modules` | Confirmed graph module version 41600. |

An initial build found a CSS import issue and was fixed before the passing production builds. A degraded-state test exposed eager database connection during construction; the client now connects lazily so the API can return a structured 503. A graph-ID check led to separate `stock-d*` IDs for physical stock nodes. A recovery test was corrected to isolate the loaded vehicle because the unrestricted solver could legitimately choose a nearer fresh vehicle. A temporary Docker networking failure after a port was released was resolved by recreating the owned backend container; all final services and checks passed. These early failures are not counted as passes.

The final npm pins are Vite 6.4.4 and Playwright 1.64.1. See the upstream [Vite advisory](https://github.com/advisories/GHSA-fx2h-pf6j-xcff) and [Playwright advisory](https://github.com/advisories/GHSA-7mvr-c777-76hp). The audit result is specifically for the frontend npm dependency tree, not a comprehensive security audit of the application or Python environment.

## Acceptance coverage

| Requirement | Evidence / status |
| --- | --- |
| Hidden conditions / schedules excluded recursively | Public context, ranking, plans, impact, replay and recorded controller outcomes recursively tested; immutable private module separate from DTOs. |
| Longer valid alternative / directionality | Real bounded Cypher path test and one-way traversal test. |
| Late old report cannot overwrite authority | New inspection followed by late old unverified and authoritative observations. |
| Evidence expiry invalidates dispatch | Real reservation cancelled; eligible allocation released. |
| Inspection rank reacts to cost / deadlines | Cost raised to 80 minutes and deadlines shortened; value changes and becomes non-positive. |
| Hypothetical branches never mutate live graph | Observed graph payload and snapshot count identical before/after ranking. |
| No useful inspection | Scenario preserves both checks; independent tiny example rejects expensive inspection. |
| Capacity, shared stock, unique requests | Verified across real graph-derived routes and constrained stock case. |
| Idempotent commit / dispatch / delivery | Repeated commit and time advance reuse receipt, do not create assignments or deliver twice. |
| Stale plan rejected | Changed graph revision returns conflict before allocation. |
| Disruption / loaded recovery | Unstarted release, loaded/current state preserved, blocked inventory reused with zero new allocation; entered segment may finish. |
| Restart and browser refresh | Unit/integration resume equality, real Docker restart script, browser refresh retains 42 kits / budget 1. |
| Missing private checkpoint | Actionable HTTP 503 instructs volume restoration; attempted time advance leaves graph state identical. |
| Fair benchmark | Initial fingerprints equal; immutable physical checkpoint equality tested; independent policy RNG; separate graphs. |
| Live LLM invokes provider | **UNVERIFIED / unavailable**: no key/model configured. Protocol and provider-failure tests use stubs and are labelled accordingly. |
| Deterministic mode | Real end-to-end operation without credentials, visible label and recorded tool calls. |
| Database outage | Actual container stopped: health and attempted mutation return 503; post-restart state unchanged. |
| Browser journey | Real Chromium; desktop and 390×844 viewport; no page JavaScript errors or document horizontal overflow. |
| Production build | Local and Docker TypeScript/Vite builds passed. |

The hand-checkable example independently enumerates feasible subsets for one three-kit vehicle and two three-kit requests with utilities 3 and 9. Base utility is 3; a 50/50 open/closed check yields branches 9 and 3, expectation 6 and gain 3. An inspection finishing after both deadlines yields gain −3. This verifies the calculation against a separately stated feasible set.

## Published benchmark interpretation

Ten worlds per policy; delivered priority-weighted utility means: **27.2** no inspections, **30.4** random inspections, **72.0** graph-value selection. On-time kit means: 15.2 / 14.6 / 29.0. Graph value ties the no-inspection baseline in five worlds and improves it in five; there are no graph-value regressions in this small suite. Random inspection does regress in some worlds. All rows and comparisons are published, including those outcomes. This suite is synthetic and small; it does not establish general superiority or real-world utility.

Solver durations include the recorded baseline/branch, preview and commit solves, including graph-path retrieval time inside the pure planner call. Wall times are hardware-dependent and should not be treated as reproducible performance guarantees. `OPTIMAL` applies only to the bounded candidate formulation.

Screenshots: `01-investigate-desktop.png`, `02-replay-desktop.png`, `03-mobile.png`, `04-benchmarks-desktop.png`. On small screens the map scrolls horizontally so map labels remain readable. Screenshots were visually inspected.
