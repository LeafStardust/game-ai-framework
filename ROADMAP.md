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

> **Phase 1 — semantic benchmark expansion and D1 survival competence refinement. Final batch pending validation.**

Phase 0 authority consolidation is **CLOSED / VALIDATED**.

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

## Phase-0 exit evidence

User-provided deterministic suite:

```powershell
git pull
python -m pytest -q tests/balatro
```

Result: **GREEN**.

Phase-0 Red/White semantic benchmark: **24/24 GREEN**:

- `BUILD_COHERENCE`: 2/2
- `D1_SURVIVAL`: 13/13
- `SHOP_SURVIVAL`: 9/9

`docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` was refreshed in `d18332cc` and documents current native owners rather than retired Phase-0 installers.

Closed Phase-0 migrations include target-hand evidence, Purple Seal branch coverage, held Blue/Gold resources, semantic-search ownership, Serpent, Hook, Cerulean, Ectoplasm, round-reset resources, Joker-generation public state, and Eye/Mouth boss constraints. Compatibility modules may remain importable but are not production authorities.

Do not reopen Phase 0 without fresh deterministic or live evidence.

---

# PHASE-1 SEMANTIC EXPANSION

Phase 1 is intentionally capped at **five batches** unless the final batch exposes a real production defect. Further benchmark growth without a concrete failure class is out of scope.

## Batch 1 — VALIDATED GREEN

Commits:

- `7c03bb73` — initial Phase-1 D1 semantic cases.
- `6ba86d1e` — benchmark wiring.

Validated:

- `d1.survival.guaranteed_clear_preserves_discard`
- `d1.boss.recursive_cerulean_legality`

User result: **26/26 GREEN**, `D1_SURVIVAL` 15/15.

## Batch 2 — VALIDATED GREEN

Commit:

- `74ebd420` — recovery/resource hierarchy semantics.

Validated:

- `d1.survival.underpace_prefers_material_redraw`
- `d1.resources.last_discard_marginal_recovery`

User result: **28/28 GREEN**, `D1_SURVIVAL` 17/17.

## Batch 3 — VALIDATED GREEN

Commit:

- `2e0db64a` — timeout consistency semantics.

Validated:

- `d1.timeout.latest_completed_root`
- `d1.timeout.sampled_clear_requires_confirmation`

User result: **30/30 GREEN**, `D1_SURVIVAL` 19/19.

This protects both completed-root reuse under partial search timeout and the rule that timeout cannot manufacture confirmation for an inexact sampled clear.

## Batch 4 — VALIDATED GREEN

Commit:

- `6f4715ac` — hand-resource and public-uncertainty semantics.

Validated:

- `d1.resources.last_hand_prefers_recovery_discard`
- `d1.uncertainty.hidden_draw_order_invariant`

User result: **32/32 GREEN**, `D1_SURVIVAL` 21/21.

This protects the final scoring-hand recovery hierarchy and ensures public redraw probabilities are invariant to inaccessible serialized deck order.

## Batch 5 — FINAL / IMPLEMENTED / VALIDATION PENDING

Commit:

- `c5031bf9` — final held-consumable/re-observation semantic.

New case:

- `d1.consumable.first_action_reobserve_boundary`
  - D1 may project a deterministic held consumable together with the guaranteed follow-up clear for survival value;
  - the executable selected action remains `USE_CONSUMABLE`, not a chained Play;
  - expected hand/discard resources reflect the projected follow-up while execution still stops at the consumable and requires authoritative re-observation/replanning.

Canonical owner if it fails: `D1LiveBlindClearPlanner._estimate_from_recommendation()` and the D1 first-action execution boundary.

No production code or tuning values changed in Batch 5.

Expected benchmark if it passes: **33/33**, with `D1_SURVIVAL` 22/22.

---

# EXACT NEXT ACTION

Validate the **final Phase-1 batch** locally:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

Do not run it from ChatGPT.

### If 33/33 green

1. mark Phase 1 **COMPLETE**;
2. do not add Batch 6 merely for more semantic cases;
3. advance immediately to **Phase 2 — simple shop survival**;
4. inspect canonical D14/D2/D3/D4/D11 simple-shop survival decisions before adding new behavior or tuning.

### If the final case fails

Fix the smallest canonical owner. Do not add a wrapper rescue. Re-run the semantic benchmark, then close Phase 1 only after green.

---

# PHASE ORDER

1. **Phase 0 — authority consolidation** — COMPLETE
2. **Phase 1 — semantic benchmark expansion + D1 survival competence refinement** — FINAL BATCH PENDING
3. **Phase 2 — simple shop survival**
4. **Phase 3 — coherent build evidence/authority quality**
5. **Phase 4 — complex packs/consumables/vouchers/economy audit**
6. **Phase 5 — live validation**
7. **Phase 6 — numerical tuning only after semantics are trustworthy**

Future stake/deck progression remains blocked until Red/White competence passes.

---

# CLOSED / DO NOT REOPEN WITHOUT FRESH EVIDENCE

- Phase-0 D1 ownership migration queue
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
