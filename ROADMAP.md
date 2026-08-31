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
- Do not use broad tuning to compensate for authority/semantic defects.

---

# ACTIVE GAMEPLAY OBJECTIVE

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

Feature growth remains frozen until this competence gate is stable and reproducible.

---

# CURRENT STATE — 2026-08-31

Active phase:

> **Phase 0 exit gate — substantive D1 authority consolidation and the full deterministic Balatro suite are locally validated.**

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
- D1 arbitration: `LiveHandActionPolicy`; production strategy-aware authority: `StrategyAwareLiveHandActionPolicy`
- D1 orchestration/final return: `LiveHandActionDecisionEngine` / path-aware production engine
- D14 SHOP: `BuildAwareShopArbiter`
- D11 reroll: `BuildAwareShopRerollPolicy`
- D9 opened pack: `BalatroPackPolicy`

## Locally validated ownership migrations

- target-hand evidence
- Purple-Seal discard beam coverage
- held Blue-Seal / Gold-card resource behavior
- semantic-search guard ownership
- The Serpent exact redraw rule
- The Hook forced-discard branch refill/search rule
- Cerulean Bell `forced_selection` live-state path
- Ectoplasm `ecto_minus` live-state path
- round-reset discard resource live-state path
- Joker-generation state, translator, explicit observer, production observer composition, and installer retirement
- The Eye / The Mouth boss-hand constraints, Mouth discard evidence, and forced legal recovery

Latest user-provided full-suite green:

```powershell
git pull
python -m pytest -q tests/balatro
```

## Phase-0 substantive migration status

**Complete. No further ownership-migration bucket is queued.**

The full-suite exit gate exposed two kinds of cleanup before passing:

### Stale tests protecting retired architecture

- `test_balatro_d1_root_discard_reserve.py` was retargeted to native `LiveBlindClearPlanner` ownership in `fa0d92d2`.
- Candidate-deadline regressions no longer monkeypatch `semantic_search_guard_policy`; they target native planner timing in `0f0bcd43`.
- Semantic prefilter/deadline regressions now target native planner helpers in `890d7fdd` and `acd1e98c`.
- Joker generation metadata-cache regressions now target `live.joker_generation_pool_state` in `4df31a96`.
- Mouth zero-score recovery regressions now target `live.boss_hand_constraints` directly in `7da289b0`.
- The Bond integration audit no longer requires the retired D1 strategy-execution installer sentinel; it verifies native strategy-policy ownership in `483301cb`.
- Blue-Seal round-end tests now enter through `_estimate_action()`, which is the canonical context that records the played action for held-card terminal accounting, in `d16e60af`.

### Genuine production defect found by exit gate

`D1LiveBlindClearPlanner` in `hand_action_planner_core.py` overrode `_play_priority()` with a four-field tuple and accidentally shadowed the native base planner's Gold-card final tie-break. Commit `621856c6` restores `-selected_gold` as the final mechanical tie-break in D1 core priority. The verified commit diff contains only that missing tie-break.

The user reran the complete deterministic Balatro suite after these repairs and reported **green**.

No broad tuning values were changed.

---

# EXACT NEXT ACTION

Run the **Red/White semantic benchmark** locally:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

Do not run it from ChatGPT.

### After the benchmark result

1. review semantic benchmark output for regressions/pathologies;
2. refresh `docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` so retired D1 installers are described as compatibility/history rather than active authority;
3. if the benchmark is acceptable and the authority map is current, declare Phase 0 complete and advance the roadmap to the next competence phase.

### If the benchmark reveals a semantic failure

Treat it as fresh evidence. Fix the smallest canonical owner and rerun the focused regression plus the semantic benchmark. Do not reopen retired wrapper architecture merely to satisfy historical expectations.

---

# ORDERED PHASE-0 QUEUE

1. Target-hand evidence — IMPLEMENTED / VALIDATED
2. Purple Seal discard beam coverage — IMPLEMENTED / VALIDATED
3. Held round-end resources — IMPLEMENTED / VALIDATED
4. Semantic-search guard — IMPLEMENTED / VALIDATED
5. Serpent — IMPLEMENTED / VALIDATED
6. Hook — IMPLEMENTED / VALIDATED
7. Cerulean — IMPLEMENTED / VALIDATED
8. Ectoplasm + round-reset resources — IMPLEMENTED / VALIDATED
9. Joker-generation live state — IMPLEMENTED / VALIDATED
10. Boss-hand constraints — IMPLEMENTED / VALIDATED
11. Phase-0 deterministic suite — **GREEN**
12. Red/White semantic benchmark — **NEXT**
13. Authority-map refresh + Phase-0 closure — **AFTER BENCHMARK**

---

# PHASE-0 EXIT GATE

Phase 0 is complete only when:

- one documented/enforced final authority exists for each action family;
- late semantic rescue layers are removed or reduced to true compatibility/diagnostic code;
- true observation adapters are explicit/native at the observer/translator boundary rather than installed via mutation;
- diagnostics cannot independently plan or change actions;
- production behavior no longer depends on fragile module import/installer order for migrated D1 semantics;
- deterministic focused tests protect behavior rather than retired monkeypatch mechanisms;
- the full Balatro deterministic suite is green — **SATISFIED**;
- the Red/White semantic benchmark has been reviewed after the decision-semantic migrations — **PENDING**;
- `docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` reflects current native ownership rather than retired installers — **PENDING**.

Semantic benchmark:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

---

# CLOSED / DO NOT REOPEN WITHOUT FRESH EVIDENCE

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

---

# LATER PHASES — BLOCKED UNTIL PHASE 0 EXIT GATE PASSES

1. Semantic benchmark expansion
2. D1 survival competence refinement
3. Simple shop survival
4. Coherent build authority
5. Complex packs/consumables/vouchers/economy audit
6. Live validation
7. Numerical tuning only after semantics/authority are trustworthy

Future stake/deck progression remains blocked until Red/White competence passes.
