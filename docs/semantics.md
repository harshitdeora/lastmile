# Model and implementation assumptions

## Evidence

- Initial stable roads are verified through minute 181, beyond the 180-minute horizon.
- Candidate roads are CONFLICTING or STALE. Authoritative observations produce VERIFIED_OPEN / VERIFIED_CLOSED with a finite 90-minute validity period.
- Reports store both observation and receipt times and retain their source/authority class. A late older inspection cannot replace newer authority. Unverified report text cannot grant authority.
- Once validity expires, the road becomes STALE. Unstarted routes using ineligible evidence are cancelled and their reservations released. Loaded vehicles stop before a segment lacking current valid evidence; onboard kits and current position are retained.
- Only verified-open roads are eligible for dispatch. Hypothetical inspection branches may assume exactly one candidate road open/closed.
- Road priors (.65 for the bridge, .35 for the marsh link) are explicitly synthetic scenario inputs. They are not learned from simulator truth or calibrated to real flooding.

## Planner and inspection value

Requests are indivisible, kit quantities and capacities are integers, and vehicles start at their assigned depot. Candidate routes visit at most two requests, use graph-derived paths and have no reload/transfer operation. Vehicles ending elsewhere cannot reload by teleporting. Recovered vehicles may plan from their actual location using their retained loaded stock, with no additional allocation from a depot.

For on-time requests, utility is `sum(quantity * configured weight)`. Plans also include already realised and known committed on-time utility, so branches are compared on a consistent total. The CP-SAT objective first maximises utility, then minimises travel, then applies deterministic stable-ID aggregate tie costs. A single worker and fixed solver seed make repeated inputs reproducible. Solver wall time is measured, not deterministic. Serving no requests can be a feasible optimum of poor utility; unmet requests are labelled with resource/deadline/candidate tradeoffs rather than universally called infeasible.

For each eligible uncertain road, ranking:

1. Solves the current no-inspection plan.
2. Copies the observed snapshot, deducts one budget check and projects **known committed movement** through the inspection interval using the same time loop with no simulator truth access.
3. Solves the open and closed branches with the same planner and limits.
4. Computes `p_open * open_utility + (1-p_open) * closed_utility - base_utility`.

No branch writes to the live graph or reads future events. At most four roads are ranked in stable ID order. With non-positive maximum gain, the deterministic policy proceeds without inspection. It repeats the one-step calculation after evidence/time changes. This is an estimate under the stated model; no multi-step information optimum is claimed.

## Reservations and physical handoff

`preview → reserved → in_transit → delivered`, with cancelled/blocked outcomes. A preview is read-only. Commit requires its expected graph revision, recomputes the same plan under the run lock and atomically writes reservations and assignments. A changed graph returns HTTP 409.

Available depot stock is initial stock minus non-released allocations. Kits are physically handed off at **vehicle loading**: the reservation moves from reserved to loaded and kits become onboard inventory. A delivered request reduces onboard kits once; the original allocation remains consumed. A retry uses the stored idempotency receipt and does not reload, re-deliver or advance time twice. An unstarted cancellation releases its allocation. A blocked loaded assignment does not release its physical allocation; a subsequent plan reuses those kits with a zero additional stock allocation. All selected requests are unique and each vehicle has at most one active assignment.

The simulator checks before entering each road. **A closure after entry does not stop that segment**; it may finish. The next segment must pass observed-validity and physical checks. Discovered physical closures create observable traversal evidence; future closure schedules remain private. Vehicle withdrawal prevents new/unstarted work; already loaded committed work finishes. The manual capacity disruption only selects an unloaded vehicle and cancels only its unstarted work.

One backend worker serialises run mutations using an RLock. A process lease prevents two API workers sharing the same private volume. Each operational mutation is one revision-guarded GRAPH.QUERY statement. This is a single-process MVP with Redis/FalkorDB command atomicity; no multi-process/distributed transaction guarantees are claimed. Graph writes are prevalidated; failed writes never produce successful API outcomes. A network failure after a successful write can be retried using the same idempotency key.

## Simulation boundary and restart

World generation uses `Random(seed)` once to build an immutable private checkpoint. Policy randomness uses a separate generator. Conditions at time T depend only on the checkpoint and T, never on the number of controller random draws. The seed is accepted for explicit creation/evaluation but excluded from World DTOs and controller context. Controller tools expose neither checkpoints nor future schedules. The browser benchmark view exposes aggregate/per-seed evaluation results in a separate workflow; controller tools do not serve them.

Run time, observations, budget, resource commitments, event sequence and idempotency receipts persist in FalkorDB. The private file does not need updating as time advances. Restart reloads both stores instead of generating new truth. Missing private checkpoint is an error for time-consuming physical actions. An orphan checkpoint after a failed initial graph write is harmless and never becomes a public run.

Replay reads committed graph snapshots, marks historical time explicitly and disables mutation controls. It cannot rewind simulator truth or operational state. A new run gets a new graph; explicit selected-run reset removes only that graph/checkpoint and creates a replacement.

## Live Codex connection

The local host bridge runs official `codex app-server` with Codex-managed ChatGPT authentication. The application never reads the Codex credential file or exports its access/refresh tokens. Each cycle uses an ephemeral model session, no environment access, and only eight registered LastMile dynamic tools. Shell, browser, connected apps, plugins and multi-agent tools are disabled. The bridge is a controller client, not another graph writer: every tool runs through an authenticated callback into the existing single API worker, using the same Pydantic schemas, mutation lock and idempotency receipts. Callback identifiers are stable for retries.

The bridge is bounded to 12 tools and 100 seconds. A failed/interrupted model turn is recorded as a failure; it is never presented as a completed live turn. Already committed application actions remain in FalkorDB. Successful decisions link to evidence IDs returned by the tools, including any committed plan being continued. The live smoke report is an actual separate run, not part of the deterministic policy benchmark.
