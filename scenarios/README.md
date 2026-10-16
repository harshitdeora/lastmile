# Public synthetic scenarios

The executable, agent-visible definitions are in `backend/app/scenarios.py`. They define 16 locations (3 depots, 5 shelters, 8 junctions), 25 bidirectional physical segments, 4 vehicles, 6 indivisible requests, 56 initial kits, a 180-minute horizon and an initial two-check inspection budget.

| Scenario | Distinguishing behaviour |
| --- | --- |
| `critical_crossing` | Conflicting bridge evidence and a long verified detour. Seeds include open and closed cases. |
| `capacity_disruption` | Same starting observations plus a private time-scheduled vehicle withdrawal, announced only when time reaches it. |
| `no_useful_inspection` | Bridge check costs 45 minutes; urgent demand cannot benefit. Negative values preserve budget. |

The public module contains no truth conditions, schedules or per-run seeds. Generated immutable checkpoints live only in `.private/` or the private Docker volume and are ignored by Git. The evaluator uses seeds 0–9 and rotates scenario by seed modulo 3. Illustrative open critical-crossing world: seed 9. Closed critical-crossing worlds include seed 0 and seed 6. Adverse seeds include pre-generated physical closures; these are evaluator details, never live tool context.
