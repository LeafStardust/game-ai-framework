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

## Native ownership status

Validated locally:

- semantic-search guard behavior;
- The Serpent exact post-action draw count;
- The Hook branch-specific forced-discard refill/search transition;
- Cerulean Bell public `forced_selection` observation and translation.

Implemented, local validation pending:

- Ectoplasm `G.GAME.ecto_minus` observation → native state translation;
- round-reset discard allowance observation → native `BalatroState` fields and copy semantics.

The corresponding Ectoplasm and round-resource installers are compatibility-only and production startup no longer installs them.

Two substantive migrations remain after this checkpoint:

1. `joker_generation_pool_live_state_policy` observation/state plumbing;
2. `boss_hand_constraint_policy` final D1 strategy-authority migration.

This remains an **ownership refactor, not a tuning family**.

## Latest final-bucket commits

Cerulean:

- `41f4a0daf6823b05d0a043638c09cc6c335c3e84` — canonical translator hydrates forced selection.
- `47717ffdbc13ccc9a2e09987eb48df29e3097a79` — canonical observer exposes forced selection.
- `17f7c54a9f507238d829fe3dbb52b48f2a8831fb` — installer retired.
- `4a060ab9388d3b9fc887c4b0fff70e787abcb4ef` — package startup no longer installs it.
- `34787bce95a2482ea30362dc62a109fdfcf8b58a` — focused regression; user reported green.

Ectoplasm / round resources:

- `52245a3fc80121309f6f985cc5b9d4e67f021a50` — round-reset discard fields/copy made native to `BalatroState`.
- `5fa1d29074fc6e98c2210c36d25e0c6311232055` — translator hydrates Ectoplasm + round-reset resources natively.
- `a729a7a2161784c8d4d92f8a2b7607d7e87db57c` — observer exposes both resource fields with a surgical diff.
- `a59aef56872fcaa5e86c80b8ce6687b94620a32b` — Ectoplasm installer retired.
- `66892ec5fd3a650db45b2af4efe5aec15eb433e5` — round-resource installer retired.
- `9a7d50bd4813efa0ffa921e20cbbf6218712b8f0` — package startup no longer installs either adapter.
- `29d0445d1f3bcdd1f4556a917994df8050dc8430` — focused native live-resource regression coverage.

An intermediate observer rewrite (`a8ddaf1a`) introduced formatting/comment noise only; `a729a7a2` restored the original observer structure and retained only the intended native fields. Do not reason from the noisy transient diff.

**ChatGPT has not run tests.**

---

# LAST USER-PROVIDED LOCAL TEST RESULT

The user reported **green** for native Cerulean ownership:

```powershell
git pull
python -m pytest -q tests/balatro/test_balatro_cerulean_live_state_native.py
```

---

# EXACT NEXT ACTION

## First: validate native Ectoplasm + round-resource ownership

Run locally:

```powershell
git pull
python -m pytest -q tests/balatro/test_balatro_live_resource_state_native.py
```

Do not run it from ChatGPT.

### If green

Proceed immediately with:

> **`joker_generation_pool_live_state_policy` native observation/state migration.**

That module currently mutates all three of:

- `live_memory_observer.snapshot_payload_from_live_memory`;
- `DefaultBalatroStateTranslator.translate`;
- `BalatroState.__init__` / `BalatroState.copy`.

Preserve its public-information boundary and catalogue caching, but move persistent state fields/copy semantics into `BalatroState`, translation into the canonical translator, and live snapshot emission into the observation boundary. Only retire installation after focused regression coverage.

Then migrate `boss_hand_constraint_policy` into `StrategyAwareLiveHandActionPolicy` / canonical D1 authority.

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

### 5c. Cerulean — IMPLEMENTED AND LOCALLY VALIDATED

### 5d. Ectoplasm + round-reset resources — IMPLEMENTED, LOCAL TEST PENDING

### 5e. Joker-generation-pool live state — NEXT

### 5f. Boss-hand constraints — FINAL SUBSTANTIVE MIGRATION

After 5f, perform the Phase-0 exit gate rather than inventing another cleanup queue.

---

# PHASE-0 EXIT GATE

Phase 0 is complete only when:

- one documented/enforced final authority exists for each action family;
- remaining late semantic rescue layers are removed or reduced to true compatibility/diagnostic code;
- true observation adapters are native at the observer/translator boundary rather than installed via class/function mutation;
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
- Cerulean installer architecture;
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
