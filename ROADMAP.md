# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative roadmap/handoff for the Balatro Red/White competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests/live games locally. **Do not run tests or live games from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Every command block shown must end with a trailing blank line after the final command.
- Preserve exact Balatro mechanics, public-state legality, boss rules, and hidden-information boundaries.
- Never use hidden RNG state, seeds, future pool order/identities, or inaccessible information.
- Prefer canonical ownership over late wrappers/rescues.
- Bond/composition and Build Health are evidence/planning layers, never immediate score/action authorities.
- Numerical tuning must not compensate for missing or malformed strategy semantics.

## Objective

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

Canonical authority remains:

```text
Authoritative public state
        ↓
Literal Balatro mechanics
        ↓
Legal candidates
        ↓
Bounded projection
        ↓
One run-winning evaluator
        ↓
One final arbiter
        ↓
Action
```

Canonical owners:

- D1 search/projection: `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`
- D1 arbitration: `StrategyAwareLiveHandActionPolicy`
- D1 orchestration/final return: `LiveHandActionDecisionEngine` / `PathAwareLiveHandActionDecisionEngine`
- D14 SHOP: `BuildAwareShopArbiter`
- D11 reroll: `BuildAwareShopRerollPolicy`
- D9 opened pack: `BalatroPackPolicy`
- D4 consumable acquisition: `ConsumableAcquisitionPolicy`
- D3 voucher acquisition: `VoucherAcquisitionPolicy`

# Current state — 2026-09-01

Phase 5 live semantic validation is complete at **74/74 green**. Phase 6 live/tuning attempts have repeatedly produced **0/10 wins**, including the original baseline and Tunes A–F. Tune A remains provisionally retained; Tunes B–F were rejected/reverted. The D9 Buffoon ownership defect was corrected in `c1f8422` and retained because it is semantically correct, but its controlled live comparison also produced 0/10 wins.

The current investigation therefore moves upstream into the **Bond strategy representation itself**.

The previous `held_retrigger` checkpoint is superseded. It made several Bond-specific structural commitments before the project had established whether the existing Bond abstractions were the right abstractions at all. Do not preserve the current catalogue, current Bond count, current pairwise boundaries, or current rank semantics merely for compatibility.

## Validated checkpoints that remain closed

- Phase 0 authority consolidation: **COMPLETE / 24/24 semantic green**
- Phase 1 D1 survival expansion: **COMPLETE / 33/33 green**
- Phase 2 simple shop survival: **COMPLETE / 42/42 green**
- Phase 3 coherent build evidence: **COMPLETE / 52/52 green**, `BUILD_COHERENCE` 12/12
- Phase 4 resource semantics: **COMPLETE / 70/70**, `RESOURCE_COHERENCE` 18/18
- Phase 5 live D1/D2 semantics: **COMPLETE / 74/74**, `D1_SURVIVAL` 25/25, `SHOP_SURVIVAL` 19/19
- Full deterministic Balatro suite: **GREEN** after the D9 structural correction and stale-contract cleanup
- Phase 6 Tune A first-Joker cash runway: **RETAINED PROVISIONALLY / 0 OF 10 WINS**
- Phase 6 Tunes B–F: **REJECTED / REVERTED**
- Phase 6 D9 Bond-utilization correction: **RETAINED AS CORRECT OWNERSHIP FIX / LIVE 0 OF 10 WINS**
- Sticky public `won` GAME_OVER restart semantics: **VALIDATED** (`28cec27b`, `6e1a2696`)
- Supervisor telemetry resilience: **LOCAL REGRESSION GREEN** (`d22f1b0a`, `cac8fd95`)

Do not stage Tune G or another live batch while Bond redesign is active.

# Phase 6 — BOND ARCHITECTURE REDESIGN — ACTIVE

## Problem statement

The working hypothesis is that the existing Bond system may not represent Balatro strategy well enough for the agent to construct, preserve, and execute consistently winning engines. This is a hypothesis, not a conclusion that every live failure originates in Bond.

The catalogue is believed to contain approximately **46 Bonds** at this checkpoint. **The number 46 is not a design requirement.** After review, Bonds may be deleted, merged, split, or replaced, and new Bonds may be added if actual Balatro mechanics require them.

The redesign objective is not to maximize abstraction or minimize Joker-specific code. It is to create a strategy representation that is mechanically correct, compositional, decision-relevant, and usable by downstream planning without becoming a second score/action authority.

## Core design rule

A Bond is not merely “two things synergize.”

A candidate Bond must represent a **strategically meaningful causal interaction or engine state that changes how the agent should build, preserve, acquire, pivot, or execute a run**.

If an interaction changes only exact score arithmetic and has no independent strategic consequence, it belongs in the canonical score/effect model rather than receiving a separate Bond merely to duplicate scoring.

## Required semantic layers

The redesign must distinguish at least three concepts.

### 1. Literal mechanical primitives

Exact Balatro rules such as:

- trigger phase;
- activation/reset/consumption conditions;
- played-card and held-card effects;
- retrigger semantics;
- enhancement/seal/edition effects;
- Joker copying and Joker-order semantics;
- persistent scaler state;
- deck/hand requirements;
- resource production/consumption.

These are factual game mechanics, not fuzzy Bond strengths.

### 2. Bonds

Bonds represent strategically useful relationships/engine structure derived from mechanics. They must be causal and decision-relevant rather than a bag of pairwise bonuses.

Useful relationship roles may include, where mechanically justified:

- `PRODUCER`
- `REQUIREMENT`
- `PAYOFF`
- `AMPLIFIER`
- `RETRIGGER`
- `COPY`
- `SCALER`
- `ENABLER`
- `CONSUMER`
- `CONVERTER`
- `PROTECTOR`
- `CONFLICT`

The final ontology is not locked by this list. Add/remove roles if the catalogue audit shows a better representation.

### 3. Realized strategy state

The model must separately represent what is structurally being built and how functional that engine is in the current public state.

Examples of realization evidence may include:

- required Joker(s) present;
- required deck density/quality present;
- valid Joker ordering/copy target;
- required hand/play constraint executable;
- enough payoff pieces to matter;
- conflicts currently blocking the engine.

Do not collapse structural development, current realization, and exact projected score into one scalar.

## Directionality and N-way composition

Do not assume Bonds are symmetric pairwise edges.

Many Balatro interactions are directional:

```text
producer → requirement
amplifier → payoff
retrigger → trigger source
copy → resolved target
consumer → resource
conflict → requirement
```

Many important engines are also N-way. The value of `A+B+C` may not equal the sum of all pairwise relationships. Retriggers, held-card effects, copying, Joker ordering, enhancements, seals, and multiplicative effects are primary examples.

Therefore:

- do not encode a complex engine as a pile of static pairwise synergy points if the actual result depends on trigger structure;
- do not create exhaustive Joker-pair/triple tables when exact component mechanics compose correctly;
- explicit exceptional interactions are allowed when generic composition cannot faithfully represent the known game rule.

## Negative interactions are first-class

Distinguish **unrelated** from **actively conflicting**.

The Bond/strategy representation must be able to express conflicts such as:

- competing discard requirements;
- played-versus-held card requirements;
- incompatible hand-shape goals;
- deck destruction of required cards;
- conflicting deck-size incentives;
- resource competition;
- incompatible Joker ordering/copy requirements;
- mutually harmful scaling conditions.

A Frankenstein board of individually positive pieces must not appear coherent merely because negative dependencies are absent from the model.

# Bond specification contract

Before implementation changes are accepted, every retained/replacement Bond should have an explicit specification covering:

1. **Name / identity** — what strategic concept does it represent?
2. **Literal mechanic** — plain Balatro description.
3. **Purpose** — why does the agent need this Bond rather than only exact scoring?
4. **Requirements** — what must exist for it to function?
5. **Producers** — what creates those requirements?
6. **Payoffs** — what benefits from them?
7. **Amplifiers/retriggers/copies** — how the engine compounds.
8. **Trigger phase** — played, scored, held, discard, blind start, round end, shop, etc.
9. **Directionality** — which component acts on which.
10. **Multiplicity** — how repeated triggers/effects compose.
11. **Copy semantics** — Blueprint/Brainstorm or equivalent behavior where relevant.
12. **Negative interactions/conflicts**.
13. **Development semantics** — what structural progress means.
14. **Realization semantics** — what makes the engine currently functional.
15. **Decision consequences** — what the agent should do differently because this Bond exists.
16. **Exact-score ownership** — which canonical evaluator owns numerical scoring effects so Bond does not double count them.
17. **Regression cases** — representative Balatro states that must behave correctly.
18. **Verdict** — `KEEP`, `SPLIT`, `MERGE`, `REPLACE`, or `DELETE`.

If the **decision consequences** cannot be stated meaningfully, question whether the candidate belongs in Bond at all.

# Redesign procedure

## Stage A — inventory the existing catalogue — NEXT

First locate the authoritative catalogue and enumerate every current Bond.

For each existing Bond, record only enough information to classify it before redesign:

- Bond name;
- evaluator/source file;
- current target;
- current contributors/state-derived evidence;
- current rank ladder;
- current realization hook;
- obvious downstream references if needed only to understand its intended purpose.

Do not assume the current name or boundary is correct.

Deliverable: a complete numbered catalogue and count. Verify whether the assumed count is actually 46 on the active branch.

## Stage B — classify before redesigning

Assign each current Bond a preliminary type such as:

- literal mechanic mistakenly promoted to Bond;
- infrastructure/requirement Bond;
- payoff Bond;
- amplifier/retrigger/copy Bond;
- deck-shaping Bond;
- economy/resource Bond;
- hand-shape/hand-level Bond;
- composite engine Bond;
- generic scoring Bond;
- unclear/mixed abstraction.

Also flag obvious overlap, duplication, over-breadth, or missing concepts.

This classification is provisional and exists to determine redesign order, not to protect the current structure.

## Stage C — derive dependency order

Do not audit alphabetically.

Redesign foundational semantics before dependent composite engines. Expected broad order:

1. scoring/play/held trigger primitives represented in Bond;
2. retrigger semantics;
3. copy/order semantics;
4. hand-type/hand-shape requirements;
5. deck composition and deck shaping;
6. discard mechanics;
7. economy/resource engines;
8. scalers/amplifiers;
9. consumable/deck-development support;
10. composite engines and remaining strategy concepts.

Adjust this ordering after inventory if the real catalogue suggests a cleaner dependency graph.

## Stage D — redesign one Bond at a time

For each Bond in dependency order:

1. state the actual Balatro mechanic independently of current code;
2. determine whether a Bond is needed at all;
3. choose `KEEP / SPLIT / MERGE / REPLACE / DELETE`;
4. write the full Bond specification contract above;
5. compare the specification against current implementation;
6. identify required data-model changes before local patches;
7. implement only after the abstraction is accepted;
8. add structural/mechanical regression coverage;
9. checkpoint the roadmap before advancing.

Do not preserve an abstraction merely because other code already consumes it. Consumers will be migrated after the model is correct.

## Stage E — system-level audit after catalogue redesign

Only after all Bonds have been reviewed:

1. global relationship/dependency graph;
2. role ontology;
3. motif/composite-engine formation;
4. realization and strategy formation;
5. StrategyPlan / composer;
6. Build Health boundary;
7. preservation/pivot behavior;
8. D1/D2/D4/D9/D14 consumption;
9. controlled live validation;
10. numerical tuning only after semantic defects are closed.

# Held-retrigger status

`held_retrigger` is no longer automatically the next implementation task.

It remains a useful **stress-test example** because Steel, Red Seal, held effects, Mime, Baron, Blueprint/Brainstorm, Joker ordering, retriggers, and multiplicative scoring expose weaknesses in pairwise/static Bond models. However, do not finalize its current boundary or contributors until inventory/classification determines where held-card primitives, retriggers, King-specific payoff, copy semantics, and composite engine formation belong.

Previous provisional conclusions such as “Baron must belong only to `kings`,” “Mime must belong only to `held_retrigger`,” or “Red-Seal Kings are the correct generic Held-Retrigger evidence” are explicitly reopened. They may still turn out to be correct, but they must now be justified from the redesigned model rather than inherited from the old checkpoint.

# EXACT NEXT ACTION

1. Locate the authoritative Bond catalogue on `feat/v1.0-red-white-competence`.
2. Enumerate every current Bond and verify the exact count.
3. For every Bond, capture its evaluator/file, target, major contributor classes, rank ladder, and realization ownership.
4. Produce a preliminary classification and flag obvious duplicates/mixed abstractions.
5. Derive the redesign dependency order from the real catalogue.
6. Only then select the first Bond for full KEEP/SPLIT/MERGE/REPLACE/DELETE redesign.
7. Do **not** modify Bond implementation, consumer wiring, run another live batch, or stage Tune G before this inventory/classification checkpoint is complete.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 — D1 survival semantic expansion — COMPLETE
3. Phase 2 — simple shop survival — COMPLETE
4. Phase 3 — coherent build evidence/authority quality — COMPLETE
5. Phase 4 — complex packs/consumables/vouchers/economy audit — COMPLETE
6. Phase 5 — live validation — COMPLETE
7. Phase 6 — Bond architecture redesign, then action-quality validation/tuning — ACTIVE

Future stake/deck progression remains blocked until Red/White competence passes.

# Closed / do not reopen without fresh evidence

- Phase-0 ownership migrations and installer retirements
- Phase-1 expansion beyond validated batches absent fresh Phase-5 evidence
- Phase-2 expansion beyond validated batches absent fresh Phase-5 evidence
- Phase-3 authority ownership absent fresh reproducible evidence
- Phase-4 resource semantics absent fresh reproducible evidence
- Phase-5 legality/authority/runtime findings absent fresh reproducible evidence
- Tune-B `$8` pre-Ante-6 paid-reroll runway
- Tune-C `0.50` ordinary Joker replacement margin
- Tune-D `0.20` D8 booster acquisition margin
- Tune-E `0.75` contextual/B3 Joker build weight
- Tune-F `_OBSERVED_HAND_PRIOR_WEIGHT=0.10`
- obsolete `_target_hand_engine_policy_installed` production guard
- Mouth discard-only legality defect
- Green Joker survival-equivalent authority
- Hook/log-resilience search reserve
- historical SHOP recursive expectation roots
- BLIND_SELECT quiescence deadlock
- ROUND_EVAL checkout fast path
- D1 root pre-beam wall-clock defect
- failed-trial tuner cascading
- Phase-A Bond exploratory tuning
- D14/D11 latency blocker absent fresh timing evidence
