# Submission draft — participant review required

**Project:** LastMile — Verify the uncertainty. Deliver what matters.

**Primary track:** Agents That Act on Connected Data.

**Repository:** https://github.com/harshitdeora/lastmile

**Demo video:** Participant must record and add the URL. No recording is claimed.

**Deployment:** Complete local Docker Compose setup is provided. No hosted URL is claimed.

## Problem and solution

Relief coordination involves choosing what to verify as well as what to deliver. LastMile explores that decision in a synthetic flood-affected town. It investigates conflicting road evidence, scores inspections by expected constrained delivery utility, records observations in a persistent graph, reserves stock and vehicles, and recovers from disruptions.

FalkorDB is central: observed roads, reports, requests, plans, assignments, reservations and decisions live in the graph. Real multi-hop path queries produce valid route alternatives; relationship queries trace evidence to operational consequences. Without FalkorDB, operational mutations fail explicitly. OR-Tools chooses compatible deliveries, while a verified live Codex controller orchestrates validated backend actions using the participant's existing local sign-in. It completed six deliveries / 42 kits through real model-selected tools. A visibly labelled deterministic controller makes the comparison reproducible without model credentials. A separate API-key adapter is also included.

## Evaluation

The repository includes actual JSON and CSV outputs from a 30-run suite: ten worlds per policy, shared starting observations, identical physical schedules and common planner constraints. Results report all seeds, ties and regressions. Describe the final committed output rather than copying an unverified headline number. No real-world benefit or calibrated prediction is claimed.

## AI assistance and participant contribution

Codex was used extensively for implementation, tests, interface construction and documentation. The participant is responsible for reviewing, understanding and verifying the implementation, making meaningful project contributions, explaining the graph queries and architectural choices, recording the working demonstration, and submitting accurate claims. The participant should edit this paragraph to describe their actual contributions; do not imply review or understanding that has not happened.

## Official rules checked October 16, 2026

The [official rules](https://www.wemakedevs.org/hackathons/falkordb/rules) require FalkorDB to perform a central function, permitted data, a public repository, setup/graph documentation, relevant queries or algorithms, a working demo video, and a named track. They allow AI assistance with disclosure and require participant understanding and meaningful contribution. Complete local setup is accepted when a deployment is unavailable. The listed deadline is **October 18, 2026 at 11:59 PM IST**. Recheck the rules when submitting.

## Blog outline

1. Why the next useful action can be an inspection rather than a delivery.
2. Model evidence and dependency paths in FalkorDB.
3. Keep simulator truth outside agent context.
4. Compute open/closed utility branches with the same constrained solver.
5. Reserve, execute and recover without double spending.
6. Show the complete benchmark, including when inspection does not help.
