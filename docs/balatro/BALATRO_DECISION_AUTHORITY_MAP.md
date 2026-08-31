# Balatro Production Decision Authority Map

Status: **Phase 0 authority consolidation complete**

Purpose: document the current production decision owners for Red Deck / White Stake and prevent future competence work from reintroducing late rescue selectors.

Historical wrapper and migration details belong in implementation history and Git history. This file describes **current authority**.

## Global authority rule

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

Bond/composition, Build Health, target-hand intent, and similar strategic models are evidence. They must not become independent final action authorities. Diagnostics are read-only.

---

# D1 — Play / Discard

## Final ownership

| Responsibility | Canonical owner | Authority |
|---|---|---|
| public hand/deck/boss state | canonical live observer → translator → `BalatroState` | observation only |
| legal Play/Discard candidates | action generator + exact boss legality | mechanics |
| public draw outcomes | live draw/outcome models | projection |
| bounded blind-clear search | `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner` | projection/search |
| Play-vs-Discard survival arbitration | `StrategyAwareLiveHandActionPolicy` | **final D1 arbiter** |
| scheduling, confirmation, timeout/fallback, final return | `LiveHandActionDecisionEngine` / path-aware production engine | orchestration/final return |

No production D1 wrapper may independently reverse Play↔Discard or reselect a same-class action after canonical arbitration.

## Native Phase-0 mechanics/evidence now owned by canonical path

- target-hand evidence
- Purple-Seal discard branch preservation
- Blue-Seal round-end consumable generation
- Gold-card final mechanical tie-break
- semantic-search candidate bounds, ordering, deadline checks, and root discard reserve
- The Serpent exact three-card post-action draw rule
- The Hook forced-discard branch refill continuation
- Cerulean Bell forced-selection live-state observation and future forced-selection branching
- Ectoplasm hand-size penalty live state
- round-reset discard-resource live state
- Joker-generation public pool state and observer sequencing
- The Eye / The Mouth exact hand constraints, Mouth discard evidence, and forced legal recovery

These behaviors no longer depend on package-time installation order.

## Retired compatibility surfaces

The following modules may remain importable for old callers/tests, but their installers are no-ops and they are **not production authorities**:

- `purple_seal_discard_policy`
- `held_round_end_resource_policy`
- `semantic_search_guard_policy`
- `serpent_draw_policy`
- `hook_planner_integration_policy`
- `cerulean_live_state_policy`
- `ectoplasm_live_state_policy`
- `round_resource_live_state_policy`
- `joker_generation_pool_live_state_policy`
- `boss_hand_constraint_policy`

Compatibility helpers must not mutate production classes or determine actions.

## D1 evidence-only strategic contributors

These may influence canonical strategy fit or evaluator evidence, but may not become second arbiters:

- Bond/composition intent and realization
- Build Health
- DNA/Ace development evidence
- Castle/Burnt discard evidence
- repetition/target-hand evidence
- held-card/resource preservation evidence

## D1 validation checkpoint

Phase-0 deterministic and semantic validation is green:

- full `tests/balatro` suite: **GREEN**
- Red/White semantic benchmark D1: **13/13**

---

# D14 — SHOP final authority

## Final ownership

| Responsibility | Canonical owner | Authority |
|---|---|---|
| visible legal shop transactions | shop action generation | mechanics |
| Joker admission/replacement | `JokerAcquisitionPolicy` / playbook D2 | family-local evaluator/admission |
| voucher admission | D3 voucher policy | family-local evaluator/admission |
| consumable admission/use | D4 consumable policy | family-local evaluator/admission |
| booster admission | D8 booster policies | family-local evaluator/admission |
| reroll | `BuildAwareShopRerollPolicy` / D11 | family-local evaluator |
| cross-family comparison | `BuildAwareShopArbiter` / D14 | **final SHOP arbiter** |

D14 compares admitted options on one normalized resource scale. Child policies may reject or admit their own family options, but no post-D14 strategy layer may replace the selected action.

## Canonical visible two-Joker planning

`BuildAwareShopArbiter._best_visible_bond_pair(...)` is a bounded D14 candidate generator, not a post-arbiter rescue.

A visible pair is admissible only when:

1. both Jokers are currently visible;
2. both standalone decisions are non-actionable HOLDs with eligible ADD options;
3. buying the first produces a **positive canonical Bond interaction delta** for the second;
4. projected D2 build gain and economics make the second a real BUY;
5. the combined normalized two-step gain competes in D14's ordinary candidate set;
6. execution still buys only the first component, re-observes, and requires fresh D2 admission for the second.

Unrelated speculative pairs remain rejected.

## Shop evidence boundaries

Bond/composition and Build Health may contribute bounded option value beneath D14. They cannot independently admit a rejected family action or post-rewrite the D14 result.

## D14 validation checkpoint

Red/White semantic benchmark SHOP: **9/9**.

---

# D9 — opened pack authority

`BalatroPackPolicy` is the final opened-pack action authority. Pack-specific valuation, strategy prescriptions, and literal mechanics remain subordinate evidence unless a later audit explicitly promotes a canonical owner.

---

# Observation boundary

True public-state adapters belong at the live observer/translator boundary, not in package-time monkeypatch installers.

Phase-0 migrations established this pattern for:

- Cerulean `forced_selection`
- Ectoplasm `ecto_minus`
- round-reset discard state
- Joker-generation public catalogue/pools

Future live-state work should follow the same rule: expose authoritative public state natively, then let mechanics/evaluators consume it.

---

# Phase-0 exit evidence

All Phase-0 authority requirements are satisfied:

- one documented final authority per action family;
- migrated D1 semantics no longer depend on installer/import order;
- retired semantic rescue layers are compatibility-only or gone;
- diagnostics cannot independently plan/change actions;
- focused deterministic regressions protect native behavior;
- full Balatro deterministic suite is green;
- Red/White semantic competence benchmark is **24/24**:
  - `BUILD_COHERENCE`: 2/2
  - `D1_SURVIVAL`: 13/13
  - `SHOP_SURVIVAL`: 9/9

---

# Next authority boundary

Phase 0 is closed. Subsequent competence work should not reopen ownership consolidation without fresh evidence.

The next work should improve **competence under the established authorities**, in roadmap order:

1. semantic benchmark expansion where meaningful;
2. D1 survival competence refinement;
3. simple shop survival;
4. coherent build authority/evidence quality;
5. complex packs/consumables/vouchers/economy audit;
6. live validation;
7. numerical tuning only after semantic evidence warrants it.
