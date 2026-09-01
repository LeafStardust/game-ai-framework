# Red/White Competence Audit

## Status

The three-Bond pilot production architecture is locally green, but the production agent has failed the live Red Deck / White Stake competence gate.

Do not run further repeated 10-attempt live batches until the offline competence audit below identifies and corrects a concrete run-level defect.

## Live evidence

Three fixed-production 10-attempt batches were run with `balatro_validate_pilot_live.py`.

### Batch 1 — pre-timeout fix

Repository SHA: `4158851ea97aabc7fa9ea6f49c411523db949f14`

- wins: 0/10
- average ante: 2.100
- median ante: 1.000
- power-engine utilization: 0.245
- unused active engines: 0.000
- destructive pivots: 0.000
- illegal actions: 0.000

Postmortem exposed a repeated D1 failure: a successful shallow Joker-aware adaptive search could be discarded when a later deep search exhausted the wall-clock budget, causing the engine to drop to a crude structural fallback.

Fix retained:
- `7cbc13439c7ec0f047772dc01eb4b4626feeb47d` — preserve deepest successfully completed D1 search on timeout.

### Batch 2 — after timeout fix

Repository SHA: `7cbc13439c7ec0f047772dc01eb4b4626feeb47d`

- wins: 0/10
- average ante: 3.100
- median ante: 3.000
- power-engine utilization: 0.437
- unused active engines: 0.000
- destructive pivots: 0.000
- illegal actions: 0.000

This was a material improvement in survival depth and engine utilization, supporting the timeout fix as causally useful, but the agent remained 0/10.

Postmortem then exposed repeated one-card discard behavior. The D1 discard beam used `discard_width=1`, and `_diverse_discard_beam()` filled that single slot by iterating discard sizes from one upward, structurally preventing larger redraws from entering that beam.

Fix retained pending broader architecture evaluation:
- `7ddf49542e652d9b2583568b693b0761a5e28097` — width one now means best discard candidate overall rather than a one-card discard by construction.

### Batch 3 — after timeout + discard-beam fixes

Repository SHA: `7ddf49542e652d9b2583568b693b0761a5e28097`

- wins: 0/10
- average ante: 2.400
- median ante: 2.000
- power-engine utilization: 0.420
- unused active engines: 0.000
- destructive pivots: 0.000
- illegal actions: 0.000

The third batch did not convert the earlier local fixes into wins and regressed aggregate survival depth relative to Batch 2. Because the sample is small, do not infer that the discard-beam correction is itself harmful from aggregate results alone. Its semantic bug remains real and its focused regression is green.

## Aggregate conclusion

Across the controlled pilot validation:

- total production attempts: 30
- wins: 0
- illegal actions: 0 in all reported batches
- destructive pivots: 0 in all reported batches
- unused active engines: 0 in all reported batches

The result is therefore not primarily an execution-legality failure and cannot be treated as a catalogue-completeness problem.

The production agent is still structurally incompetent at Red Deck / White Stake despite local Bond correctness and several real D1 fixes.

## What this means for the Bond project

The three-pilot work is still valuable: it proved that Bond evidence can form strategy, reach canonical owners, remain bounded by commitment/survival authority, and alter final actions for the intended reason.

It did **not** prove that the overall agent can convert those decisions into winning runs.

Therefore:

1. Do not discard the three-pilot architecture.
2. Do not generalize it across all 46 Bonds yet.
3. Do not apply Tune G or numerical compensation for missing semantics.
4. Do not request more repeated 10-run live batches yet.
5. Audit the core Red/White competence stack offline first.

The remaining Bond catalogue still requires systematic redesign/refurbishment after the production agent demonstrates a viable run-winning baseline. The pilot subset is a proof architecture, not a replacement for catalogue-wide work.

## Active offline audit

The next work item is a run-level competence audit across the canonical owners that dominate White Stake survival.

### A. D1 — hand survival/search

Audit whether:

- candidate generation admits the materially distinct play/discard lines needed to recover;
- shallow/deep expectimax values are comparable and do not privilege horizon artifacts;
- pace semantics correspond to actual remaining score, hands, and discards;
- discard use values redraw opportunity rather than only retained visible structure;
- final-hand/final-discard behavior maximizes actual survival probability;
- timeout and fallback semantics preserve the best trustworthy completed evidence;
- normal search budgets spend time on decision-relevant branches instead of repeatedly timing out in predictable deep horizons.

### B. D2 and shop economy — build acquisition

Audit whether:

- the agent buys enough immediate scoring power early enough to survive Antes 1–3;
- HOLD, BUY, REPLACE, REROLL, voucher, and pack decisions share coherent money/opportunity-cost semantics;
- speculative scaling cannot crowd out mandatory immediate scoring;
- sell/replacement economics correctly compare current joker contribution against admitted candidates;
- strategy/Bond construction bonuses remain bounded and cannot rescue a weak raw purchase;
- the agent can recognize when a run has insufficient scoring and must prioritize raw tempo over engine elegance.

### C. Run-level build progression

Audit whether the current independent canonical owners collectively produce a coherent run trajectory:

`early survival -> first scoring engine -> economy stabilization -> scalable engine -> boss-safe execution`

The key question is no longer only whether each owner is locally sensible. It is whether their combined incentives create enough actual score growth before blind requirements outscale the build.

### D. Telemetry gaps

The current pilot postmortem reports strategy recognition and final decision trails, but terminal ante was not recovered in the per-run summaries (`ante=None`). Before the next live validation, diagnostics should expose enough durable run-level state to classify:

- ante/blind of death;
- score requirement and achieved score on the losing blind;
- money and shop purchases leading into the loss;
- joker set and immediate/scaling contribution before death;
- hands/discards spent in the terminal blind;
- whether the run died from insufficient build power or incorrect hand execution.

## Gate for another live batch

Do not schedule another 10-run batch merely because one more isolated regression turns green.

Resume live validation only after the offline audit identifies and fixes a concrete run-level competence defect with a controlled production counterfactual.

The next batch should answer a specific hypothesis, not act as open-ended debugging.

## Later catalogue phase

After Red/White live validation demonstrates a viable baseline and the three-pilot architecture remains useful in real runs, systematically refurbish the remaining Bond catalogue.

For each Bond, review:

- whether the Bond should exist;
- correct public contributors and literal mechanics;
- meaningful R0–R5 development;
- realization semantics;
- strategy formation/linking;
- FORMING vs PINNED+ authority;
- construction goals and prescriptions;
- correct D1/D2/D3/D4/D9/D11/D14 consumers;
- conflicts, synergies, and motifs;
- realistic reachability;
- whether the production agent can actually act on the Bond rather than merely detect it.
