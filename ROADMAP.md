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

> **Phase 0 — D1 authority consolidation: remove installation-order-dependent wrappers by moving valid behavior into canonical owners without changing intended production semantics.**

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

Latest user-provided green command:

```powershell
git pull
python -m pytest -q tests/balatro/test_balatro_live_resource_state_native.py
```

## Joker-generation live-state migration — IN PROGRESS

Current implementation:

- `c053e7c0` — `BalatroState` natively owns:
  - `joker_generation_pool_observed`
  - `joker_generation_pools`
  - `joker_generation_edition_rate`
  - `visible_poker_hands`
  and preserves them through `copy()`.
- `320cad9d` — `DefaultBalatroStateTranslator.translate()` hydrates those fields natively.
- `a6815ec3` — extracted read-only `live/joker_generation_pool_state.py` catalogue reader preserving existing eligibility/cache semantics.
- `1672a920` — old installer narrowed to **snapshot emission only**; it no longer mutates `BalatroState` or the translator.
- `f9f4e948` — focused native state/translator regression coverage.

The existing public-information contract remains unchanged:

- no PRNG state;
- no future pool order;
- no selected future Joker identity;
- eligibility only uses public unlock/duplicate/Showman/challenge/pool-flag/enhancement-gate state;
- edition rate and visible poker-hand set remain public inputs;
- catalogue cache resets at `GAME_OVER`.

One temporary mutation remains:

- `joker_generation_pool_live_state_policy` still wraps `live_memory_observer.snapshot_payload_from_live_memory` to append the catalogue payload.

That observer hook must be made native before this migration is complete.

## Final substantive migration after Joker-generation state

`boss_hand_constraint_policy` still mutates `StrategyAwareLiveHandActionPolicy` for:

- The Eye candidate constraints;
- The Mouth locked-hand candidate constraints;
- Mouth discard evidence;
- Mouth discard-only forced legal recovery;
- zero-score Play redraw shaping when locked and no discards remain.

This is the final D1 strategy-authority migration before the Phase-0 exit gate.

---

# EXACT NEXT ACTION

1. Run the native Joker-generation state/translator checkpoint locally:

```powershell
git pull
python -m pytest -q tests/balatro/test_balatro_joker_generation_state_native.py
```

2. If green, migrate the remaining Joker-generation **snapshot emission** into canonical live observation:
   - canonical observer must call the read-only catalogue reader directly;
   - retire `install_joker_generation_pool_live_state_policy()` to compatibility no-op;
   - remove its package startup registration;
   - add focused observer-level regression coverage;
   - preserve catalogue caching and public-information boundaries.

3. Then migrate `boss_hand_constraint_policy` into `StrategyAwareLiveHandActionPolicy` / canonical D1 authority.

4. After boss-hand constraints are green, perform the Phase-0 exit gate. Do not invent another cleanup queue.

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
9. Joker-generation live state — **IN PROGRESS**
10. Boss-hand constraints — **FINAL SUBSTANTIVE MIGRATION**
11. Phase-0 exit gate

---

# PHASE-0 EXIT GATE

Phase 0 is complete only when:

- one documented/enforced final authority exists for each action family;
- late semantic rescue layers are removed or reduced to true compatibility/diagnostic code;
- true observation adapters are native at the observer/translator boundary rather than installed via mutation;
- diagnostics cannot independently plan or change actions;
- production behavior no longer depends on fragile module import/installer order for migrated D1 semantics;
- deterministic focused tests protect behavior rather than retired monkeypatch mechanisms.

After the final migration run:

```powershell
git pull
python -m pytest -q tests/balatro
```

If decision semantics changed materially, also run:

```powershell
python -m games.balatro.red_white_semantic_benchmark
```

The full deterministic suite is mandatory before Phase 0 is declared complete.

---

# CLOSED / DO NOT REOPEN WITHOUT FRESH EVIDENCE

- ordinary D1 competence failures already repaired
- Mouth discard-only legality defect itself (architecture still being migrated)
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
- production-default tuning ContextVar hypothesis — falsified
- historical SHOP recursive expectation roots
- BLIND_SELECT quiescence deadlock
- ROUND_EVAL checkout fast-path semantics
- D1 root pre-beam wall-clock budget defect
- live tuner cascading after failed/non-COMPLETE trial
- Phase-A Bond exploratory tuning — completed with no promotion
- D14/D11 SHOP latency blocker unless fresh timing evidence reproduces it

---

# LATER PHASES — BLOCKED UNTIL PHASE 0 IS CLEAN

1. Semantic benchmark expansion
2. D1 survival competence refinement
3. Simple shop survival
4. Coherent build authority
5. Complex packs/consumables/vouchers/economy audit
6. Live validation
7. Numerical tuning only after semantics/authority are trustworthy

Future stake/deck progression remains blocked until Red/White competence passes.
