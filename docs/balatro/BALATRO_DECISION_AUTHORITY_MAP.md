# Balatro Production Decision Authority Map

Status: **Phase 0 authority inventory — active**

Purpose: identify every production layer that can materially change an action so Red/White competence work stops accumulating late rescue policies.

This document is about **authority**, not feature history. Historical implementations remain retained in `BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md`.

## Target rule

For each action family there should eventually be one obvious path:

```text
public state -> mechanics/legality -> candidate projection -> run-winning value -> final arbiter -> action
```

Strategy/Bond state and Build Health are evidence supplied to the evaluator. They must not become independent final definitions of value. Diagnostics must be read-only.

## Current production installation shape

`games/balatro/__init__.py` still installs an ordered stack of monkeypatch-style policy/runtime helpers. D1 is now materially narrower than the historical stack: the surviving strategy/Joker layers contribute evidence, exact mechanics, projection, caching, or bounded-search behavior rather than owning independent post-policy Play/Discard selectors. Removing the remaining implementation-order dependency is still a Phase-0 objective.

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

The live runner calls `PathAwareLiveHandActionDecisionEngine.decide(state)` through the production runtime. The engine owns adaptive-search scheduling and timeout handling. `LiveBlindClearPlanner` produces bounded plan evidence; `StrategyAwareLiveHandActionPolicy` owns Play-vs-Discard survival arbitration.

| Component | Class | Current role | Desired role |
|---|---|---|---|
| `CardSelector` | M | Generates legal play/discard candidates | Keep |
| boss/forced-selection mechanics | M | Restrict legality or exact score semantics | Keep authoritative |
| `LiveHandDecisionEvaluator` | P/E | Literal current-action projection and local recovery evidence | Keep beneath D1 arbitration |
| `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner` | P/E | Bounded public-state expectimax and plan values; discard beam pre-ranking uses canonical evaluator evidence directly | **Canonical D1 projection/search authority** |
| `StrategyAwareLiveHandActionPolicy` | A | Owns canonical safe-pace clear / pace-play / recovery arbitration and score/survival-equivalent strategy refinement | **Canonical D1 Play-vs-Discard arbiter** |
| `PathAwareLiveHandActionDecisionEngine` | A | Owns search schedule, confirmation, timeout/fallback and final return | **Canonical D1 orchestration/final-return authority** |
| public draw/outcome models | P | Model distributions without hidden draw order/RNG | Keep |

Strategy/Joker hooks may contribute candidate evidence only where explicitly justified. They may not independently reverse Play↔Discard or reselect a same-class candidate after canonical arbitration.

## Inspected wrapper classification

| Wrapper | Class | Finding | Consolidation direction |
|---|---|---|---|
| `boss_hand_constraint_policy` | **M + S** | Eye/Mouth exact constraints filter candidates before arbitration. Locked-Mouth redraw structure/width is now strategy evidence; the old post-selection discard rewrite is removed | Keep exact boss filtering; eventually move filter integration directly into candidate generation |
| retired production `mouth_hand_policy` | **historical S + A/G** | First-hand Mouth logic previously performed a separate same-class selector after canonical D1 | **Retired from production:** canonical Bond/strategy evidence plus exact Mouth constraints now own the behavior |
| `serpent_draw_policy` | **M + P** | Models The Serpent's exact draw-count consequence | Keep; mechanics/projection only |
| `hook_planner_integration_policy` | **M + P** | Models The Hook's mandatory two-card discard in successor projection | Keep; mechanics/projection only |
| `cerulean_bell_d1_legality_policy` | **M + G** | Enforces forced-card legality for Cerulean Bell | Keep exact legality; eventually prefer direct candidate-generation integration over late guard shape |
| retired production `d1_candidate_deadline_policy` installer | **P/runtime utility** | Its `_candidate_actions` patch was always overwritten later by `semantic_search_guard_policy`; only deadline/ranking helper functions are still consumed | **Installer retired:** keep helpers until bounded search is native |
| `d1_outer_evaluation_cache_policy` | **P runtime** | Memoizes repeated public-state/action evaluation during one outer search | Keep performance semantics; eventually make cache native rather than monkeypatched |
| `d1_log_resilience_policy` | **E + runtime** | Boss-unconfirmed exactness is downgraded and search reserve is bounded. Its former hard-coded late Play→Discard rewrites were removed | Keep confidence/runtime safeguards only; no independent action arbitration |
| retired `d1_debuff_recovery_policy` | **E** | Bounded preference for discarding currently debuffed cards was valid recovery evidence, but the monkeypatch wrapper was unnecessary | **Consolidated:** evidence now lives directly in `LiveHandDecisionEvaluator._discard_value`; installer/file removed |
| `safe_pace_timeout_patch` | **P/runtime** | Seeds a bounded horizon-1 root before adaptive search. Its former duplicate completed-root timeout selector was removed; completed bootstrap evidence is fed to canonical timeout history | Keep bounded bootstrap only; eventually move bootstrap scheduling into the engine directly |
| retired `safe_pace_scope_correction` | **A** | Previously owned production safe-pace Play-vs-Discard scope as a late wrapper | **Consolidated:** safe-pace arbitration lives directly in `StrategyAwareLiveHandActionPolicy` |
| `safe_pace_optimization_policy` | **P/runtime** | Installs only the bounded adaptive-search schedule; it no longer patches action arbitration | Keep bounded schedule semantics; eventually make schedule native rather than monkeypatched |
| retired `pinned_strategy_safe_pace_policy` | **S + A/G** | Previously re-selected PACE_PLAY after canonical policy using a score/survival-equivalence band | **Consolidated:** equivalence semantics live directly in `StrategyAwareLiveHandActionPolicy` |
| `semantic_search_guard_policy` | **P + runtime** | Bounds root/child candidate generation and preserves compact made-hand representatives. Stale no-discard helper coupling has been removed | Preserve bounded candidate semantics; migrate search behavior into planner directly |
| `secret_hand_score_authority` | **M + P/E** | Adds exact vanilla base scores for secret hands and representative D2 probes; it does not choose D1 actions | Keep mechanics; eventually move score table into canonical scorer definition |
| `castle_discard_policy` | **M/S evidence** | Castle current-suit progression augments discard strategy fit only; it no longer replaces the selected DISCARD | Keep evidence semantics; eventually move helper directly into canonical strategy policy |
| `bond_d1_cache_policy` | **S/runtime** | Caches immutable Bond hand-intent evidence for one D1 decision; no independent action objective | Keep performance semantics; make cache native to strategy-aware policy when practical |
| `burnt_bond_execution_policy` | **S/E evidence** | Burnt first-discard permanent hand-level growth augments discard strategy fit only; it no longer replaces a selected DISCARD | Keep as evidence helper; eventually fold directly into canonical strategy policy |
| `aces_dna_hand_policy` | **S evidence** | DNA linked-rank duplication, DNA+Scholar Ace setup, and Ace development augment PLAY strategy fit only | Keep as evidence helper; eventually fold directly into canonical strategy policy |
| `strategy_execution_guard_policy` | **S evidence** | Hand-repetition realization augments PLAY strategy fit only. Redundant no-discard PLAY re-selection was removed | Keep as evidence helper; eventually fold directly into canonical strategy policy |
| `target_hand_engine_policy` | **M/S evidence** | Runner/To Do List target-hand mechanics augment PLAY strategy fit only | Keep as evidence helper; eventually fold directly into canonical strategy policy |
| `purple_seal_discard_policy` | **M + P** | Preserves mechanically distinct Purple-Seal Tarot-generation discard branches through bounded child/root beams; it does not assign final utility or choose D1 action | Keep beam-coverage semantics; migrate candidate generation directly into `D1LiveBlindClearPlanner` |
| `held_round_end_resource_policy` | **M + P/E** | Projects exact Blue-Seal round-end generation and uses Gold-card retention only as a final equal-value ordering term; it does not post-rewrite chosen action | Keep literal resource semantics; move projection/priority behavior into canonical planner implementation |
| retired production `ride_the_bus_execution_policy` | **historical M/E + A/G** | Previously switched terminal guaranteed PLAY after arbitration to preserve an accumulated Bus stack | **Consolidated:** Bus preservation now lives in canonical safe-equivalent-clear ordering beneath generated resources/Gold and above irrelevant overkill |
| `pinned_strategy_execution_policy` | **S/E** for packs, not D1 | Augments already-positive pack options with pinned missing-feature evidence and motif prescriptions | Exclude from D1 queue; audit under D8/D14 |
| `strategy_authority_correction_policy` | **S/E** for composition/shop/pack, not D1 | Corrects premature strategy commitment and adds bounded missing-piece recruitment evidence | Exclude from D1 queue; audit under composition/D8/D14 |
| `live_decision_quality_policy` | **G** for D8/B4/D9, not D1 | Does not own play/discard selection | Exclude from D1 consolidation; audit later under pack/shop phase |
| final `red_white_competence_corrections` | **G**, shop only | D1 multi-card redraw and planner discard pre-ranking have both been migrated out | Audit/migrate remaining behavior during D14 consolidation; it no longer owns D1 authority |

Classification is evidence-based. At this checkpoint no installed strategy/Joker D1 layer intentionally owns a second post-policy Play/Discard or same-class selector. Remaining D1 consolidation is primarily exact-mechanics integration and runtime/projection plumbing.

## D1 authority defects and disposition

1. **Planner/controller disagreement:** resolved. `LiveBlindClearPlanner._discard_priority` uses canonical `LiveHandDecisionEvaluator.evaluate(...)` directly; semantic case `d1.authority.candidate_beam` protects this boundary.
2. **Recovery oscillation:** multi-card redraw efficiency lives in canonical `LiveHandDecisionEvaluator`, while planner discard beam admission uses the same evaluator. Continue watching live behavior rather than adding a second objective.
3. **Timeout divergence:** path-aware production retains completed canonical D1 evidence; `d1.authority.timeout_consistency` protects this. The older duplicate timeout selector is removed.
4. **Post-policy cross-class reversal:** retired. Semantic cases `d1.authority.action_class`, `d1.authority.canonical_safe_pace`, and `d1.authority.mouth_action_class` protect ownership.
5. **Debuffed-card recovery wrapper:** resolved in `LiveHandDecisionEvaluator`.
6. **Log-resilience second arbiter:** resolved; only confidence/runtime safeguards remain.
7. **Safe-pace strategy second pass:** resolved in `StrategyAwareLiveHandActionPolicy`.
8. **Burnt/Castle same-class selectors:** resolved. Both are evidence-only strategy-fit hooks.
9. **DNA/target-hand/repetition same-class selectors:** resolved. These mechanics are evidence-only strategy-fit hooks.
10. **Multi-card redraw late correction:** resolved in canonical evaluator.
11. **Ride the Bus terminal second selector:** resolved. Canonical safe-equivalent-clear ordering preserves generated consumables and Gold before Bus stack, and Bus before irrelevant overkill; semantic case `d1.resources.bus_terminal_hierarchy` protects the hierarchy.
12. **Locked-Mouth redraw second selector:** resolved. Exact Mouth legality remains mechanical; redraw structure/width is evidence-only and protected by `d1.boss.mouth_redraw_evidence`.
13. **Redundant root deadline installer:** resolved. The overwritten installer is retired; shared deadline helpers remain for the active bounded-search layer.

## Phase-0 consolidation target for D1

- Exact mechanics/legality stay outside and above value arbitration.
- `LiveBlindClearPlanner` owns bounded plan projection/search, not final policy meaning.
- One production hand-action policy owns Play-vs-Discard survival arbitration.
- `PathAwareLiveHandActionDecisionEngine` owns scheduling/confirmation/timeout and must never switch objectives because the time budget expires.
- Candidate pruning may remove only mechanically dominated/unusable candidates; it must not introduce a second strategic objective.
- Pace, held-card value, generated resources, strategy execution, and discard mechanics become evidence visible to the same D1 arbitration path.
- Remaining D1 wrappers should collapse toward exact mechanics, projection, caching, or runtime scheduling only.

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

## Known shop authority defects already observed

1. **Generic HOLD vs obvious first scoring foothold:** an otherwise positive early scorer could be rejected by reserve/adequacy logic.
2. **Rescue overriding semantic veto:** the early scoring rescue initially overrode the Scary Face / Ride the Bus canonical conflict, proving rescue authority was too broad.
3. **Cash paralysis:** a rich underpowered build could repeatedly END_SHOP because one upstream recommendation object prevented later survival evidence from reopening reroll.
4. **Nested planning/runtime:** hypothetical D2/D14 states and diagnostics launched expensive D1/future expectation work even when that work had no final authority.
5. **Legacy bundle logic:** named historical shop-combination logic could compete with canonical Bond/composition arbitration until explicitly disabled in production.

## Phase-0 consolidation target for shop

- Family evaluators return facts/options, not final global truth.
- One D14 arbiter compares BUY/REPLACE/voucher/pack/consumable/reroll/END_SHOP on a shared run-winning scale.
- Mechanical/Bond incompatibility is a hard semantic constraint where genuine.
- Build Health and Bond changes are terms in the final comparison, not separate rescue paths.
- Visible immediate survival outranks speculative future option value when the build is underpowered.
- Paid-reroll reserve remains a hard safety constraint; within that constraint, underpowered rich states can choose reroll.

---

# D8 / D9 / D10 — packs and consumables

## Desired authority

- Unopened stochastic packs: one-layer public expectation only.
- Opened packs / held consumables: exact currently visible modeled mechanics may be evaluated because the choice is now real.
- Hidden future contents, hidden draw order, seed/RNG state are never decision inputs.
- Family-local expectation is evidence submitted to D14; it does not independently outrank survival/economy.

Existing detailed implementations remain intact during the competence freeze. They are audited/reintroduced after D1 and simple shop benchmarks are stable.

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

The removal of post-decision bounded D1 Build Health projection is the model for this rule.

---

# Phase-0 consolidation queue

Before deleting a wrapper that protects behavior, first ensure the valid behavior has semantic/property coverage whenever practical. A wrapper that is purely redundant implementation plumbing may be removed once its semantics have moved canonically. Related low-risk items that share one authority boundary should be batched in the same pass; do not require a separate validation round for every trivial wrapper cleanup.

1. [x] Tag every D1-affecting installed wrapper M/P/E/S/A/G/D.
2. [ ] Tag every shop-affecting installed wrapper M/P/E/S/A/G/D.
3. [ ] Identify wrappers whose only purpose is a previously observed live defect.
4. [ ] Add benchmark coverage for that defect if absent.
5. [ ] Move semantics into the canonical D1 planner/evaluator/policy/engine or D14 comparison.
6. [ ] Remove redundant late wrappers.
7. [ ] Group related low-risk migrations into one consolidation batch and let the user run the targeted semantic/regression gate after the batch.
8. [ ] Require one full deterministic-suite + semantic-benchmark integration gate when the batch is complete.

## Current intended final authorities

Until consolidation is complete:

- **D1 projection/search:** `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`.
- **D1 action arbitration:** `StrategyAwareLiveHandActionPolicy` is the production Play-vs-Discard authority.
- **D1 orchestration/final return:** `PathAwareLiveHandActionDecisionEngine.decide()`.
- **D2 family:** Joker acquisition/replacement policies produce family-local evidence.
- **D14:** `BuildAwareShopArbiter` is the intended final cross-family shop authority, currently still surrounded by Build Health/Bond/late runtime corrections that must be consolidated.
- **Execution:** injected bridge executes only the selected legal action; execution guards may reject stale/illegal actions but must not invent a second strategy.
- **Diagnostics:** no gameplay authority.
