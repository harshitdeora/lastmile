# 2–3 minute demonstration script

Prepare Docker Compose and open localhost:5173. Use Critical crossing, world 9, Deterministic demo. This seed appears in the published 10-world suite. Avoid describing deterministic orchestration as a live LLM.

**0:00–0:20 — Problem.** “This is fictional Alder Reach. We have four vehicles, limited stock and six delivery requests. The bridge has conflicting reports. The question is which uncertainty is worth resolving before deadlines close.” Show the source panel and synthetic-scenario label.

**0:20–0:50 — Investigate.** Trace delivery impact. Explain Report → Road → Assignment / Request, and graph-derived alternative paths. Compare inspections: bridge gain +57.2, marsh negative. “That is an estimated value from two solver branches using an explicit synthetic prior. Both branches charge inspection time. The controller does not know the result.”

**0:50–1:20 — Act.** Inspect bridge; observe its real simulated result and retained report history. Preview and commit the plan. Explain expected revision, shared depot stock and capacity. Advance ten-minute steps; vehicles move on real backend state. Show 42 kits / six on-time requests in the open seed.

**1:20–1:45 — Explain and replay.** Follow a recorded decision to evidence IDs and plan. Open Graph evidence to show actual Cypher query names and returned IDs. Enter Replay and move to revision 0. The historical clock and disabled controls make this read-only.

**1:45–2:15 — Recover.** Return live, create another run, preview and commit its local plan. Trigger capacity disruption before dispatch: an unstarted allocation is released. Run one decision to replan; no completed work or loaded inventory is reset. Mention the Capacity disruption scenario's time-based withdrawal. Show No useful inspection's non-positive ranking if time allows.

**2:15–2:45 — Measure.** Open Benchmarks: ten identical worlds per policy, no inspections / random / graph value. Show every seed, including ties and adverse outcomes. “These are synthetic results from one bounded model. The live Responses adapter is implemented but was not exercised without a configured API credential.”

End with the public repo and local setup. Record the video yourself after reviewing and understanding the code. Do not claim a hosted service or recorded video already exists.
