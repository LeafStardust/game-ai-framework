# Balatro Production Decision Authority Map

Status: **Phase 0 authority inventory — active**

Purpose: identify every production layer that can materially change an action so
Red/White competence work stops accumulating late rescue policies.

This document is about **authority**, not feature history. Historical implementations
remain retained in `BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`.

## Target rule

For each action family there should eventually be one obvious path:

```text
public state -> mechanics/legality -> candidate projection -> run-winning value -> final arbiter -> action
```

Strategy/Bond state and Build Health are evidence supplied to the evaluator. They
must not become independent final definitions of value. Diagnostics must be read-only.

## Current production installation shape

`games/balatro/__init__.py` installs a long ordered stack of monkeypatch-style policy
wrappers. The final installation order matters because later wrappers can observe,
rescue, veto, or rewrite decisions made by earlier ones.

The existence of this ordering dependency is itself the main Phase-0 risk.

### Authority classes

- **M — Mechanics / legality:** exact Balatro rules, boss legality, forced actions.
- **P — Projection:** estimates consequences of a legal action without selecting it.
- **E — Evaluator:** converts projected consequences into comparable decision evidence.
- **S — Strategy evidence:** Bond/composition, realization, prescriptions, Build Health.
- **A — Arbitration:** chooses among competing legal actions/options.
- **G — Guard/correction:** late veto/rescue/rewrite. These are Phase-0 consolidation targets.
- **D — Diagnostics only:** may observe and report but must never alter action selection.

---

# D1 — play/discard authority

## Canonical core

| Component | Class | Current role | Desired role |
|---|---|---|---|
| `CardSelector` | M | Generates legal play/discard candidates | Keep |
| boss/forced-selection policies | M | Restrict legal candidates according to exact mechanics | Keep authoritative |
| `LiveHandDecisionEvaluator` | E/P | Scores visible play/discard candidates and projects literal scoring | Keep as local semantic evaluator beneath planner |
| `LiveBlindClearPlanner` | A/P | Bounded public-state expectimax; chooses play/discard root action | **Canonical D1 final authority** |
| public draw/outcome models | P | Model distributions without hidden draw order/RNG | Keep |

## Installed D1-affecting wrappers currently surrounding the core

The package installer includes, among others:

- `mouth_hand_policy`
- `boss_hand_constraint_policy`
- `serpent_draw_policy`
- `hook_planner_integration_policy`
- `cerulean_bell_d1_legality_policy`
- `secret_hand_score_authority`
- `d1_log_resilience_policy`
- `d1_candidate_deadline_policy`
- `d1_outer_evaluation_cache_policy`
- `d1_debuff_recovery_policy`
- `safe_pace_optimization_policy`
- `safe_pace_timeout_patch`
- `safe_pace_scope_correction`
- `castle_discard_policy`
- `bond_d1_cache_policy`
- `burnt_bond_execution_policy`
- `pinned_strategy_execution_policy`
- `strategy_authority_correction_policy`
- `live_decision_quality_policy`
- `pinned_strategy_safe_pace_policy`
- `aces_dna_hand_policy`
- `strategy_execution_guard_policy`
- `target_hand_engine_policy`
- `semantic_search_guard_policy`
- `purple_seal_discard_policy`
- `held_round_end_resource_policy`
- `ride_the_bus_execution_policy`
- final `red_white_competence_corrections`

Not all of these are wrong. The Phase-0 question is whether each is M/P/E/S or an
independent G that can alter the final action after the canonical planner has already
applied a different objective.

## Known authority defects already observed

1. **Planner/controller disagreement:** discard candidate pre-ranking used a different
   objective than canonical D1 evaluation. The current late correction redirects
   `_discard_priority` back through the evaluator.
2. **Recovery oscillation:** separate rescue rules have produced both repeated
   one-card discards and later runs that preserved all discards while dying.
3. **Timeout divergence:** timeout/fallback behavior has previously selected actions
   under a different objective from normal search.

## Phase-0 consolidation target for D1

- Exact mechanics/legality stay outside and above value arbitration.
- One planner owns play-vs-discard selection.
- Candidate pruning may remove only mechanically dominated/unusable candidates; it
  must not introduce a second strategic objective.
- Pace, held-card value, generated resources, strategy execution, and discard
  mechanics become terms/evidence visible to the same planner value ordering.
- Late D1 guards should be deleted or reduced to mechanical legality once equivalent
  benchmark-covered semantics exist in the canonical path.

---

# D2 / D14 — shop authority

## Canonical core

| Component | Class | Current role | Desired role |
|---|---|---|---|
| shop action generator | M | Exposes currently legal visible transactions | Keep |
| `JokerBuildValueEvaluator` and literal candidate models | P/E | Candidate Joker consequences | Keep as evidence |
| `PlaybookJokerAcquisitionPolicy` / D2 | E/A | Joker buy/replace/HOLD recommendation | Keep as Joker-family evaluator, not global final arbiter |
| voucher/booster/consumable policies | E | Family-local option evaluation | Keep as evidence providers |
| `BuildAwareShopArbiter` / D14 | A | Compares visible shop actions, reroll, END_SHOP | **Canonical shop final authority** |
| Bond/composition | S | Coherence, realization, disruption, future direction | Evidence only |
| Build Health | S | Survival/immediate/scaling/coherence/runway evidence | Evidence only |

## Installed shop-affecting wrappers currently surrounding the core

Important examples include:

- `post_transaction_joker_value_policy`
- `held_consumable_option_policy`
- `consumable_d14_literal_policy`
- `shop_transaction_policy`
- `voucher_parent_literal_policy`
- `early_capacity_policy`
- `early_spend_sanity_policy`
- `late_shop_resource_guard`
- `deck_growth_pack_policy`
- `pack_sunk_cost_policy`
- family-specific pack expectation policies
- `build_health_policy`
- `shop_clear_probability_health_policy`
- `bond_shop_health_policy`
- `bond_pivot_authority`
- `bond_power_engine_retention_policy`
- `bond_prescription_policy`
- `pinned_strategy_transition/retention/shop_goal` policies
- `strategy_plan_pack_policy`
- `strategy_resource_coherence_policy`
- `stateful_joker_admission_policy`
- `tactical_scaler_retention_policy`
- `full_roster_shop_guard`
- `full_roster_pack_guard`
- `planet_scaler_authority`
- final `red_white_competence_corrections`
- late runtime-only SHOP expectation/competence contracts installed by the supervisor entry point

## Known authority defects already observed

1. **Generic HOLD vs obvious first scoring foothold:** an otherwise positive early
   scorer could be rejected by reserve/adequacy logic.
2. **Rescue overriding semantic veto:** the early scoring rescue initially overrode
   the Scary Face / Ride the Bus canonical conflict, proving rescue authority was too broad.
3. **Cash paralysis:** a rich underpowered build could repeatedly END_SHOP because
   one upstream recommendation object prevented later survival evidence from reopening reroll.
4. **Nested planning/runtime:** hypothetical D2/D14 states and diagnostics launched
   expensive D1/future expectation work even when that work had no final authority.
5. **Legacy bundle logic:** named historical shop-combination logic could compete with
   canonical Bond/composition arbitration until explicitly disabled in production.

## Phase-0 consolidation target for shop

- Family evaluators return facts/options, not final global truth.
- One D14 arbiter compares BUY/REPLACE/voucher/pack/consumable/reroll/END_SHOP on a
  shared run-winning scale.
- Mechanical/Bond incompatibility is a hard semantic constraint where genuine.
- Build Health and Bond changes are terms in the final comparison, not separate
  rescue paths.
- Visible immediate survival outranks speculative future option value when the build
  is underpowered.
- Paid-reroll reserve remains a hard safety constraint; within that constraint,
  underpowered rich states can choose reroll.

---

# D8 / D9 / D10 — packs and consumables

## Desired authority

- Unopened stochastic packs: one-layer public expectation only.
- Opened packs / held consumables: exact currently visible modeled mechanics may be
  evaluated because the choice is now real.
- Hidden future contents, hidden draw order, seed/RNG state are never decision inputs.
- Family-local expectation is evidence submitted to D14; it does not independently
  outrank survival/economy.

Existing detailed implementations remain intact during the competence freeze. They
are audited/reintroduced after D1 and simple shop benchmarks are stable.

---

# Diagnostics / runtime observability

Diagnostics must be **D only**.

Allowed:

- publish current activity;
- record decision latency;
- render Bond/composition and Build Health already computed or cheap diagnostic forms;
- log final decision rationale.

Forbidden:

- launch a second planner whose result can change the action;
- launch expensive survival projection solely to decorate telemetry;
- mutate state or policy objects in a way visible to action selection.

The recent removal of post-decision bounded D1 Build Health projection is the model
for this rule.

---

# Phase-0 consolidation queue

Before deleting any wrapper, first add a semantic benchmark property representing the
behavior it protects.

1. [ ] Tag every D1-affecting installed wrapper M/P/E/S/A/G/D.
2. [ ] Tag every shop-affecting installed wrapper M/P/E/S/A/G/D.
3. [ ] Identify wrappers whose only purpose is a previously observed live defect.
4. [ ] Add benchmark coverage for that defect if absent.
5. [ ] Move the semantics into the canonical D1 planner/evaluator or D14 comparison.
6. [ ] Remove the redundant late wrapper.
7. [ ] Require semantic benchmark non-regression after each consolidation group.

## Current final authorities

Until consolidation is complete:

- **D1:** `LiveBlindClearPlanner.plan()` is the intended final strategic authority,
  subject only to exact mechanics/legality and currently still surrounded by late
  semantic guards that must be consolidated.
- **D2 family:** Joker acquisition/replacement policies produce family-local evidence.
- **D14:** `BuildAwareShopArbiter` is the intended final cross-family shop authority,
  currently still surrounded by Build Health/Bond/late runtime corrections that must
  be consolidated.
- **Execution:** injected bridge executes only the selected legal action; execution
  guards may reject stale/illegal actions but must not invent a second strategy.
- **Diagnostics:** no gameplay authority.
