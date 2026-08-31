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
2. `d1.boss.recursive_cerulean_legality`

User reported **26/26 GREEN**, with `D1_SURVIVAL` at 15/15.

### Batch 2 — VALIDATED GREEN

Commit:

- `74ebd420` — adds two recovery/resource hierarchy cases.

Validated cases:

1. `d1.survival.underpace_prefers_material_redraw`
   - no pace-qualified Play + materially better canonical redraw => choose discard.
2. `d1.resources.last_discard_marginal_recovery`
   - a marginal recovery edge does not consume the final discard after the canonical reserve penalty.

User reported **28/28 GREEN**, with `D1_SURVIVAL` at 17/17.

### Batch 3 — IMPLEMENTED / VALIDATION PENDING

Commit:

- `2e0db64a` — adds two timeout-consistency cases.

New cases:

1. `d1.timeout.latest_completed_root`
   - if a later adaptive pass times out, reuse the latest fully completed canonical D1 root;
   - do not rewind to older evidence or switch to structural emergency selection.
2. `d1.timeout.sampled_clear_requires_confirmation`
   - an inexact sampled line above the clear-probability floor remains recovery evidence unless an independent confirmation pass completed;
   - timeout cannot manufacture `CLEAR_PATH` confirmation.

Canonical owner if either fails: `PathAwareLiveHandActionDecisionEngine._structural_timeout_fallback()` and its completed-root history contract.

No production code or tuning values changed in this batch.

Expected benchmark total if both pass: **30/30**, with `D1_SURVIVAL` at 19/19.

---

# EXACT NEXT ACTION

Validate the third Phase-1 semantic batch locally:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

Do not run it from ChatGPT.

### If 30/30 green

Continue the Phase-1 audit for the next coherent D1 survival gap, prioritizing:

1. hand-resource hierarchy when hands are nearly exhausted;
2. held-consumable spend vs re-observation/replan boundaries;
3. public-state uncertainty invariants;
4. remaining terminal-clear/resource hierarchy gaps not already protected.

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
