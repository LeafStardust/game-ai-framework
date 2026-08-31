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

Canonical owners:

- D1 search/projection: `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`
- D1 arbitration: `StrategyAwareLiveHandActionPolicy`
- D1 orchestration/final return: `LiveHandActionDecisionEngine` / path-aware production engine
- D14 SHOP: `BuildAwareShopArbiter`
- D11 reroll: `BuildAwareShopRerollPolicy`
- D9 opened pack: `BalatroPackPolicy`

## Phase-0 exit evidence

User-provided deterministic suite:

```powershell
git pull
python -m pytest -q tests/balatro
```

Result: **GREEN**.

User-provided Red/White semantic benchmark at Phase-0 exit:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

Result: **24/24 GREEN**:

- `BUILD_COHERENCE`: 2/2
- `D1_SURVIVAL`: 13/13
- `SHOP_SURVIVAL`: 9/9

`docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` was refreshed in `d18332cc` and documents current native owners rather than retired Phase-0 installers.

## Phase-0 closed migrations

- target-hand evidence
- Purple-Seal discard branch coverage
- held Blue-Seal / Gold-card resources
- semantic-search guard ownership
- The Serpent exact redraw rule
- The Hook forced-discard refill continuation
- Cerulean Bell `forced_selection` live-state path
- Ectoplasm `ecto_minus` live-state path
- round-reset discard-resource live state
- Joker-generation public pool live state
- The Eye / The Mouth boss-hand constraints and forced recovery

Compatibility modules for retired installers may remain importable but are not production authorities.

Do not reopen Phase 0 without fresh deterministic or live evidence.

## Phase-1 semantic expansion

### Batch 1 — VALIDATED GREEN

Commits:

- `7c03bb73` — adds `red_white_semantic_phase1_d1_cases.py`.
- `6ba86d1e` — includes the new cases in the Red/White semantic benchmark.

Validated cases:

1. `d1.survival.guaranteed_clear_preserves_discard`
   - a currently visible guaranteed clear suppresses discard generation entirely;
   - owner: `D1LiveBlindClearPlanner._candidate_actions()`.
2. `d1.boss.recursive_cerulean_legality`
   - recursive Cerulean Play candidates obey the same forced-card legality as root candidates;
   - owner: D1 child candidate generation / exact boss legality.

User reported the expanded benchmark **26/26 GREEN**, with `D1_SURVIVAL` at 15/15.

### Batch 2 — IMPLEMENTED / VALIDATION PENDING

Commit:

- `74ebd420` — expands `red_white_semantic_phase1_d1_cases.py` with two recovery/resource cases.

New cases:

1. `d1.survival.underpace_prefers_material_redraw`
   - when no current Play reaches required pace and the canonical recovery evaluator materially prefers a discard, D1 must choose the redraw;
   - owner if it fails: `LiveHandActionPolicy` PACE_RECOVERY arbitration.
2. `d1.resources.last_discard_marginal_recovery`
   - a small recovery edge must not consume the final discard once the canonical low-discard reserve penalty is applied;
   - owner if it fails: `LiveHandActionPolicy` PACE_RECOVERY resource hierarchy.

No production code or tuning values changed in this batch.

Expected benchmark total if both pass: **28/28**, with `D1_SURVIVAL` at 17/17.

---

# EXACT NEXT ACTION

Validate the second Phase-1 semantic batch locally:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

Do not run it from ChatGPT.

### If 28/28 green

Continue the Phase-1 audit for the next coherent D1 survival gap, prioritizing:

1. hand-resource hierarchy when hands are nearly exhausted;
2. held-consumable spend vs re-observation/replan boundaries;
3. timeout consistency under partially completed search;
4. public-state uncertainty invariants.

Do not add cases merely to increase benchmark count.

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
- ordinary D1 competence failures already repaired
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
