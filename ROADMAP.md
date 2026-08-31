# ROADMAP — SINGLE SOURCE OF TRUTH

This file is written for an LLM continuing development of this repository.

**This is the only authoritative roadmap, handoff, queue, or current-status document in the repository.**

Rules for future chats:

1. Read this file first.
2. Treat `CURRENT STATE` and `EXACT NEXT ACTION` as authoritative.
3. Other files under `docs/` are supporting architecture/history only and must not override this file.
4. `docs/balatro/BALATRO_IMPLEMENTATION_HISTORY.md` is historical evidence only.
5. If code or a user-provided local test result proves this file stale, update it in the same development batch.
6. Do not create another roadmap/handoff file.

---

# REPOSITORY CONTRACT

- Repository: `LeafStardust/game-ai-framework`
- Active branch: `feat/v1.0-red-white-competence`
- Work only on that branch unless the user explicitly changes scope.
- The user runs tests locally. **Do not run tests from ChatGPT.**
- When giving local validation commands, include `git pull` first.
- When a test fails, distinguish a production regression from a stale test protecting retired architecture before changing behavior.
- Preserve exact Balatro mechanics, public-state legality, boss rules, and hidden-information boundaries.
- Never use hidden RNG state, seeds, future pool order, future identities, or inaccessible information.
- Do not hard-code arbitrary Joker tier lists or named shop-combination strategy tables.
- Prefer canonical ownership over late monkeypatch/rescue wrappers.
- Bond/composition and Build Health are evidence, not independent final action authorities.
- Winning the current run is the gameplay objective.

---

# ACTIVE GAMEPLAY OBJECTIVE

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

Feature growth is frozen until this competence gate is stable and reproducible.

Do not start higher-stake progression, another deck, collection-first behavior, Endless-first behavior, a new strategy framework, or broad numerical tuning intended to compensate for semantic/authority defects.

Literal Balatro scoring and legality remain authoritative over strategy labels.

---

# CURRENT STATE — 2026-08-31

Ordinary Red/White mechanics/runtime stabilization is substantially complete. Previous D14/D11 SHOP latency and D1 root-budget blockers are closed unless fresh evidence reproduces them. Phase-A Bond calibration completed its exploratory gate with **no promotion**; production calibration remains unchanged.

The active engineering phase is:

> **Phase 0 — D1 authority consolidation: remove installation-order-dependent wrappers by moving valid behavior into canonical owners without changing intended production semantics.**

## Canonical authority shape

- D1 search/projection: `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`.
- D1 arbitration: `LiveHandActionPolicy`; production strategy-aware authority: `StrategyAwareLiveHandActionPolicy`.
- D1 orchestration/final return: `LiveHandActionDecisionEngine` / path-aware production engine.
- D14 SHOP: `BuildAwareShopArbiter`.
- D11 reroll: `BuildAwareShopRerollPolicy`.
- D9 opened pack: `BalatroPackPolicy`.

Target architecture:

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

## D1 ownership migrations implemented so far

The following behavior is now owned natively rather than by late D1 installation-order wrappers:

- safe-pace adaptive-search scheduling and timeout/fallback authority;
- Hook/log-resilience search reserve;
- boss-unconfirmed projection confidence;
- per-decision Bond intent cache;
- Castle, Burnt Joker, DNA/Aces, hand-repetition, and Green-Joker evidence;
- Runner / To Do List target-hand evidence;
- Purple-Seal discard candidate/beam preservation;
- Blue-Seal round-end generated-consumable accounting;
- Gold-card final play-priority preservation;
- semantic Bond rank-relation guard;
- root/child play and discard prefilter bounds;
- redraw-size diversity, short-play reserve, and root discard reserve;
- planner non-clearing discard quality ordering;
- strategy zero-signal discard redraw-size ordering;
- The Serpent exact post-action draw count on both reusable base D1 and integrated production D1;
- The Hook branch-specific post-forced-discard refill/search transition on reusable base D1;
- Cerulean Bell public `forced_selection` observation and translation from live memory into `BalatroCard`.

`semantic_search_guard_policy`, `serpent_draw_policy`, `hook_planner_integration_policy`, and `cerulean_live_state_policy` are compatibility-only; production startup no longer installs them. Semantic, Serpent, and Hook focused native regression gates are green locally. Cerulean native regression is pending local validation.

This remains an **ownership refactor, not a tuning family**.

## Latest consolidation commits

Exact mechanics / live-state:

- `89fb1a23f6be232abe327745a4317259f75f673a` — native Serpent draw count.
- `d17f6aee546b7b376c8c41ae775e2f99c11a3c5c` — focused Serpent regression; green locally.
- `65ae958dc7f9fd28277aa66c79ec44491a4caf68` — native Hook branch refill/search.
- `84ca995c5a1878752fe79fa82c7ee5a28ba66b8f` — focused Hook regression; green locally.
- `41f4a0daf6823b05d0a043638c09cc6c335c3e84` — canonical translator hydrates Cerulean forced selection.
- `47717ffdbc13ccc9a2e09987eb48df29e3097a79` — canonical memory observer exposes Cerulean forced selection.
- `17f7c54a9f507238d829fe3dbb52b48f2a8831fb` — Cerulean installer retired to compatibility no-op.
- `4a060ab9388d3b9fc887c4b0fff70e787abcb4ef` — package startup no longer installs Cerulean overlay.
- `34787bce95a2482ea30362dc62a109fdfcf8b58a` — focused native Cerulean observation/translation regression.

**ChatGPT has not run tests.**

---

# LAST USER-PROVIDED LOCAL TEST RESULT

The user reported **green** for native Hook ownership:

```powershell
git pull
python -m pytest -q tests/balatro/test_balatro_hook_native.py
```

---

# EXACT NEXT ACTION

## First: local focused validation of native Cerulean live-state ownership

The user should run:

```powershell
git pull
python -m pytest -q tests/balatro/test_balatro_cerulean_live_state_native.py
```

Do not run it from ChatGPT.

### If green

Continue immediately with the remaining live-state/boss installer classification. Prioritize still-installed modules that alter observation or D1 semantics, especially:

- `ectoplasm_live_state_policy`;
- `joker_generation_pool_live_state_policy`;
- `round_resource_live_state_policy`;
- `boss_hand_constraint_policy`.

Classify each as:

1. canonical observation/state parsing — migrate into observer/translator if it is still installed as a monkeypatch;
2. exact mechanics adaptation — move into the canonical mechanics/planner owner;
3. semantic rescue/duplicate policy — retire after native ownership exists.

Do not begin higher stakes or broad tuning.

---

# ORDERED D1 CONSOLIDATION QUEUE

## 1. Target-hand evidence — IMPLEMENTED

## 2. Purple Seal discard beam coverage — IMPLEMENTED

## 3. Held round-end resources — IMPLEMENTED

## 4. `semantic_search_guard_policy` — IMPLEMENTED AND LOCALLY VALIDATED

## 5. Remaining exact-mechanics / boss / live-state wrappers — ACTIVE

### 5a. Serpent — IMPLEMENTED AND LOCALLY VALIDATED

### 5b. Hook — IMPLEMENTED AND LOCALLY VALIDATED

### 5c. Cerulean — IMPLEMENTED, LOCAL TEST PENDING

### 5d. Remaining installed boss/live-state wrappers — NEXT AFTER CERULEAN GREEN

This is the final consolidation sub-bucket before the Phase-0 exit gate.

---

# PHASE-0 EXIT GATE

Phase 0 is complete only when:

- one documented/enforced final authority exists for each action family;
- remaining late semantic rescue layers are removed or reduced to true compatibility/diagnostic code;
- true observation adapters are native at the observer/translator boundary rather than installed via class/function mutation;
- diagnostics cannot independently plan or change actions;
- production behavior no longer depends on fragile module import/installer order for migrated D1 semantics;
- deterministic focused tests protect behavior rather than retired monkeypatch mechanisms.

Supporting architecture inventory: `docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md`.

---

# VALIDATION WORKFLOW

For each consolidation item:

1. implement native ownership;
2. add/update the smallest focused regression;
3. have the user run the targeted command, always beginning with `git pull`;
4. if green, continue immediately;
5. after the final consolidation bucket, run:

```powershell
git pull
python -m pytest -q tests/balatro
```

6. if decision semantics changed materially, also run locally:

```powershell
python -m games.balatro.red_white_semantic_benchmark
```

The full deterministic suite is mandatory before Phase 0 is declared complete.

---

# CLOSED / DO NOT REOPEN WITHOUT FRESH EVIDENCE

- ordinary D1 competence failures already repaired;
- Mouth discard-only legality;
- Green Joker survival-equivalent authority;
- Hook/log-resilience search reserve;
- target-hand installer architecture;
- Purple-Seal installer architecture;
- held-round-end-resource installer architecture;
- semantic-search-guard installer architecture;
- Serpent installer architecture;
- Hook planner installer architecture;
- production-default tuning ContextVar hypothesis — falsified;
- historical SHOP recursive expectation roots;
- BLIND_SELECT quiescence deadlock;
- ROUND_EVAL checkout fast-path semantics;
- D1 root pre-beam wall-clock budget defect;
- live tuner cascading after failed/non-COMPLETE trial;
- Phase-A Bond exploratory tuning — completed with no promotion;
- D14/D11 SHOP latency blocker unless fresh timing evidence reproduces it.

---

# SEMANTIC COMPETENCE CONTRACT

## D1

- guaranteed clear must be taken;
- useful discards must be used when current pace is inadequate;
- trivial tiny plays must not burn hands while useful discard recovery exists;
- repeated one-card discards must be exceptional unless exact mechanics justify them;
- survival-equivalent lines may preserve valuable held resources;
- forced selections and boss rules are obeyed;
- impossible-clear states maximize remaining progress rather than irrelevant resources;
- timeout retains completed canonical evidence;
- late evidence cannot reverse a finalized survival class without valid canonical authority.

## SHOP

- affordable obvious immediate scoring is bought when underpowered and legal;
- mechanical conflicts remain authoritative;
- dead components may be replaced by materially better legal candidates;
- interest/economy is preserved for marginal purchases;
- rich underpowered builds may reroll when visible offers are inadequate;
- rerolls respect survival reserve.

## Build

- functioning engines survive marginal side-development offers;
- real scaling deficits are detected;
- dormant/theoretical synergy does not count as realized scoring;
- coherent pivots remain possible when whole-build value is genuinely better.

## Packs/resources/bosses

- hidden future value is never predicted;
- deterministic visible improvements are not skipped without reason;
- speculative option value does not override immediate survival without explicit projected evidence;
- boss mechanics and legality remain exact.

---

# LATER PHASES — BLOCKED UNTIL PHASE 0 IS CLEAN

1. Semantic benchmark expansion.
2. D1 survival competence refinement.
3. Simple shop survival.
4. Coherent build authority.
5. Complex packs/consumables/vouchers/economy audit.
6. Live validation.
7. Numerical tuning only after semantics/authority are trustworthy.

Promotion requires a fresh controlled comparison with at least 20 completed episodes per arm and non-regression/pathology gates.

---

# FUTURE VERSION PROGRESSION — BLOCKED

After Red/White competence passes:

| Version | Stake | Main new adaptation |
|---|---|---|
| v1.1 | Red | No Small Blind reward money |
| v1.2 | Green | Green Stake score scaling |
| v1.3 | Black | Eternal Joker adaptation |
| v1.4 | Blue | Reduced-discard adaptation |
| v1.5 | Purple | Purple Stake score scaling |
| v1.6 | Orange | Perishable Joker adaptation |
| v1.7 | Gold | Rental Joker adaptation and all-stakes validation |

Then additional decks: Blue, Yellow, Green, Black. Reuse the permanent architecture rather than parallel strategy frameworks.
