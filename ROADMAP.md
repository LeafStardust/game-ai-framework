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

The broad 46-Bond architecture remains frozen from expansion and numerical tuning. Phase 6's deliberately small vertical proof is now **complete/green**: strategic evidence has been shown to be recognized, to change bounded valuation, to change canonical downstream decisions, to gain preservation authority only after PINNED commitment, and to respect explicit contradictions.

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
- Phase 6D Proof 3 held-card preservation: complete/green
- Phase 6E Proof 4 contradiction handling: complete/green
- sticky GAME_OVER restart semantics validated
- supervisor telemetry resilience validated

Do not stage Tune G or another live batch until the catalogue architecture decision below is complete.

# Phase 6 — MINIMAL STRATEGY/BOND VERTICAL PROOF — COMPLETE / GREEN

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

## Authority contract — VALIDATED

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

## Minimal formation rule — VALIDATED

- Positive mechanically enriched evidence may exist at R0.
- A singleton mechanical axis remains `EXPLORATORY` while weak/unestablished.
- An unlocked singleton axis that reaches R1 or at least PARTIAL realization may become `FORMING` at deliberately low confidence.
- Pure `SUPPORT` and/or `DENSITY_INFRASTRUCTURE` evidence cannot form a singleton strategy by itself.
- Singleton evidence does not become `PINNED` merely because it is alone and developed.
- Multi-mechanic semantic links and motifs remain the route to stronger commitment.

# Proof-set status

## Proof 1 — Burnt / persistent hand-level development — COMPLETE / GREEN

Validated trace:

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

Validated outcome:
- Erosion forms a low-authority `FORMING` deck-thinning strategy.
- Trading Card materially deepens that strategy and establishes the canonical `Card Destruction ↔ Deck Thinning` synergy.
- An unrelated positive Three-of-a-Kind Bond transition does not receive equivalent transition value automatically.
- Standalone Trading Card is allowed to be intrinsically coherent because it genuinely supplies both destruction and thinning.

Relevant regression:
- `tests/balatro/test_balatro_deck_thinning_strategy_transition.py`

No production patch was required for this proof slice.

## Proof 3 — held-card / persistent-card-state preservation — COMPLETE / GREEN

Validated causal boundary:
- the canonical owner is `StrategyAwareLiveHandActionPolicy`, not a late preservation rescue;
- `FORMING` has no held-card preservation authority;
- `PINNED` held-card evidence contributes within the normal safe/equivalent D1 ordering;
- PINNED preservation changes the final discard from a held-engine King to an unrelated card when survival evidence is equal;
- deterministic survival still overrides preservation and may spend the held-engine card when required.

Relevant regressions:
- `tests/balatro/test_balatro_d1_pinned_held_card_preservation.py`
- `tests/balatro/test_balatro_d1_pinned_held_card_final_action.py`

No new late arbitration layer was added.

## Proof 4 — contradiction handling — COMPLETE / GREEN

Canonical case: `Burnt × No-Discard`.

Validated outcome:
- the relationship is explicitly `CONFLICT`;
- composer selection does not keep both conflicting Bonds in the selected composition;
- reinforcing the selected No-Discard direction receives positive transition value;
- opening the conflicting Burnt axis does not receive equivalent positive D2 structural reward merely because Burnt itself develops;
- the first failed regression exposed a real `CONSUMER_VALUATION` defect in `_bond_transition_bonus`;
- `9027577` fixed that owner by suppressing positive structural alignment for newly introduced conflicts with the current selected composition, while retaining an escape for a materially stronger PINNED pivot.

Relevant regression:
- `tests/balatro/test_balatro_conflicting_strategy_transition.py`

# Phase 6F — CATALOGUE ARCHITECTURE DECISION — ACTIVE

The minimal causal architecture is now proven. The next task is **not** to blindly expand or tune all 46 Bonds. First decide which frozen catalogue entries genuinely fit the validated architecture.

## Decision questions

For each existing Bond family, determine whether it is:
1. a real persistent/developable strategic axis that should remain a Bond;
2. better represented as a contributor/state feature to another Bond;
3. better represented only as a semantic role/link;
4. better represented as a motif/package above Bonds;
5. redundant or mechanically malformed and should be removed/reworked.

The audit must use the four validated proof properties as the admission standard:
- recognizable from public mechanics before completion;
- changes bounded acquisition/development valuation;
- can causally reach the correct downstream consumer when authority permits;
- respects conflicts and stronger survival/material alternatives.

## Catalogue policy during the architecture decision

- Do not tune rank thresholds yet.
- Do not add exhaustive relationships.
- Do not expand motif inventory merely to rescue generic semantic failures.
- Do not assume a frozen Bond is valid because tests mention it.
- Prefer deleting/merging malformed abstractions over adding more special-case consumers.
- Preserve literal Joker/mechanic coverage even when a Bond abstraction is removed.
- No Tune G or live batch until the catalogue shape is decided and focused regressions are green.

## Failure ownership remains

- `MECHANIC_MODEL` — literal mechanic absent/wrong.
- `BOND_REPRESENTATION` — strategic axis loses essential persistent information.
- `ROLE_DESCRIPTOR` — mechanical role/target/condition absent or malformed.
- `SEMANTIC_LINKING` — mechanics are incorrectly connected/disconnected.
- `STRATEGY_FORMATION` — evidence exists but candidate/commitment is wrong.
- `GOAL_PRESCRIPTION` — strategy exists but construction/preservation need is missing/wrong.
- `PROJECTED_TRANSITION` — candidate post-action/post-buy state is evaluated incorrectly.
- `CONSUMER_VALUATION` — correct strategy evidence reaches the consumer but does not alter value correctly.
- `FINAL_ARBITRATION` — correct strategic value is lost/overridden at the final authority.

# EXACT NEXT ACTION

1. Read this roadmap plus `docs/balatro/BALATRO_STRATEGY_SYSTEM.md` and `docs/balatro/BALATRO_RELATIONSHIPS_MOTIFS.md`.
2. Treat Proofs 1–4 as closed/green unless fresh reproducible evidence contradicts them.
3. Inventory the frozen 46 Bond IDs, their evaluators, mechanical roles/targets/conditions, relationships, motif participation, and downstream consumers.
4. Classify each Bond as `KEEP`, `MERGE/CONTRIBUTOR`, `ROLE-ONLY`, `MOTIF-ONLY`, or `REMOVE/REWORK`, with a short mechanical reason.
5. Start with architecture-level duplicates or category mistakes rather than numerical thresholds.
6. Apply only the smallest structural corrections needed to make the catalogue conform to the validated architecture.
7. Add focused regressions for every removal/merge that could change strategy formation or downstream valuation.
8. User runs focused tests locally; all validation commands must begin with `git pull` and focused pytest commands must use `-q`.
9. After catalogue architecture is stable/green, reassess whether rank-threshold calibration is needed.
10. Only then consider action-quality tuning / Tune G / another live validation batch.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 D1 survival semantic expansion — COMPLETE
3. Phase 2 simple shop survival — COMPLETE
4. Phase 3 coherent build evidence/authority quality — COMPLETE
5. Phase 4 complex packs/consumables/vouchers/economy audit — COMPLETE
6. Phase 5 live validation — COMPLETE
7. Phase 6A minimal strategy formation/authority contract — **COMPLETE / GREEN**
8. Phase 6B Burnt vertical proof — **COMPLETE / GREEN**
9. Phase 6C deck-shaping transition proof — **COMPLETE / GREEN**
10. Phase 6D held-card/persistent-card preservation proof — **COMPLETE / GREEN**
11. Phase 6E contradiction proof — **COMPLETE / GREEN**
12. Phase 6F catalogue architecture decision — **ACTIVE**
13. Phase 6G action-quality tuning/live validation — BLOCKED

Future stake/deck progression remains blocked until Red/White competence passes.
