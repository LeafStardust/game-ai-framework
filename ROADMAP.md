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

User-provided Red/White semantic benchmark:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

Result: **24/24 GREEN**:

- `BUILD_COHERENCE`: 2/2
- `D1_SURVIVAL`: 13/13
- `SHOP_SURVIVAL`: 9/9

`docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` was refreshed in `d18332cc` and now documents current native owners rather than retired Phase-0 installers.

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

---

# EXACT NEXT ACTION

Proceed with **Phase 1 semantic benchmark expansion for D1 survival competence**.

The existing 13 D1 semantic cases protect authority and several known mechanics. Expand coverage only where it can expose a real survival-decision defect.

Start by auditing current D1 semantic cases against these failure classes:

1. **resource-spend survival tradeoffs** — avoid spending a discard/hand/consumable when an equivalent or safer clear exists;
2. **redraw quality vs immediate score** — preserve high-value redraw branches when current score gain is insufficient;
3. **terminal-clear hierarchy** — guaranteed clear dominates development except literal round-end resources/equal-clear tie-breaks already encoded;
4. **boss-legality continuity** — root and recursive candidates obey identical boss legality/mechanics;
5. **timeout consistency** — bounded search must not change the underlying decision objective;
6. **public-state uncertainty** — no semantic case may rely on hidden draw order or RNG identity.

Do not add cases merely to increase the count. Every new case must correspond to a plausible live competence failure and identify the canonical owner that would be fixed if it fails.

After identifying a coherent first batch, implement the semantic cases and ask the user to run:

```powershell
git pull
python -m games.balatro.red_white_semantic_benchmark
```

If a new case fails, fix the smallest canonical owner. Do not add wrapper rescues.

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
