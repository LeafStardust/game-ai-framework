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

> **Phase 2 — simple shop survival. Batch 3 validated 40/40; final Batch 4 implemented, validation pending.**

Phase 0 authority consolidation: **COMPLETE / VALIDATED**.

Phase 1 D1 survival semantic expansion: **COMPLETE / VALIDATED**.

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

Phase-0 semantic exit benchmark: **24/24 GREEN**.

Phase-1 final semantic benchmark: **33/33 GREEN**:

- `BUILD_COHERENCE`: 2/2
- `D1_SURVIVAL`: 22/22
- `SHOP_SURVIVAL`: 9/9

Phase-2 validated checkpoints:

- Batch 1: **36/36 GREEN**, `SHOP_SURVIVAL` 12/12.
- Batch 2: **38/38 GREEN**, `SHOP_SURVIVAL` 14/14.
- Batch 3: **40/40 GREEN**, `SHOP_SURVIVAL` 16/16.

`docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` was refreshed in `d18332cc` and reflects current native authority.

---

# PHASE 1 — CLOSED

Phase 1 was intentionally capped at five batches and is complete. No Batch 6 is queued absent fresh evidence.

Validated additions:

1. guaranteed clear preserves discard resource;
2. recursive Cerulean candidates preserve boss legality;
3. under-pace play yields to materially stronger redraw;
4. final discard is conserved for only marginal recovery;
5. timeout reuses latest completed canonical root;
6. timeout does not promote unconfirmed sampled clears;
7. last-hand recovery preserves the final scoring opportunity;
8. public redraw value is invariant to hidden serialized deck order;
9. deterministic held-consumable clear projection executes only `USE_CONSUMABLE`, then re-observes/replans.

Do not expand Phase 1 merely to increase semantic case count.

---

# PHASE 2 — SIMPLE SHOP SURVIVAL

Goal: protect basic Red/White shop decisions before deeper composition/build optimization.

Audit order:

1. explicit END_SHOP/no-action survival baseline;
2. free versus paid reroll behavior;
3. transaction checkpoint safety for replacement/sell/buy flows;
4. early scoring foothold versus support/economy spending;
5. cash/reserve stop-loss on ordinary purchases and paid rerolls;
6. simple cross-family purchase comparison.

Existing SHOP semantics also protect first scoring foothold, strategic conflict vetoes, first-engine-before-hand-size, Wheel admission, empty-roster Buffoon admission, visible Bond-pair authority, and pair interaction requirements.

## Batch 1 — VALIDATED GREEN

Commits:

- `f2de18be` — adds `red_white_semantic_phase2_shop_cases.py`.
- `7a1a8188` — wires Phase-2 cases into the benchmark.

Validated:

- `shop.simple.end_shop_zero_baseline`
- `shop.simple.free_reroll_zero_tie`
- `shop.simple.replacement_reobserve_boundary`

User result: **36/36 GREEN**, `SHOP_SURVIVAL` 12/12.

## Batch 2 — VALIDATED GREEN

Commit:

- `2a09039c` — D11 paid-reroll stop-loss semantics.

Validated:

- `shop.simple.paid_reroll_cost_cap`
- `shop.simple.paid_reroll_cash_reserve`

User result: **38/38 GREEN**, `SHOP_SURVIVAL` 14/14.

## Batch 3 — VALIDATED GREEN

Commits:

- `00fe6214` — D2 ordinary-purchase cash semantics.
- `27484d51` — fixes synthetic planner interface.
- `c4c6c020` — isolates fixtures from Bond transition value.
- `8edc2ad9` — aligns synthetic evaluator with installed post-transaction D2 valuation.

Validated:

- `shop.simple.first_engine_zero_cash_guard`
- `shop.simple.joker_reserve_crossing_cost`

Validation history exposed three fixture mismatches before the real runtime contract was represented correctly: missing planner evaluator, Bond-value contamination, and installed post-transaction D2 revaluation through `transition_planner.evaluator.evaluate()`. No production behavior was changed by those fixture repairs.

User result after final repair: **40/40 GREEN**, `SHOP_SURVIVAL` 16/16.

## Batch 4 — FINAL PLANNED PHASE-2 BATCH / VALIDATION PENDING

Commits:

- `d57c4364` — adds `red_white_semantic_phase2_cross_family_cases.py`.
- `ce58863b` — wires the final cross-family cases into the semantic benchmark.

New cases:

1. `shop.simple.cross_family_first_engine_wins`
   - an admitted first scoring Joker with materially higher shared D14 normalized gain must beat a weaker deterministic support/economy purchase;
   - owner if it fails: `BuildAwareShopArbiter` / `ShopUtilityScale` cross-family comparison.
2. `shop.simple.cross_family_support_can_win`
   - first-engine status is evidence, not a hardcoded family override; a materially higher-value deterministic support/economy option must still beat the weaker Joker on the same parent scale;
   - owner if it fails: `BuildAwareShopArbiter` value ordering / family priority.

Batch 4 changes semantic coverage only. No production code or tuning values changed.

Expected benchmark if both pass: **42/42**, with `SHOP_SURVIVAL` 18/18.

**Phase 2 is capped at four planned batches.** If Batch 4 passes, close Phase 2 and advance to Phase 3. Do not add a Batch 5 merely to increase coverage count.

---

# EXACT NEXT ACTION

Validate final Phase-2 Batch 4 locally:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

Do not run it from ChatGPT.

### If 42/42 green

Close Phase 2 and begin **Phase 3 — coherent build evidence/authority quality**. Start by auditing whether D2/D14 build evidence distinguishes real scoring engines, support, scaling, and economy without duplicate or contradictory authority. Do not tune numerical weights yet.

### If either Batch-4 case fails

Classify fixture versus genuine D14 shared-scale defect. Fix the smallest canonical owner. Do not add post-arbiter family rescues.

---

# PHASE ORDER

1. **Phase 0 — authority consolidation** — COMPLETE
2. **Phase 1 — D1 survival semantic expansion** — COMPLETE
3. **Phase 2 — simple shop survival** — ACTIVE
4. **Phase 3 — coherent build evidence/authority quality**
5. **Phase 4 — complex packs/consumables/vouchers/economy audit**
6. **Phase 5 — live validation**
7. **Phase 6 — numerical tuning only after semantics are trustworthy**

Future stake/deck progression remains blocked until Red/White competence passes.

---

# CLOSED / DO NOT REOPEN WITHOUT FRESH EVIDENCE

- Phase-0 D1 ownership migration queue
- Phase-1 semantic expansion beyond five validated batches
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
