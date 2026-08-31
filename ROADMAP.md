# ROADMAP — SINGLE SOURCE OF TRUTH

This file is written for an LLM continuing development of this repository.

**This is the only authoritative roadmap, handoff, queue, or current-status document in the repository.**

Rules:

1. Read this file first.
2. Treat `CURRENT STATE` and `EXACT NEXT ACTION` as authoritative.
3. Other `docs/` files are supporting evidence/history only.
4. If local test evidence proves this stale, update it in the same batch.
5. Do not create another roadmap/handoff file.

---

# REPOSITORY CONTRACT

- Repository: `LeafStardust/game-ai-framework`
- Active branch: `feat/v1.0-red-white-competence`
- User runs tests locally. **Do not run tests from ChatGPT.**
- Every local validation command must begin with `git pull`.
- Preserve exact Balatro mechanics, public-state legality, boss rules, and hidden-information boundaries.
- Never use hidden RNG state, seeds, future pool order, future identities, or inaccessible information.
- Prefer canonical ownership over late monkeypatch/rescue wrappers.
- Do not use broad tuning to compensate for semantic defects.

---

# ACTIVE GAMEPLAY OBJECTIVE

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

---

# CURRENT STATE — 2026-08-31

Active phase:

> **Phase 3 — coherent build evidence/authority quality. Batch 2 validated 46/46; Batch 3 contextual-pair semantics implemented, validation pending.**

Phase 0 authority consolidation: **COMPLETE / VALIDATED**.

Phase 1 D1 survival semantic expansion: **COMPLETE / VALIDATED**.

Phase 2 simple shop survival: **COMPLETE / VALIDATED**.

Canonical owners:

- D1 search/projection: `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`
- D1 arbitration: `StrategyAwareLiveHandActionPolicy`
- D1 orchestration/final return: `LiveHandActionDecisionEngine` / `PathAwareLiveHandActionDecisionEngine`
- D14 SHOP: `BuildAwareShopArbiter`
- D11 reroll: `BuildAwareShopRerollPolicy`
- D9 opened pack: `BalatroPackPolicy`

Canonical authority shape:

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

---

# VALIDATED BASELINE

Full deterministic Balatro suite:

```powershell
git pull
python -m pytest -q tests/balatro
```

Result: **GREEN**.

Semantic checkpoints:

- Phase 0 exit: **24/24 GREEN**.
- Phase 1 exit: **33/33 GREEN**.
- Phase 2 exit: **42/42 GREEN** (`BUILD_COHERENCE` 2/2, `D1_SURVIVAL` 22/22, `SHOP_SURVIVAL` 18/18).
- Phase 3 Batch 1: **44/44 GREEN**, `BUILD_COHERENCE` 4/4.
- Phase 3 Batch 2: **46/46 GREEN**, `BUILD_COHERENCE` 6/6.

`docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` was refreshed in `d18332cc` and reflects current native authority.

---

# PHASE 1 — CLOSED

Phase 1 was capped at five batches and is complete. No Batch 6 is queued absent fresh evidence.

Validated D1 additions include guaranteed-clear resource preservation, recursive boss legality, under-pace redraw quality, final-discard conservation, timeout authority, last-hand preservation, public hidden-order invariance, and held-consumable re-observation boundaries.

---

# PHASE 2 — CLOSED

Phase 2 was capped at four batches and is complete at **42/42**.

Validated simple-shop survival includes explicit `END_SHOP`, free/paid reroll boundaries, replacement re-observation, cash stop-loss, bounded first-engine reserve relaxation, reserve-crossing purchase economics, and shared-scale cross-family ordering.

Important Batch-3 fixture history:

- production D2 includes installed post-transaction Joker revaluation through `transition_planner.evaluator.evaluate()`;
- synthetic D2 fixtures must model that path when controlling build gain;
- no production behavior was changed by those fixture repairs.

Do not add a Phase-2 Batch 5 merely to increase coverage count.

---

# PHASE 3 — COHERENT BUILD EVIDENCE / AUTHORITY QUALITY

Goal: ensure D2/D14 build evidence distinguishes real scoring, support, scaling, economy, and composition without creating duplicate scoring authority or converting structural evidence into fake immediate power.

Audit order:

1. scoring-engine versus support/economy role separation;
2. scaling evidence versus already-realized scoring power;
3. contextual interaction value versus standalone intrinsic value;
4. Bond/composition evidence must not duplicate literal score arithmetic;
5. replacement/pivot evidence must remain downstream of legal D2 economics;
6. only after these semantics are clean, consider numerical weighting questions.

Build Health, Bond rank, motifs, and composition remain evidence/planning layers. They do not replace D1 survival authority or D14 final SHOP arbitration.

## Batch 1 — VALIDATED GREEN

Commits:

- `0f5b0f3a` — adds `red_white_semantic_phase3_build_cases.py`.
- `a89e8e6e` — benchmark wiring.

Validated:

- `build.roles.scoring_engine_direct_gain`
- `build.roles.economy_not_direct_scoring`

User result: **44/44 GREEN**, `BUILD_COHERENCE` 4/4.

## Batch 2 — VALIDATED GREEN AFTER CANONICAL DEFECT FIX

Commits:

- `ab6cdee0` — scaling-potential versus realized-power semantics using `RideTheBusJoker`.
- `f2f5f4c8` — canonical lifecycle checkpoint fix.

Validated:

- `build.scaling.fresh_potential_is_contextual`
- `build.scaling.investment_increases_direct_power`

Initial result was **44/46** because `LifecycleJokerBehaviorAnalyzer._score_sequence()` mutated event-driven Jokers with a synthetic `HAND_SCORED` event but `_checkpoint()` observed them with `event=None`. Ride the Bus therefore grew public `mult` but never exposed lifecycle scaling evidence. `f2f5f4c8` makes only score-sequence checkpoints carry the matching synthetic `HAND_SCORED` event on deep copies. Direct scoring was already correct.

User result after fix: **46/46 GREEN**, `BUILD_COHERENCE` 6/6.

## Batch 3 — IMPLEMENTED / VALIDATION PENDING

Commit:

- `e489d9dd` — adds contextual pair-value / double-count semantics.

Cases:

1. `build.interaction.blueprint_pair_only_value`
   - Blueprint may have standalone copy capability evidence;
   - a concrete visible adjacent scoring target must add additional pair-only interaction value through the mechanical `COPY` probe.
2. `build.interaction.independent_scoring_not_pair_synergy`
   - two ordinary independent scoring Jokers must not receive pair-interaction credit merely because each scores independently;
   - their literal scoring remains owned by direct score projection, not duplicated in B3 pair synergy.

Batch 3 changes semantic coverage only. No production code or tuning values changed.

Expected if both pass: **48/48**, with `BUILD_COHERENCE` 8/8.

---

# EXACT NEXT ACTION

Validate Phase-3 Batch 3 locally:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

Do not run it from ChatGPT.

### If 48/48 green

Continue Phase 3 with **Bond/composition evidence versus literal score arithmetic**. Audit for concrete double-counting paths first; add semantics only where a real B3/Bond owner can violate the boundary.

### If either Batch-3 case fails

Classify whether the pair probe fails to detect the real Blueprint adjacency mechanic or whether independent scoring is being duplicated as contextual interaction. Fix the smallest canonical B3 pair/synergy owner. Do not add D2/D14 rescue wrappers and do not weaken the semantics merely to make the count pass.

---

# PHASE ORDER

1. **Phase 0 — authority consolidation** — COMPLETE
2. **Phase 1 — D1 survival semantic expansion** — COMPLETE
3. **Phase 2 — simple shop survival** — COMPLETE
4. **Phase 3 — coherent build evidence/authority quality** — ACTIVE
5. **Phase 4 — complex packs/consumables/vouchers/economy audit**
6. **Phase 5 — live validation**
7. **Phase 6 — numerical tuning only after semantics are trustworthy**

Future stake/deck progression remains blocked until Red/White competence passes.

---

# CLOSED / DO NOT REOPEN WITHOUT FRESH EVIDENCE

- Phase-0 D1 ownership migration queue
- Phase-1 semantic expansion beyond five validated batches
- Phase-2 simple-shop expansion beyond four validated batches
- Mouth discard-only legality defect itself
- Green Joker survival-equivalent authority
- Hook/log-resilience search reserve
- target-hand installer architecture
- Purple-Seal installer architecture
- held-round-end-resource installer architecture
- semantic-search-guard installer architecture
- Serpent installer architecture
- Hook planner installer architecture
- Cerulean installer architecture
- Ectoplasm installer architecture
- round-resource installer architecture
- Joker-generation live-state installer architecture
- boss-hand-constraint installer architecture
- production-default tuning ContextVar hypothesis — falsified
- historical SHOP recursive expectation roots
- BLIND_SELECT quiescence deadlock
- ROUND_EVAL checkout fast-path semantics
- D1 root pre-beam wall-clock budget defect
- live tuner cascading after failed/non-COMPLETE trial
- Phase-A Bond exploratory tuning — completed with no promotion
- D14/D11 SHOP latency blocker unless fresh timing evidence reproduces it
