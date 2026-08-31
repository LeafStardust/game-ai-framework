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

> **Phase 1 — semantic benchmark expansion and D1 survival competence refinement.**

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

## Batch 4 — IMPLEMENTED / VALIDATION PENDING

Commit:

- `6f4715ac` — hand-resource and public-uncertainty semantics.

New cases:

1. `d1.resources.last_hand_prefers_recovery_discard`
   - with one scoring hand left, a useful discard may outrank a slightly stronger under-pace Play because the Play consumes the final scoring opportunity;
   - owner if it fails: `LiveHandActionPolicy` PACE_RECOVERY hand-resource hierarchy.
2. `d1.uncertainty.hidden_draw_order_invariant`
   - `PublicDeckComposition` and redraw probability are invariant to the serialized order of unseen deck cards;
   - owner if it fails: `games/balatro/live/draw_model.py` public-state boundary.

No production code or tuning values changed in Batch 4.

Expected benchmark if both pass: **32/32**, with `D1_SURVIVAL` 21/21.

---

# EXACT NEXT ACTION

Validate Batch 4 locally:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

Do not run it from ChatGPT.

### If 32/32 green

Phase-1 semantic coverage has now explicitly protected:

- guaranteed-clear resource conservation;
- recursive boss legality;
- under-pace redraw quality;
- last-discard reserve;
- partial-search timeout consistency;
- sampled-clear confirmation boundaries;
- last-hand survival hierarchy;
- hidden draw-order invariance.

Then audit whether any **held-consumable spend vs re-observation/replan boundary** remains a plausible unprotected D1 competence failure. Add a case only if there is a concrete production path that can actually violate that boundary. Otherwise close Phase 1 and advance to **Phase 2 — simple shop survival**.

### If a new case fails

Fix the smallest canonical owner. Do not add wrapper rescues.

---

# PHASE ORDER

1. **Phase 0 — authority consolidation** — COMPLETE
2. **Phase 1 — semantic benchmark expansion + D1 survival competence refinement** — ACTIVE
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
