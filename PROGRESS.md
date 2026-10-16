# LastMile build progress

## Plan
1. Establish real FalkorDB storage and synthetic world boundary.
2. Implement bounded graph paths, CP-SAT planning, inspection value and execution.
3. Add tool controllers, operations UI, replay and fair benchmarks.
4. Verify backend, browser and persistence; document reproducible setup.

## Completed
- Created public GitHub repository https://github.com/harshitdeora/lastmile.
- Real FalkorDB graph, parameterised Cypher, private immutable simulator, CP-SAT planner and inspection estimator.
- Reservations, idempotent commits/time advancement, segment execution, expiry, capacity and blockage recovery.
- Deterministic tool policy and configurable real Responses API adapter with typed input/output schemas.
- React operations UI, evidence inspection, read-only replay, three scenarios and fair 30-run benchmarks.
- Docker Compose, locked dependencies, CI workflow, graph/assumption documentation, demo script and submission draft.

## Environment
- Windows; Node 22.19, npm 10.9, bundled Python 3.12.14.
- GitHub Git credential available; no OpenAI environment credential found.
- Docker Desktop 29.2.1 and FalkorDB 4.16.0 verified. Owned service ports: 5173, 8000, 6380, all localhost-bound.

## Verification
- 29 real-database backend tests passed; production frontend build passed locally and in Docker.
- Chromium journey passed at desktop and 390-pixel viewport; screenshots saved.
- Real Docker backend restart, DB outage/503, DB restart and private checkpoint continuation passed.
- 30-run suite completed: mean delivered utility 27.2 / 30.4 / 72.0 for none / random / graph value. All rows and ties/regressions retained.
- Exact commands and acceptance mapping: docs/verification.md.
- Full 30-run suite repeated inside Linux Docker with identical per-world utilities; final output exported to benchmarks/.
- Source, screenshots, documentation and CI pushed to public origin/main; GitHub metadata and remote commit verified.
- Patched Vite/Playwright after concrete installer advisories; final npm audit reports zero vulnerabilities.
- Connected existing signed-in Codex through the official app-server, without extracting its credentials.
- Actual gpt-6.1-sol tool orchestration and live browser cycle passed; four live cycles delivered 42 kits / six requests on time. Evidence: docs/live-codex-smoke.json.

## Remaining limits / participant steps
- Live Codex sign-in mode is verified and available. The separate API-key adapter still needs OPENAI_API_KEY/OPENAI_MODEL for its own provider smoke test.
- Participant must review, understand and meaningfully contribute, record the demo video and submit. No external deployment or video claimed.
- GitHub Actions is configured; remote workflow status is visible in the repository Actions tab.
