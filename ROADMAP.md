# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative roadmap/handoff for the Balatro Red/White competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests/live games locally. **Do not run tests or live games from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Every focused pytest validation command must use `-q`.
- Every command block shown must end with a trailing blank after the final command.
- Preserve exact Balatro mechanics, public-state legality, boss rules, and hidden-information boundaries.
- Never use hidden RNG state, seeds, future pool order/identities, or inaccessible information.
- Prefer canonical ownership over late wrappers/rescues.
- Bond/composition and Build Health are evidence/planning layers, never immediate score/action authorities.
- Numerical tuning must not compensate for missing or malformed strategy semantics.
- **Before Bond/strategy work, read `docs/balatro/BALATRO_STRATEGY_SYSTEM.md` and `docs/balatro/BALATRO_RELATIONSHIPS_MOTIFS.md`, then inspect the current implementation.**
- Use scoped Conventional Commit messages such as `docs(balatro): ...`, `fix(balatro): ...`, `test(balatro): ...`, `feat(balatro): ...`, and `tune(balatro): ...`.

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

The broad 46-Bond architecture remains frozen from expansion and numerical tuning. Phase 6 is a deliberately small vertical proof: prove that strategic evidence is recognized, changes valuation, and causally changes the correct downstream decision before scaling the catalogue.

Validated checkpoints that remain closed absent fresh reproducible evidence:
- Phase 0 authority consolidation: complete
- Phase 1 D1 survival expansion: complete
- Phase 2 simple shop survival: complete
- Phase 3 coherent build evidence: complete
- Phase 4 resource semantics: complete
- Phase 5 live D1/D2 semantics: complete
- Phase 6A strategy formation/authority contract: complete/green
- Phase 6B Proof 1 Burnt vertical: complete/green
- Phase 6C Proof 2 deck shaping transition: complete/green
- sticky GAME_OVER restart semantics validated
- supervisor telemetry resilience validated

Do not stage Tune G or another live batch while the minimal strategy proof is active.

# Phase 6 — MINIMAL STRATEGY/BOND VERTICAL PROOF — ACTIVE

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

The architecture vocabulary remains:

```text
Development = Bond R0–R5
Realization = DORMANT / PARTIAL / ACTIVE / MATURE
Commitment  = EXPLORATORY / FORMING / PINNED / ESTABLISHED / DOMINANT
```

Every layer must justify itself by observable downstream behavior.

## Authority contract — CURRENT

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

A `PINNED`, `ESTABLISHED`, or `DOMINANT` strategy may additionally expose stronger strategy/motif prescriptions to downstream preservation, replacement, and execution consumers, subject to legality, survival, affordability, boss correctness, and materially stronger alternatives.

The composer must pass the candidate's **real commitment** to the plan builder. No temporary `FORMING → PINNED` promotion is permitted.

## Minimal formation rule — CURRENT

- Positive mechanically enriched evidence may exist at R0.
- A singleton mechanical axis remains `EXPLORATORY` while weak/unestablished.
- An unlocked singleton axis that reaches R1 or at least PARTIAL realization may become `FORMING` at deliberately low confidence.
- Pure `SUPPORT` and/or `DENSITY_INFRASTRUCTURE` evidence cannot form a singleton strategy by itself.
- Singleton evidence does not become `PINNED` merely because it is alone and developed.
- Multi-mechanic semantic links and motifs remain the route to stronger commitment.

## Four proof gates

### Gate 1 — Recognition

Controlled public state must represent the intended strategic axis correctly. A nonzero Bond rank alone is insufficient.

### Gate 2 — Valuation

The strategy representation must materially change the value of a relevant legal candidate in the correct direction.

### Gate 3 — Final decision counterfactual

```text
same public state
same legal actions
same non-strategy evidence
change only the relevant strategy fact
→ final selected action changes when it should
```

### Gate 4 — Controlled run-level usefulness

A controlled deterministic scenario must show coherent behavior across multiple decisions rather than a one-step bonus.

# Proof-set status

## Proof 1 — Burnt / persistent hand-level development — COMPLETE / GREEN

Required trace:

```text
Burnt public mechanic
→ Burnt/target-hand Bond evidence
→ bounded development authority
→ D1 discard valuation
→ StrategyAwareLiveHandActionPolicy arbitration
→ final D1 action
→ observed persistent hand-level gain
→ later exploitation of that gain
```

Validated evidence:
- Recognition and target-hand semantics are covered by Burnt Bond tests.
- Native D1 Burnt evidence distinguishes the target first discard from a generic discard.
- Final-decision counterfactual is green.
- Survival override is green.
- `FINAL_ARBITRATION` defect was corrected so consensus recovery cannot erase canonical D1 strategy ordering.
- Controlled Gate 4 sequence is green locally:
  1. first safe discard develops the intended High Card;
  2. public `hand_levels` records the persistent Burnt result;
  3. canonical scoring makes the developed High Card the preferred later play;
  4. when hands are critical and the play clears the blind, Burnt development pressure switches off and survival wins.

Relevant regressions:
- `tests/balatro/test_balatro_d1_burnt_native_evidence.py`
- `tests/balatro/test_balatro_d1_burnt_final_arbitration.py`
- `tests/balatro/test_balatro_d1_burnt_controlled_sequence.py`
- `tests/balatro/test_balatro_path_aware_hand_action_engine.py`

Do not reopen Burnt unless fresh reproducible evidence contradicts these results.

## Proof 2 — simple deck shaping — COMPLETE / GREEN

Purpose: prove strategy can influence acquisition/deck construction rather than only D1 execution.

Validated outcome:
- Erosion forms a low-authority `FORMING` deck-thinning strategy.
- Trading Card materially deepens that strategy and establishes the canonical `Card Destruction ↔ Deck Thinning` synergy.
- An unrelated positive Three-of-a-Kind Bond transition does not receive equivalent transition value automatically.
- Standalone Trading Card is allowed to be intrinsically coherent because it genuinely supplies both destruction and thinning; Proof 2 does not require it to be weak in isolation.

Relevant regression:
- `tests/balatro/test_balatro_deck_thinning_strategy_transition.py`

The focused deck-thinning transition validation was reported green locally. No production patch was required for this proof slice.

## Proof 3 — held-card / persistent-card-state preservation — ACTIVE

Use a small held-card/Steel-style case to prove persistent card-state strategy can graduate from construction authority to preservation authority without requiring the full Baron-Mime-Steel package.

Required causal shape:

```text
public held-card / persistent-card mechanics
→ Bond evidence + semantic links
→ coherent strategy candidate
→ FORMING while evidence is insufficient for preservation
→ PINNED+ when the engine is coherent enough
→ canonical preservation/replacement consumer changes its choice
```

Required counterfactual:
- baseline/no relevant strategy: ordinary legal/safe choice;
- `FORMING`: construction influence may exist, but no categorical preservation merely from commitment;
- `PINNED+`: strategy-relevant persistent card/component is preserved among otherwise safe/near-equivalent choices;
- removing the relevant strategy fact removes the preservation preference;
- legality, exact survival, affordability, boss correctness, and materially stronger alternatives remain superior authorities.

Do **not** add a late preservation rescue. Locate the existing canonical preservation/replacement owner and feed it existing strategy authority there.

## Proof 4 — one contradiction — BLOCKED ON PROOF 3

Use a compact incompatible pair such as Burnt/Discard vs No-Discard or Vampire vs preserve-enhancements behavior.

Required outcome:
- the system does not reward both merely because both are individually developed;
- the selected strategy owns the relevant acquisition/preservation consequence.

Do not add a fifth/sixth proof axis until Proofs 1–4 demonstrate the full causal contract.

# Current implementation checkpoint

1. `build_strategy_plan()` accepts `FORMING` rather than blanket-rejecting everything below `PINNED`.
2. `FORMING` plans are construction-only: generated `seek_*` goals are allowed, preservation/execution prescriptions are not.
3. `compose_build()` no longer temporarily promotes motif-backed `FORMING` candidates to `PINNED`.
4. The composer may plan the highest-ranked real `FORMING` candidate when no strategy is pinned.
5. A developed singleton mechanical axis may become low-authority `FORMING`; support/density-only evidence cannot.
6. Burnt Proof 1 now demonstrates recognition → valuation → final decision → multi-decision usefulness.
7. Deck-shaping Proof 2 demonstrates aligned acquisition transition value without automatically rewarding unrelated Bond development.

The next unresolved boundary is **PINNED preservation authority** for a persistent-card/held-card strategy.

## Current diagnostic target

Trace the first existing canonical consumer that destroys, replaces, discards, sells, or otherwise sacrifices a persistent strategy-relevant card/component. Determine whether it can already observe:
- current `Composition.strategy_plan`;
- candidate commitment (`FORMING` vs `PINNED+`);
- existing preservation prescriptions/card relevance;
- legality/survival constraints.

Fix the first owning layer where correct `PINNED+` preservation evidence is lost. Do not grant preservation to `FORMING` merely to make the proof pass.

## Catalogue policy during the proof

- Do not delete the existing 46 Bonds yet.
- Do not assume any existing Bond is correct merely because it remains registered.
- Do not tune Bond rank thresholds.
- Do not add exhaustive relationships.
- Do not expand motif inventory to compensate for generic semantic failures.
- Catalogue expansion is blocked until the minimal proof demonstrates the required causal effects.

## Failure ownership

For each proof, the first incorrect stage owns the defect:
- `MECHANIC_MODEL` — literal mechanic absent/wrong.
- `BOND_REPRESENTATION` — strategic axis loses essential persistent information.
- `ROLE_DESCRIPTOR` — mechanical role/target/condition absent or malformed.
- `SEMANTIC_LINKING` — mechanics are incorrectly connected/disconnected.
- `STRATEGY_FORMATION` — evidence exists but candidate/commitment is wrong.
- `GOAL_PRESCRIPTION` — strategy exists but construction/preservation need is missing/wrong.
- `PROJECTED_TRANSITION` — candidate post-action/post-buy state is evaluated incorrectly.
- `CONSUMER_VALUATION` — correct strategy evidence reaches the consumer but does not alter value correctly.
- `FINAL_ARBITRATION` — correct strategic value is lost/overridden at the final authority.

Do not patch a later consumer to compensate for a missing upstream fact.

## Implementation freeze during the proof

Until Proofs 1–4 pass:
- no Bond threshold tuning;
- no Bond-by-Bond catalogue redesign;
- no broad relationship/motif expansion;
- no late shop/preservation rescue layers;
- no Tune G;
- no live tuning batch;
- no D1–D14 ownership changes absent a causal counterexample.

Small semantic corrections, instrumentation, and deterministic causal regressions are allowed because they directly serve the proof.

# EXACT NEXT ACTION

1. Read this roadmap plus the two required strategy docs.
2. Treat Burnt Proof 1 and deck-shaping Proof 2 as closed/green unless fresh evidence contradicts them.
3. Inspect held-card/Steel Bond definitions, semantic descriptors, strategy composition, and existing preservation prescriptions.
4. Locate the canonical preservation/replacement consumer that can exercise persistent-card strategy authority.
5. Build the shortest deterministic Proof 3 counterfactual covering baseline, `FORMING`, and `PINNED+`.
6. Verify `FORMING` does not gain preservation authority.
7. Verify `PINNED+` changes an otherwise safe/near-equivalent preservation/replacement decision for the correct strategy reason.
8. Verify legality/survival/materially stronger alternatives still override preservation.
9. If the proof fails, classify and fix the first owning layer only.
10. User runs focused tests locally. Validation commands must start with `git pull`, use `pytest -q`, and obey the repository command-format contract.
11. Only after Proof 3 is green proceed to the contradiction proof.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 — D1 survival semantic expansion — COMPLETE
3. Phase 2 — simple shop survival — COMPLETE
4. Phase 3 — coherent build evidence/authority quality — COMPLETE
5. Phase 4 — complex packs/consumables/vouchers/economy audit — COMPLETE
6. Phase 5 — live validation — COMPLETE
7. Phase 6A — minimal strategy formation/authority contract — **COMPLETE / GREEN**
8. Phase 6B — Burnt vertical proof — **COMPLETE / GREEN**
9. Phase 6C — deck-shaping transition proof — **COMPLETE / GREEN**
10. Phase 6D — held-card/persistent-card preservation proof — **ACTIVE**
11. Phase 6E — contradiction proof — BLOCKED
12. Phase 6F — catalogue architecture decision and expansion — BLOCKED
13. Phase 6G — action-quality tuning/live validation — BLOCKED

Future stake/deck progression remains blocked until Red/White competence passes.
