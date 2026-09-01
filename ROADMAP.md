# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative roadmap/handoff for the Balatro Red/White competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests/live games locally. **Do not run tests or live games from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Every command block shown must end with a trailing blank after the final command.
- Preserve exact Balatro mechanics, public-state legality, boss rules, and hidden-information boundaries.
- Never use hidden RNG state, seeds, future pool order/identities, or inaccessible information.
- Prefer canonical ownership over late wrappers/rescues.
- Bond/composition and Build Health are evidence/planning layers, never immediate score/action authorities.
- Numerical tuning must not compensate for missing or malformed strategy semantics.
- **Before Bond/strategy work, read `docs/balatro/BALATRO_STRATEGY_SYSTEM.md` and `docs/balatro/BALATRO_RELATIONSHIPS_MOTIFS.md`, then inspect the current implementation.** These documents preserve the Currency-Wars-derived intent of Bonds and motifs; they are historical/design context, not immutable implementation requirements.

## Objective

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

Canonical authority:

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

Canonical owners remain:
- D1 search/projection: `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`
- D1 arbitration: `StrategyAwareLiveHandActionPolicy`
- D1 orchestration/final return: `LiveHandActionDecisionEngine` / `PathAwareLiveHandActionDecisionEngine`
- D14 SHOP: `BuildAwareShopArbiter`
- D11 reroll: `BuildAwareShopRerollPolicy`
- D9 opened pack: `BalatroPackPolicy`
- D4 consumable acquisition: `ConsumableAcquisitionPolicy`
- D3 voucher acquisition: `VoucherAcquisitionPolicy`

# Current state — 2026-09-02

Phase 5 live semantic validation is complete at **74/74 green**. The original baseline and Tunes A–F repeatedly produced **0/10 wins**. Tune A is provisionally retained; B–F were rejected/reverted. The D9 Buffoon ownership correction `c1f8422` is retained as semantically correct but did not improve the controlled live result.

The D1–D14 decision-authority audit is not the current primary target. The observed competence failure is that the agent can have an apparent run direction yet still fail to buy useful pieces, buy unrelated/contradictory pieces, or fail to preserve/use the machinery of that direction.

The broad 46-Bond architecture is therefore **not allowed to expand or receive numerical tuning yet**. Development has moved to a deliberately small vertical proof: first prove that one or a few strategic axes are recognized, alter valuation, and causally alter the final decision for the correct reason. Only then scale the catalogue.

Validated checkpoints that remain closed absent fresh reproducible evidence:
- Phase 0 authority consolidation: complete
- Phase 1 D1 survival expansion: complete
- Phase 2 simple shop survival: complete
- Phase 3 coherent build evidence: complete
- Phase 4 resource semantics: complete
- Phase 5 live D1/D2 semantics: complete
- full deterministic Balatro suite green at the latest checkpoint
- sticky GAME_OVER restart semantics validated
- supervisor telemetry resilience validated

Do not stage Tune G or another live batch while the minimal strategy proof is active.

# Phase 6 — MINIMAL STRATEGY/BOND VERTICAL PROOF — ACTIVE

## Why the plan changed

The previous Phase 6 plan traced six representative builds across the full 46-Bond system. That is useful for later breadth testing, but it does not answer the more basic question quickly enough:

> **Can the agent actually use a strategy representation to make a different and better decision?**

The architecture has been in development long enough that recognition/rank logs are no longer sufficient evidence. A working system must demonstrate a causal chain from public mechanics to the final bounded action.

The current catalogue remains in source for compatibility and rollback. It is **not** treated as validated merely because its Bonds exist or its unit tests pass.

## Minimal canonical flow

```text
public game state
    ↓
literal mechanics
    ↓
strategy/Bond state
    ↓
candidate action values
    ↓
final bounded decision
```

The richer intended architecture still provides the vocabulary:

```text
Development = Bond R0–R5
Realization = DORMANT / PARTIAL / ACTIVE / MATURE
Commitment  = EXPLORATORY / FORMING / PINNED / ESTABLISHED / DOMINANT
```

But every layer must justify itself by observable downstream behavior.

## Authority contract — CURRENT

Commitment is explicitly split into two authority tiers:

### `FORMING` — construction authority only

A `FORMING` strategy may:
- expose a bounded strategy plan;
- identify the next Bond-development target;
- emit specific `seek_feature:*` goals;
- emit specific `seek_component:*` goals for missing motif pieces;
- influence admitted acquisition/development choices through those bounded goals.

A `FORMING` strategy may **not** merely by existing:
- protect components from replacement;
- create pivot resistance;
- dictate hand execution;
- impose preservation prescriptions;
- receive fake `PINNED` authority internally.

### `PINNED+` — preservation/execution authority

A `PINNED`, `ESTABLISHED`, or `DOMINANT` strategy may additionally expose its stronger strategy/motif prescriptions to downstream preservation, replacement, and execution consumers, subject to legality, survival, affordability, boss correctness, and materially stronger alternatives.

The composer must pass the candidate's **real commitment** to the plan builder. No temporary `FORMING → PINNED` promotion is permitted.

## Minimal formation rule — CURRENT

A strategy does not need two different Bonds merely to become visible.

- Positive mechanically enriched evidence may exist at R0.
- A singleton mechanical axis remains `EXPLORATORY` while weak/unestablished.
- An unlocked singleton axis that reaches R1 or at least PARTIAL realization may become `FORMING` at deliberately low confidence.
- Pure `SUPPORT` and/or `DENSITY_INFRASTRUCTURE` evidence cannot form a singleton strategy by itself.
- Singleton evidence does not become `PINNED` merely because it is alone and developed.
- Multi-mechanic semantic links and motifs remain the route to stronger commitment.

This rule exists to prevent the circular failure:

```text
strategy needs multiple linked pieces before it can form
→ no strategy plan exists
→ agent never seeks the missing complementary piece
→ linked strategy never forms
```

## Definition of “the Bond system is working”

The architecture is **not validated** until a small proof set passes all four gates.

### Gate 1 — Recognition

Given a controlled public state, the intended strategic axis is represented correctly.

Example:

```text
Burnt Joker owned
+ target hand has persistent development/evidence
→ Burnt/target-hand direction is represented
```

A nonzero Bond rank alone does not pass this gate.

### Gate 2 — Valuation

The strategy representation must materially change the value of a relevant legal candidate.

Example:

```text
without Burnt strategy evidence:
first discard = ordinary tactical value

with Burnt strategy evidence:
first discard of target hand = bounded future hand-level value
```

The exact numerical magnitude is not tuned yet; the required proof is correct direction and causal ownership.

### Gate 3 — Final decision counterfactual

This is the decisive architecture test:

```text
same public state
same legal actions
same non-strategy evidence
change only the relevant strategy fact
→ final selected action changes when it should
```

The trace must show why the action changed. A strategy object appearing in telemetry while the final action remains unaffected does not pass.

### Gate 4 — Controlled run-level usefulness

Once the deterministic counterfactual passes, a controlled scenario must show the agent using the mechanic coherently over multiple decisions rather than firing a one-step bonus blindly.

For Burnt, for example:
- use the first discard to develop the intended hand when safe;
- preserve enough discards/hands to clear the blind;
- exploit accumulated hand levels;
- stop forcing the development action when survival requires otherwise.

Only after Gates 1–4 are demonstrated may the proof set expand materially.

## Proof-set order

Start with the smallest set that exercises structurally different strategic behavior.

### Proof 1 — Burnt / persistent hand-level development — ACTIVE

Why first:
- Burnt is explicitly allowed by the strategy design as a defining mechanical axis;
- it has a clean causal action consequence in D1;
- it tests long-term development against immediate survival;
- it can produce a strong final-decision counterfactual.

Required trace:

```text
Burnt public mechanic
→ Burnt/target-hand Bond evidence
→ FORMING/PINNED strategy state as appropriate
→ bounded development goal / execution authority as appropriate
→ D1 discard valuation
→ StrategyAwareLiveHandActionPolicy arbitration
→ LiveHandActionDecisionEngine final return
```

**Current handoff:** the strategy metadata/formation-authority slice has been validated green. The work has moved downstream to the decisive question: **does Burnt actually change D1's selected discard/play action?** Do not re-open formation architecture unless the D1 trace produces evidence that the required fact is already missing upstream.

### Proof 2 — simple deck shaping

Use a deck-thinning/destruction axis to prove strategy can influence acquisition/deck construction rather than only D1 execution.

Required outcome:
- removal/thinning support gets positive transition value when it deepens the current strategy;
- unrelated positive Bond development does not receive equivalent value automatically.

### Proof 3 — held-card or persistent-card-state axis

Use a small held-card/Steel-style case to prove persistent card-state strategy and preservation can graduate from FORMING to PINNED without requiring the full Baron-Mime-Steel package.

### Proof 4 — one contradiction

Use a compact incompatible pair such as Burnt/Discard vs No-Discard or Vampire vs preserve-enhancements behavior.

Required outcome:
- the system does not reward both merely because both are individually developed;
- the selected strategy owns the relevant acquisition/preservation consequence.

Do **not** add a fifth/sixth proof axis until these cases demonstrate the full causal contract.

## Current implementation checkpoint

Phase 6A's first core architecture correction is complete and its focused strategy-authority regressions are green:

1. `build_strategy_plan()` accepts `FORMING` rather than blanket-rejecting everything below `PINNED`.
2. `FORMING` plans are construction-only: generated `seek_*` goals are allowed, preservation/execution prescriptions are not.
3. `compose_build()` no longer temporarily promotes motif-backed `FORMING` candidates to `PINNED`.
4. The composer may plan the highest-ranked real `FORMING` candidate when no strategy is pinned.
5. A developed singleton mechanical axis may become low-authority `FORMING`; support/density-only evidence cannot.
6. Focused deterministic regressions validate these authority boundaries.

This proves only that strategy evidence can survive **formation → plan construction**. It does **not** yet prove that D1 candidate valuation or the final D1 arbiter uses Burnt correctly.

### Current diagnostic target

Do not add another abstraction layer yet. Trace the existing D1 production path and find the first point where Burnt's mechanically correct strategic consequence is absent, malformed, or discarded:

```text
Burnt/public state
→ Bond evaluation / realization
→ strategy composition + commitment
→ strategy plan / prescriptions
→ LiveBlindClearPlanner / D1LiveBlindClearPlanner candidate projections
→ StrategyAwareLiveHandActionPolicy candidate values/arbitration
→ LiveHandActionDecisionEngine / PathAwareLiveHandActionDecisionEngine final action
```

At each stage record:
1. What exact Burnt/target-hand fact exists?
2. Is it mechanically correct?
3. Does it distinguish the intended first discard from ordinary tactical discards?
4. Is survival still allowed to override it?
5. Does the consequence survive to the next stage?

The **first** stage where the required consequence disappears owns the defect. Fix that shared owner rather than adding a Burnt-specific late rescue unless Burnt's mechanic itself genuinely requires explicit literal modeling there.

### Counterfactual required before Proof 1 can close

Construct a deterministic pair with:

```text
State A:
Burnt strategic mechanic/evidence absent
same hand, score requirement, hands/discards, legal actions, and all unrelated evidence
→ final action X

State B:
only the relevant Burnt strategic mechanic/evidence present
same remaining public/legal state
→ final action Y
```

`Y` must be the strategically correct change, and removing the Burnt fact must remove that preference again. Also include a survival-pressure variant proving Burnt does **not** force the development discard when that materially jeopardizes clearing the blind.

## Catalogue policy during the proof

- Do not delete the existing 46 Bonds yet.
- Do not assume any existing Bond is correct merely because it remains registered.
- Do not tune Bond rank thresholds.
- Do not add exhaustive relationships.
- Do not add obscure hand/rank/suit Bonds for coverage.
- Do not expand motif inventory to compensate for generic semantic failures.
- A proof-axis Bond may be KEEP/SPLIT/MERGE/REPLACE/DELETE only when its causal trace provides evidence.
- Catalogue expansion is blocked until the minimal proof demonstrates final-decision influence.

## Failure ownership

For each proof, the first incorrect stage owns the defect:

- `MECHANIC_MODEL` — literal mechanic absent/wrong.
- `BOND_REPRESENTATION` — strategic axis loses essential persistent information.
- `ROLE_DESCRIPTOR` — mechanical role/target/condition absent or malformed.
- `SEMANTIC_LINKING` — mechanics are incorrectly connected/disconnected.
- `STRATEGY_FORMATION` — evidence exists but candidate/commitment is wrong.
- `GOAL_PRESCRIPTION` — strategy exists but construction need is missing/wrong.
- `PROJECTED_TRANSITION` — candidate post-action/post-buy state is evaluated incorrectly.
- `CONSUMER_VALUATION` — correct strategy evidence reaches the consumer but does not alter value correctly.
- `FINAL_ARBITRATION` — correct strategic value is lost/overridden at the final authority.

Do not patch a later consumer to compensate for a missing upstream fact.

## Implementation freeze during the proof

Until the four proof gates pass:
- no Bond threshold tuning;
- no Bond-by-Bond catalogue redesign;
- no broad relationship/motif expansion;
- no late shop/preservation rescue layers;
- no Tune G;
- no live tuning batch;
- no D1–D14 ownership changes absent a causal counterexample.

Small semantic corrections, instrumentation, and deterministic causal regressions are allowed because they directly serve the proof.

# EXACT NEXT ACTION

**Next chat should start here; do not repeat the Phase 6A formation work.**

1. Read this roadmap plus the two required strategy docs.
2. Inspect the current Burnt implementation and existing Burnt/strategy tests only as needed to establish the exact upstream fact already available.
3. Locate the production D1 files/classes for:
   - `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`;
   - `StrategyAwareLiveHandActionPolicy`;
   - `LiveHandActionDecisionEngine` / `PathAwareLiveHandActionDecisionEngine`.
4. Trace Burnt end-to-end through those D1 owners. Do not assume metadata reaching the strategy plan means it reaches action valuation.
5. Build the **Burnt final-decision counterfactual regression**: identical public/legal state, toggle only the relevant Burnt strategy fact, require the correct final action to change.
6. Build the paired **survival override regression**: Burnt may improve a development discard, but must lose when that discard materially threatens blind clear.
7. If the counterfactual fails, classify the first break as `PROJECTED_TRANSITION`, `CONSUMER_VALUATION`, `FINAL_ARBITRATION`, or an earlier category if the trace proves the fact was already missing.
8. Fix only that owning layer. Avoid a Burnt-only policy exception if a generic strategy-value channel is the missing architecture.
9. User runs focused tests locally. Any validation command supplied must start with `git pull` and obey the repository command-format contract.
10. Once Burnt Gates 1–3 are green, construct the short controlled Gate-4 scenario. Only after Burnt passes Gate 4 proceed to deck shaping.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 — D1 survival semantic expansion — COMPLETE
3. Phase 2 — simple shop survival — COMPLETE
4. Phase 3 — coherent build evidence/authority quality — COMPLETE
5. Phase 4 — complex packs/consumables/vouchers/economy audit — COMPLETE
6. Phase 5 — live validation — COMPLETE
7. Phase 6A — minimal strategy formation/authority contract — **COMPLETE / GREEN**
8. Phase 6B — Burnt recognition/valuation/final-decision proof — **ACTIVE: D1 FINAL-ACTION TRACE**
9. Phase 6C — 2–4 structurally different proof axes — BLOCKED
10. Phase 6D — catalogue architecture decision and expansion — BLOCKED
11. Phase 6E — action-quality tuning/live validation — BLOCKED

Future stake/deck progression remains blocked until Red/White competence passes.
