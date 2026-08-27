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

`games/balatro/__init__.py` still installs an ordered stack of monkeypatch-style policy wrappers. Installation order matters because later wrappers can observe, rescue, veto, or rewrite decisions made by earlier ones. Removing that semantic ordering dependency is the main Phase-0 objective.

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

The live runner calls `PathAwareLiveHandActionDecisionEngine.decide(state)` through the production runtime. The engine owns adaptive-search scheduling and timeout handling. `LiveBlindClearPlanner` produces bounded plan evidence; `LiveHandActionPolicy`/the production strategy-aware policy owns Play-vs-Discard survival arbitration.

| Component | Class | Current role | Desired role |
|---|---|---|---|
| `CardSelector` | M | Generates legal play/discard candidates | Keep |
| boss/forced-selection mechanics | M | Restrict legality or exact score semantics | Keep authoritative |
| `LiveHandDecisionEvaluator` | P/E | Literal current-action projection and local recovery evidence | Keep beneath D1 arbitration |
| `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner` | P/E | Bounded public-state expectimax and plan values | **Canonical D1 projection/search authority** |
| `LiveHandActionPolicy` / production strategy-aware policy | A | Applies clear-path / pace / recovery hierarchy to completed plans | **Canonical D1 Play-vs-Discard arbiter** |
| `PathAwareLiveHandActionDecisionEngine` | A | Owns search schedule, confirmation, timeout/fallback and final return | **Canonical D1 orchestration/final-return authority** |
| public draw/outcome models | P | Model distributions without hidden draw order/RNG | Keep |

Post-policy wrappers may refine evidence or a candidate **within a finalized action class** where explicitly justified, but they may not independently reverse Play↔Discard after canonical survival arbitration.

## Inspected wrapper classification

| Wrapper | Class | Finding | Consolidation direction |
|---|---|---|---|
| `boss_hand_constraint_policy` | **M + G** | Eye/Mouth constraints encode real public boss mechanics, but `_mouth_forced_discard` can rewrite a selected discard after arbitration | Keep exact boss filtering; move any valid preference into canonical D1 evidence |
| `mouth_hand_policy` | **M + S + A/G** | The Mouth lock/candidate legality is exact, but first-hand logic also runs a separate planner/Bond comparison and can replace the selected play | Keep exact Mouth state/legality; consolidate first-hand strategy rewrite into canonical evidence/arbitration |
| `serpent_draw_policy` | **M + P** | Models The Serpent's exact draw-count consequence | Keep; mechanics/projection only |
| `hook_planner_integration_policy` | **M + P** | Models The Hook's mandatory two-card discard in successor projection | Keep; mechanics/projection only |
| `cerulean_bell_d1_legality_policy` | **M + G** | Enforces forced-card legality for Cerulean Bell | Keep exact legality; eventually prefer direct candidate-generation integration over late guard shape |
| `d1_candidate_deadline_policy` | **P/G runtime** | Bounds candidate work against the D1 deadline; does not introduce a strategic objective | Keep bounded-search behavior; canonicalize into planner when practical |
| `d1_outer_evaluation_cache_policy` | **P runtime** | Memoizes repeated public-state/action evaluation during one outer search | Keep performance semantics; eventually make cache native rather than monkeypatched |
| `d1_log_resilience_policy` | **E + runtime** | Boss-unconfirmed exactness is downgraded and search reserve is bounded. Its former hard-coded late Play→Discard rewrites were removed | Keep confidence/runtime safeguards only; no independent action arbitration |
| retired `d1_debuff_recovery_policy` | **E** | Bounded preference for discarding currently debuffed cards was valid recovery evidence, but the monkeypatch wrapper was unnecessary | **Consolidated:** evidence now lives directly in `LiveHandDecisionEvaluator._discard_value`; installer/file removed |
| `safe_pace_timeout_patch` | **P/runtime** | Seeds a bounded horizon-1 root before adaptive search. Its former duplicate completed-root timeout selector was removed; completed bootstrap evidence is now fed to the path-aware engine's canonical timeout history | Keep bounded bootstrap only; eventually move bootstrap scheduling into the engine directly |
| `safe_pace_scope_correction` | **A** | Current production survival arbiter that owns pace-qualified Play vs recovery Discard scope | Keep temporarily as the intentional A layer; migrate semantics into canonical policy before removing wrapper |
| `safe_pace_optimization_policy` | **P/runtime** | Installs only the bounded adaptive-search schedule; it no longer patches action arbitration | Keep bounded schedule semantics; eventually make schedule native rather than monkeypatched |
| retired `pinned_strategy_safe_pace_policy` | **S + A/G** | Previously re-selected a PACE_PLAY after the canonical policy using a 98% score-equivalence and survival-tolerance band | **Consolidated:** the equivalence band now lives directly in `StrategyAwareLiveHandActionPolicy`; installer/file removed |
| `semantic_search_guard_policy` | **P + G runtime** | Bounds root/child candidate generation and preserves compact made-hand representatives; also patches unrelated Bond/no-discard helper behavior in the same installer | Preserve bounded candidate semantics, split unrelated concerns, then migrate search behavior into planner directly |
| `secret_hand_score_authority` | **M + P/E** | Adds exact vanilla base scores for secret hands and representative D2 probes; it does not choose D1 actions | Keep mechanics; eventually move secret-hand score table into canonical scorer definition rather than install-time mutation |
| `castle_discard_policy` | **M/E + G** | Castle may replace one already-selected Discard with a current-suit discard only inside modeled safety tolerance; it never creates a discard | Preserve Castle mechanic/value as within-discard evidence; migrate tie-break into canonical D1 evaluator/policy and remove late wrapper |
| `bond_d1_cache_policy` | **S/runtime** | Caches immutable Bond hand-intent evidence for one D1 decision; no independent action objective | Keep performance semantics; make cache native to strategy-aware policy when practical |
| `burnt_bond_execution_policy` | **S + A/G** | Explicitly allows a survival-equivalent first Burnt discard to replace a pace-qualified Play. The permanent first-discard leveling value is legitimate, but this is a second Play↔Discard controller | **High-priority migration target:** benchmark Burnt first-discard semantics, expose its permanent value to canonical arbitration, then remove cross-class wrapper authority |
| `aces_dna_hand_policy` | **S + A/G** | DNA/Aces strategy logic can replace the canonical result with a PLAY candidate; survival floors bound the rewrite, but the wrapper can still reverse a canonical DISCARD into PLAY | Benchmark DNA setup semantics, expose duplication/setup value inside canonical D1 evidence, then remove cross-class wrapper authority |
| `strategy_execution_guard_policy` | **S/E + A/G** | Realized no-discard and hand-repetition engines refine only an already-selected PLAY; DISCARD is observed but not reversed | Keep action-class boundary; migrate these within-PLAY preferences into canonical strategy-aware ranking and remove late wrapper |
| `target_hand_engine_policy` | **M/S + A/G** | Exact Runner/To Do List target-hand mechanics are used to pick a survival-equivalent pace PLAY, but the wrapper can reverse a canonical DISCARD into PLAY | Preserve target mechanics as evidence; move target-hand value into canonical D1 arbitration before removing wrapper |
| `purple_seal_discard_policy` | **M + P** | Preserves mechanically distinct Purple-Seal Tarot-generation discard branches through bounded child/root beams; it does not assign final utility or choose the D1 action | Keep beam-coverage semantics; migrate candidate generation directly into `D1LiveBlindClearPlanner` |
| `held_round_end_resource_policy` | **M + P/E** | Projects exact Blue-Seal round-end generation and uses Gold-card retention only as a final equal-value ordering term; it does not post-rewrite the chosen action | Keep literal resource semantics; move projection/priority behavior into canonical planner implementation |
| `ride_the_bus_execution_policy` | **M/E + A/G** | On an already-selected terminal guaranteed PLAY, it may switch to a non-face guaranteed PLAY that preserves the Bus stack without worsening modeled round resources | Preserve the dominance rule, but move Bus stack preservation into canonical terminal-plan evaluation/tie-breaking |
| `pinned_strategy_execution_policy` | **S/E** for packs, not D1 | Augments already-positive pack options with pinned missing-feature evidence and motif prescriptions | Exclude from D1 queue; audit under D8/D14 |
| `strategy_authority_correction_policy` | **S/E** for composition/shop/pack, not D1 | Corrects premature strategy commitment and adds bounded missing-piece recruitment evidence | Exclude from D1 queue; audit under composition/D8/D14 |
| `live_decision_quality_policy` | **G** for D8/B4/D9, not D1 | Does not own play/discard selection | Exclude from D1 consolidation; audit later under pack/shop phase |
| final `red_white_competence_corrections` | **G** | Late Red/White rescues still patch D1 discard value/beam plus shop admissions | Every retained behavior must gain benchmark coverage and move into its canonical owner |

Classification is evidence-based. The currently installed D1-affecting wrapper inventory has now been classified; Phase 0 should proceed by migrating the remaining A/G semantics rather than adding new wrappers.

## D1 authority defects and disposition

1. **Planner/controller disagreement:** discard candidate pre-ranking used a different objective than canonical D1 evaluation. This is benchmarked; candidate ranking must use canonical D1 evidence.
2. **Recovery oscillation:** separate rescue rules have produced both repeated one-card discards and later runs that preserved all discards while dying. Continue consolidating into one survival comparison.
3. **Timeout divergence:** structural fallback could abandon completed modeled survival evidence. The path-aware production engine now retains completed canonical D1 evidence; semantic case `d1.authority.timeout_consistency` protects this. The older duplicate completed-root selector in `safe_pace_timeout_patch` has been removed.
4. **Post-policy cross-class reversal:** deeper adaptive evidence could replace a production pace decision with the opposite action class. This behavior is retired; semantic case `d1.authority.action_class` protects final Play-vs-Discard ownership.
5. **Debuffed-card recovery wrapper:** valid recovery evidence lived in a monkeypatch. It is now canonical in `LiveHandDecisionEvaluator`; wrapper/installer removed.
6. **Log-resilience second arbiter:** hard-coded projected-score margins could rewrite Play→Discard after policy arbitration. Those rewrites are removed; only confidence/runtime safeguards remain.
7. **Safe-pace strategy second pass:** pinned strategy previously re-arbitrated PACE_PLAY after the canonical policy. Its score/survival equivalence semantics now live in `StrategyAwareLiveHandActionPolicy`; the wrapper is removed.
8. **Burnt first-discard second arbiter:** permanent Burnt scaling is legitimate strategy evidence, but the current wrapper can override a pace-qualified Play. Move that value into canonical arbitration before deleting the wrapper.
9. **DNA/target-hand cross-class rewrites:** setup/engine value is legitimate, but the current wrappers can turn canonical DISCARD into PLAY. These are the next high-risk strategy migration targets.

## Phase-0 consolidation target for D1

- Exact mechanics/legality stay outside and above value arbitration.
- `LiveBlindClearPlanner` owns bounded plan projection/search, not final policy meaning.
- One production hand-action policy owns Play-vs-Discard survival arbitration.
- `PathAwareLiveHandActionDecisionEngine` owns scheduling/confirmation/timeout and must never switch objectives because the time budget expires.
- Candidate pruning may remove only mechanically dominated/unusable candidates; it must not introduce a second strategic objective.
- Pace, held-card value, generated resources, strategy execution, and discard mechanics become evidence visible to the same D1 arbitration path.
- Late D1 guards are deleted or reduced to mechanics/runtime once equivalent benchmark-covered semantics exist canonically.

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

Before deleting a wrapper that protects behavior, first ensure the valid behavior has semantic/property coverage whenever practical. A wrapper that is purely redundant implementation plumbing may be removed once its semantics have moved canonically.

1. [x] Tag every D1-affecting installed wrapper M/P/E/S/A/G/D.
2. [ ] Tag every shop-affecting installed wrapper M/P/E/S/A/G/D.
3. [ ] Identify wrappers whose only purpose is a previously observed live defect.
4. [ ] Add benchmark coverage for that defect if absent.
5. [ ] Move semantics into the canonical D1 planner/evaluator/policy/engine or D14 comparison.
6. [ ] Remove redundant late wrappers.
7. [ ] Use targeted deterministic tests during a consolidation batch.
8. [ ] Require one full deterministic-suite + semantic-benchmark integration gate when the batch is complete.

## Current intended final authorities

Until consolidation is complete:

- **D1 projection/search:** `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`.
- **D1 action arbitration:** one production `LiveHandActionPolicy` hierarchy.
- **D1 orchestration/final return:** `PathAwareLiveHandActionDecisionEngine.decide()`.
- **D2 family:** Joker acquisition/replacement policies produce family-local evidence.
- **D14:** `BuildAwareShopArbiter` is the intended final cross-family shop authority, currently still surrounded by Build Health/Bond/late runtime corrections that must be consolidated.
- **Execution:** injected bridge executes only the selected legal action; execution guards may reject stale/illegal actions but must not invent a second strategy.
- **Diagnostics:** no gameplay authority.
