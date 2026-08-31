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
- The Serpent exact post-action draw count on both reusable base D1 and integrated production D1.

`semantic_search_guard_policy` is compatibility-only, production startup no longer installs it, and the completed native search-bound + ordering regression gate is green locally.

`serpent_draw_policy` is now compatibility-only and production startup no longer installs it. Native Serpent regression is pending local validation.

This remains an **ownership refactor, not a tuning family**.

## Latest consolidation commits

Target hand / Purple / held resources:

- `0defc8a7bb91d5b11b7d3e4905c996e0f50f0474` — native target-hand evidence.
- `84252776fe335ede82eba4a16fda33e56ea4b5fb` — native Purple-Seal D1 beam coverage.
- `73b8e8c6291a59c628f3d1ad41b8b754325871b9` — native Blue-Seal terminal accounting and Gold-card tie-break.
- `f0e646a211f9f5e1ccc42419be3e30d636edabce` — held-resource installer compatibility no-op.
- `9da37efe4ab426fcfd0086b5efad8b6a7b467622` — explicit Serpent-then-Hook registration after held-resource installer retirement.

Semantic-search consolidation:

- `10201187` — bounded semantic candidate generation moved into `LiveBlindClearPlanner`.
- `f54aec34` — old semantic guard narrowed to the final two ordering hooks.
- `eda3d146f8ba3af1b58ff1b96991c9784c8b981f` — native search-bound/Bond regression checkpoint.
- `237335e18fddebffdce23d1514ab078c919257a9` — planner estimate ordering made native.
- `44d0856497b44a512d06955c7abb4a504ee7a09f` — strategy discard ordering made native.
- `613a25b58c6c60048dd51e3726d8ededd9587788` — semantic guard installer retired to compatibility no-op.
- `e5f4b6448c6fb9036e78a38702a7fb642dea2af6` — production no longer installs semantic search guard.
- `87746cc00cc7e857dbd25332380b35fff0091c3a` — native semantic ordering regression coverage.

Exact mechanics:

- `89fb1a23f6be232abe327745a4317259f75f673a` — base `LiveBlindClearPlanner` now owns exact Serpent redraw count natively for Play and Discard transitions.
- `4811943d22405005a34912f48200c2189e7e9845` — Serpent installer retired to compatibility no-op.
- `b8840745f770425153f593d7e86ff81e02634dc7` — production no longer installs Serpent overlay; Hook remains explicitly installed.
- `d17f6aee546b7b376c8c41ae775e2f99c11a3c5c` — focused native Serpent regression coverage.

A previous noisy attempted planner rewrite was fully undone before the clean native ordering commit; do not resurrect or reason from that transient state.

**ChatGPT has not run tests.**

---

# LAST USER-PROVIDED LOCAL TEST RESULT

The user reported **green** for the completed semantic-search consolidation gate:

```powershell
git pull
python -m pytest -q tests/balatro/test_balatro_semantic_search_native_bounds.py tests/balatro/test_balatro_semantic_search_native_ordering.py
```

This validates native Bond/search bounds, planner estimate ordering, strategy zero-signal discard ordering, and retirement of the production semantic-search installer.

---

# EXACT NEXT ACTION

## First: local focused validation of native Serpent ownership

The user should run:

```powershell
git pull
python -m pytest -q tests/balatro/test_balatro_serpent_native.py
```

Do not run it from ChatGPT.

### If it fails

- inspect the exact failure;
- do not restore `install_serpent_draw_policy()` merely to satisfy a sentinel/import-order test;
- preserve The Serpent literal rule: after each Play or Discard, draw exactly 3 cards while the boss is active;
- if the boss is disabled by owned Joker mechanics, ordinary draw behavior must apply.

### If it is green

Continue immediately with:

> **`hook_planner_integration_policy` exact forced-discard branch migration.**

The Hook wrapper is heavier than Serpent because it currently replaces base `_estimate_play` to account for forced-discard score branches and branch-specific hand refill. Move that exact mechanic into the canonical planner carefully, add focused behavior regression coverage, and only then retire the installer.

After Hook, inspect Cerulean and the remaining boss/live-state wrappers to distinguish canonical state parsing from late mutation.

Do not begin higher stakes or broad tuning.

---

# ORDERED D1 CONSOLIDATION QUEUE

## 1. Target-hand evidence — IMPLEMENTED

- Runner / To Do List evidence is consumed natively by canonical D1.
- Target-hand installer architecture is intentionally retired.

## 2. Purple Seal discard beam coverage — IMPLEMENTED

- Purple-Seal opportunities survive child-candidate/beam truncation natively.
- Ordinary discard ranking remains authoritative outside the reserved distinct branch.
- `purple_seal_discard_policy` is compatibility-only.

## 3. Held round-end resources — IMPLEMENTED

- Blue-Seal reward accounting is native terminal valuation on actual round end.
- Consumable capacity is respected.
- Gold preservation is only a final play-priority tie-break.
- `held_round_end_resource_policy` is compatibility-only.

## 4. `semantic_search_guard_policy` — IMPLEMENTED AND LOCALLY VALIDATED

Native ownership covers Bond rank filtering, bounded candidate generation, redraw diversity, root reserves, planner recovery ordering, and strategy zero-signal discard ordering.

## 5. Remaining exact-mechanics / boss / Cerulean wrappers — ACTIVE

### 5a. Serpent — IMPLEMENTED, LOCAL TEST PENDING

- reusable `LiveBlindClearPlanner` natively forces post-action draw count to 3 under active The Serpent;
- integrated production D1 already owns the same rule natively;
- boss-disable semantics preserve ordinary draw count;
- `serpent_draw_policy` is compatibility-only;
- package startup no longer installs it.

### 5b. Hook — NEXT AFTER SERPENT GREEN

`hook_planner_integration_policy` still mutates base `_estimate_play` for exact forced-discard score branches. Preserve this literal mechanic while moving it into canonical planner ownership.

### 5c. Cerulean / remaining boss-live-state wrappers — AFTER HOOK

Inspect whether each remaining wrapper is canonical state parsing, exact mechanics adaptation, or removable late mutation before changing ownership.

Migration contract:

1. exact Balatro mechanics remain authoritative;
2. do not merge distinct boss mechanics into generic heuristics;
3. move behavior only when a canonical owner is clear;
4. add focused behavior regressions before retiring each installer;
5. preserve public-state-only information boundaries;
6. do not change tuning merely because ownership changes.

---

# PHASE-0 EXIT GATE

Phase 0 is complete only when:

- one documented/enforced final authority exists for each action family;
- remaining late semantic rescue layers are removed or reduced to true compatibility/diagnostic code;
- diagnostics cannot independently plan or change actions;
- production behavior no longer depends on fragile module import/installer order for migrated D1 semantics;
- deterministic focused tests protect behavior rather than retired monkeypatch mechanisms.

Supporting architecture inventory: `docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md`.

Do not trust that map if it conflicts with current code; refresh stale rows as wrappers are retired.

---

# VALIDATION WORKFLOW

Do not demand the full Balatro suite after every small migration.

For each consolidation item:

1. implement native ownership;
2. add/update the smallest focused regression;
3. have the user run the targeted command, always beginning with `git pull`;
4. if green, continue immediately to the next closely related item;
5. after a coherent batch, have the user run:

```powershell
git pull
python -m pytest -q tests/balatro
```

6. if decision semantics changed materially, also run locally:

```powershell
python -m games.balatro.red_white_semantic_benchmark
```

The full deterministic suite is mandatory before live validation, release promotion, or a major phase transition.

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
- production-default tuning ContextVar hypothesis — falsified;
- historical SHOP recursive expectation roots;
- BLIND_SELECT quiescence deadlock;
- ROUND_EVAL checkout fast-path semantics;
- D1 root pre-beam wall-clock budget defect;
- live tuner cascading after failed/non-COMPLETE trial;
- Phase-A Bond exploratory tuning — completed with no promotion;
- D14/D11 SHOP latency blocker unless fresh timing evidence reproduces it.

Reopen only from fresh user-provided test/trace evidence.

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

---

# HISTORY / SUPPORTING DOCS

- `docs/balatro/BALATRO_IMPLEMENTATION_HISTORY.md` — completed implementation/tuning history only.
- `docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` — architecture inventory/supporting evidence; refresh when stale.
- other `docs/balatro/*.md` — mechanics, audits, validation records, strategy/Bond design, runtime evidence.

Again: **none of them define the current queue. This file does.**
