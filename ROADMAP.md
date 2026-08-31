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

> **Phase 0 exit gate — substantive D1 authority consolidation is complete and locally validated.**

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

Latest focused green:

```powershell
git pull
python -m pytest -q tests/balatro/test_balatro_boss_hand_constraints_native.py
```

## Phase-0 substantive migration status

**Complete. No further ownership-migration bucket is queued.**

The full-suite exit gate exposed one stale architecture regression:

- `tests/balatro/test_balatro_d1_root_discard_reserve.py` still imported `_ensure_root_discard_reserve` and monkeypatched `_cheap_discard_key` / `_active_hook` from retired `semantic_search_guard_policy`.
- Production root-discard reserve behavior already lives natively on `LiveBlindClearPlanner`.
- `fa0d92d2` retargeted the old regression to native planner methods while preserving its three behavioral checks: root discard reserve insertion, no duplicate discard evidence, and Hook suppression.
- No production behavior changed for this repair.

No tuning values were changed as part of ownership consolidation.

---

# EXACT NEXT ACTION

Re-run the **Phase-0 full deterministic exit gate** locally:

```powershell
git pull
python -m pytest -q tests/balatro
```

Do not run it from ChatGPT.

### If the full deterministic suite is green

Run the Red/White semantic benchmark:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

Then refresh `docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` if it still describes retired D1 installers. Only after the full suite, benchmark review, and authority-map refresh should Phase 0 be declared complete and the roadmap advance.

### If the full suite fails

Treat each failure as fresh evidence. Distinguish:

1. genuine production semantic/mechanics regression;
2. stale regression protecting retired monkeypatch/installer architecture;
3. test-construction/identity assumption inconsistent with the canonical contract.

Fix the smallest correct layer. Do not reopen closed migration buckets without evidence.

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
11. Phase-0 exit gate — **ACTIVE; full suite rerun pending after stale root-reserve test repair**

---

# PHASE-0 EXIT GATE

Phase 0 is complete only when:

- one documented/enforced final authority exists for each action family;
- late semantic rescue layers are removed or reduced to true compatibility/diagnostic code;
- true observation adapters are explicit/native at the observer/translator boundary rather than installed via mutation;
- diagnostics cannot independently plan or change actions;
- production behavior no longer depends on fragile module import/installer order for migrated D1 semantics;
- deterministic focused tests protect behavior rather than retired monkeypatch mechanisms;
- the full Balatro deterministic suite is green;
- the Red/White semantic benchmark has been reviewed after the decision-semantic migrations;
- `docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` reflects current native ownership rather than retired installers.

Mandatory deterministic suite:

```powershell
git pull
python -m pytest -q tests/balatro
```

Then semantic benchmark:

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
