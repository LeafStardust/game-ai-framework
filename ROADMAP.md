# ROADMAP — SINGLE SOURCE OF TRUTH

This file is written for an LLM continuing development of this repository.

**This is the only authoritative roadmap, handoff, queue, or current-status document in the repository.**

Rules for future chats:

1. Read this file first.
2. Treat its `CURRENT STATE` and `EXACT NEXT ACTION` sections as authoritative.
3. Other files under `docs/` are supporting architecture, audits, mechanics, validation evidence, or history only. They may explain implementation details but **must never override the current status or queue in this file**.
4. `docs/balatro/BALATRO_IMPLEMENTATION_HISTORY.md` is historical evidence only.
5. If code or a user-provided local test result proves this file stale, update this file in the same development batch after fixing/reconciling the code.
6. Do not create another file with `ROADMAP` in its name. Do not create a second handoff document.

---

# REPOSITORY CONTRACT

- Repository: `LeafStardust/game-ai-framework`
- Active branch: `feat/v1.0-red-white-competence`
- Work only on that branch unless the user explicitly changes scope.
- The user runs tests locally. **Do not run tests from ChatGPT.**
- When the user reports a failure, inspect whether it is a real production regression or a stale test protecting retired architecture before changing behavior.
- When exact repo/branch/path is known, use direct branch-scoped fetch/update/delete operations. Do not waste time rediscovering known paths or probing unrelated history.
- Preserve exact Balatro mechanics, public-state legality, boss rules and hidden-information boundaries.
- Never use hidden RNG state, seeds, future pool order, future identities or other inaccessible information.
- Do not hard-code arbitrary Joker tier lists or named shop-combination strategy tables.
- Prefer canonical ownership over late monkeypatch/rescue wrappers.
- If a wrapper merely injects evidence, mechanics, caching or ordering into an existing final authority, migrate that behavior into the canonical owner and retire the installer.
- Bond/composition and Build Health are evidence, not independent final action authorities.
- Winning the current run is the gameplay objective.

---

# ACTIVE GAMEPLAY OBJECTIVE

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

Feature growth is frozen until this competence gate is stable and reproducible.

Do not start Red Stake or higher-stake progression, another deck, collection-first behavior, Endless-first behavior, a new strategic framework, or broad numerical tuning intended to compensate for semantic/authority defects.

Literal Balatro scoring and legality remain authoritative over strategy labels.

---

# CURRENT STATE — 2026-08-31

Ordinary Red/White mechanics/runtime stabilization is substantially complete. Previous D14/D11 SHOP latency and D1 root-budget blockers are closed unless fresh evidence reproduces them. Phase-A Bond calibration completed its exploratory gate with **no promotion**; production calibration remains unchanged.

The active engineering phase is:

> **Phase 0 — D1 authority consolidation: remove installation-order-dependent wrappers by moving valid behavior into canonical owners without changing intended production semantics.**

## Canonical authority shape

- D1 search/projection: `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`.
- D1 action arbitration: `LiveHandActionPolicy`; effective production strategy-aware policy: `StrategyAwareLiveHandActionPolicy`.
- D1 orchestration/final return: `LiveHandActionDecisionEngine` / path-aware production engine.
- D14 SHOP final authority: `BuildAwareShopArbiter`.
- D11 reroll authority: `BuildAwareShopRerollPolicy`.
- D9 opened-pack authority: `BalatroPackPolicy`.

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

The following behavior has been moved away from installation-order-dependent D1 wrappers into canonical production ownership:

- safe-pace adaptive-search scheduling;
- safe-pace timeout/fallback authority;
- Hook/log-resilience search reserve;
- boss-unconfirmed projection confidence;
- per-decision Bond intent cache;
- Castle discard evidence;
- Burnt Joker discard evidence;
- DNA/Aces evidence;
- hand-repetition evidence;
- Green Joker survival-equivalent Play/Discard preservation;
- Runner / To Do List target-hand evidence;
- Purple-Seal discard candidate/beam preservation;
- Blue-Seal round-end generated-consumable accounting;
- Gold-card preservation as a final play-priority tie-break.

The current sequence is an **ownership refactor**, not a new tuning family. Preserve intended behavior while eliminating late mutation.

## Latest consolidation commits

Target-hand:

- `0defc8a7bb91d5b11b7d3e4905c996e0f50f0474` — native target-hand evidence.
- `65f352cbedae67a246f0c27774549d8e8a36a99a` — native target-hand regression.
- `60f7245939fb29e7e63cadee1cd508efea61cdf6` — remove stale installer-sentinel assertion.

Purple Seal:

- `84252776fe335ede82eba4a16fda33e56ea4b5fb` — native D1 Purple-Seal beam coverage.
- `5ee46673deb9958d33b3b8b2bb90624e6e4ccbce` — retire Purple-Seal installer implementation.
- `9bdef2dbb9c713c2b08febc2bf3ea7ef14eb2034` — stop installing Purple-Seal overlay.
- `2571dedb212e8767d4b0360e99e45e2d9597ccac` — focused native Purple-Seal regression.

Held round-end resources:

- `73b8e8c6291a59c628f3d1ad41b8b754325871b9` — native Blue-Seal terminal accounting and Gold-card play-priority tie-break in `LiveBlindClearPlanner`.
- `f0e646a211f9f5e1ccc42419be3e30d636edabce` — retire held-resource installer implementation to compatibility no-op.
- `9da37efe4ab426fcfd0086b5efad8b6a7b467622` — stop installing held-resource overlay; register Serpent then Hook mechanics explicitly instead of relying on held-resource side effects.
- `a47077b07a2f57257d03e81f15f4c951a1a171c3` — focused native Blue/Gold regression coverage.

**ChatGPT has not run these tests. Local validation is pending from the user.**

---

# LAST USER-PROVIDED LOCAL TEST RESULT

The last reported command was:

```powershell
python -m pytest -q tests/balatro -k "target_hand or runner or todo or strategy_hand"
```

It previously produced one stale-architecture failure:

```text
FAILED tests/balatro/test_balatro_target_hand_engine_policy.py::test_production_stack_installs_target_hand_guard
1 failed, 38 passed, 2743 deselected
```

That failure did **not** indicate missing target-hand behavior. The old installer had deliberately been retired, while one regression still required its sentinel. Commit `60f72459...` corrected that stale assertion instead of reintroducing the wrapper.

No newer local result has been provided yet.

---

# EXACT NEXT ACTION

## First: local focused validation of the completed consolidation batch

The user should pull the branch and run:

```powershell
python -m pytest -q tests/balatro/test_balatro_target_hand_engine_policy.py tests/balatro/test_balatro_purple_seal_d1_native.py tests/balatro/test_balatro_held_round_end_resource_native.py
```

Do not run it from ChatGPT.

### If the focused command fails

- inspect the exact failure directly;
- distinguish a production semantic regression from a stale architecture assertion;
- do not restore retired target-hand, Purple-Seal, or held-resource installers merely to satisfy sentinel-based tests;
- preserve native canonical ownership unless evidence shows the native behavior itself is wrong.

### If the focused command is green

Continue immediately to:

> **`semantic_search_guard_policy` classification and staged ownership migration.**

Do not perform a giant blind rewrite. First classify every behavior currently owned by the module and move concerns one owner at a time.

---

# ORDERED D1 CONSOLIDATION QUEUE

## 1. Target-hand evidence — IMPLEMENTED, LOCAL RETEST PENDING

Expected architecture:

- Runner / To Do List target-hand evidence is consumed natively by canonical D1;
- no production startup target-hand installer;
- no `_target_hand_engine_policy_installed` sentinel requirement.

## 2. Purple Seal discard beam coverage — IMPLEMENTED, LOCAL TEST PENDING

Expected architecture:

- Purple-Seal Tarot-generation opportunities survive D1 child-candidate and discard-beam truncation natively;
- ordinary discard ranking remains authoritative outside the reserved mechanically distinct branch;
- `purple_seal_discard_policy` is compatibility-only and does not mutate planner classes;
- no `_purple_seal_discard_policy_installed` sentinel requirement.

## 3. Held round-end resources — IMPLEMENTED, LOCAL TEST PENDING

Expected architecture:

- Blue-Seal reward accounting happens through canonical terminal D1 valuation only when the round actually clears and the Blue-Seal card remains held;
- consumable capacity caps generated Blue-Seal value;
- Gold-card preservation is only a final play-priority tie-break and cannot outrank better clear/score evidence;
- `held_round_end_resource_policy` is compatibility-only and does not mutate planner classes;
- Serpent and Hook exact mechanics remain explicitly installed in their existing order until their later ownership migrations;
- no `_held_round_end_resource_policy_installed` sentinel requirement.

## 4. `semantic_search_guard_policy` — NEXT AFTER GREEN FOCUSED VALIDATION

This is a larger mixed runtime/search wrapper. Before changing it, classify every behavior it owns.

Known concerns currently mixed into the module include:

- Bond relation filtering for over-broad rank-feature relationships;
- root/child play prefilter bounds;
- root/child discard prefilter bounds and redraw-size diversity;
- root short-play reserve;
- root discard reserve under soft-deadline pressure;
- non-clearing discard quality ordering;
- zero-signal discard redraw-size tie-breaks;
- any patched planner/policy methods that remain in the lower half of the module.

Migration contract:

1. separate Bond-graph semantics from D1 search/runtime behavior;
2. separate candidate generation/prefiltering from value arbitration;
3. move bounded search behavior into the canonical planner owner;
4. move final action comparison behavior into the canonical arbiter/evaluator owner;
5. preserve existing deadlines, root/child beam bounds and exact legality;
6. retire each monkey patch only after its native behavior is covered;
7. do not change tuning merely because ownership changes.

## 5. Remaining exact-mechanics / boss / Cerulean wrappers

Only after narrower evidence/search wrappers are consolidated. Exact mechanics must remain authoritative even if their ownership changes.

---

# PHASE-0 EXIT GATE

Phase 0 is complete only when:

- one documented/enforced final authority exists for each action family;
- remaining late semantic rescue layers are removed or reduced to true compatibility/diagnostic code;
- diagnostics cannot independently plan or change actions;
- production behavior no longer depends on fragile module import/installer order for migrated D1 semantics;
- deterministic focused tests protect behavior rather than retired monkeypatch mechanisms.

Supporting architecture inventory: `docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md`.

**Do not trust that map blindly if it disagrees with current code. It is supporting documentation, not the roadmap. Refresh stale rows as wrappers are retired.**

---

# VALIDATION WORKFLOW

Do not demand the full Balatro suite after every small ownership migration.

For each consolidation item:

1. implement the native ownership change;
2. update/add the smallest focused regression tests;
3. have the user run the smallest targeted pytest command;
4. if green, continue to the next closely related consolidation item;
5. after a coherent consolidation batch, have the user run:

```powershell
python -m pytest -q tests/balatro
```

6. if decision semantics changed materially, also run locally:

```powershell
python -m games.balatro.red_white_semantic_benchmark
```

The full deterministic suite is mandatory before live validation, release promotion, or moving to a major new phase.

Live runs are integration evidence, not the primary progress metric.

---

# CLOSED / DO NOT REOPEN WITHOUT FRESH EVIDENCE

Do not spend time reopening the following merely because old docs or history mention them:

- ordinary D1 competence failures already repaired;
- Mouth discard-only legality;
- Green Joker survival-equivalent authority already migrated;
- Hook/log-resilience reserve already migrated;
- target-hand installer architecture — intentionally retired;
- Purple-Seal installer architecture — intentionally retired;
- held-round-end-resource installer architecture — intentionally retired;
- production-default tuning ContextVar hypothesis — falsified;
- historical SHOP recursive expectation roots;
- BLIND_SELECT quiescence deadlock;
- ROUND_EVAL checkout fast-path semantics;
- D1 root pre-beam wall-clock budget defect;
- live tuner cascading after failed/non-COMPLETE trial;
- Phase-A Bond exploratory tuning — completed with no promotion;
- D14/D11 SHOP latency blocker — closed unless fresh timing evidence reproduces it.

If a new user-provided trace/test reproduces one of these failure classes, reopen it based on that evidence only.

---

# SEMANTIC COMPETENCE CONTRACT

## D1

- guaranteed clear must be taken;
- useful discards must be used when current pace is inadequate;
- trivial tiny plays must not burn hands while a useful discard exists;
- repeated one-card discards must be exceptional unless exact mechanics justify them;
- survival-equivalent lines may preserve valuable held resources;
- forced selections and boss rules are obeyed;
- impossible-clear states maximize remaining progress rather than preserve irrelevant resources;
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

## Phase 1 — semantic benchmark expansion

Expand captured/reconstructed public checkpoints when new failure classes appear. Prefer behavioral properties over fragile exact actions unless exactness is mechanically required.

## Phase 2 — D1 survival competence

Default comparison order:

1. probability of clearing the blind;
2. feasibility/confidence of remaining clear paths;
3. expected progress toward target;
4. expected hands remaining;
5. expected discards remaining;
6. score/economy/generated resources as later tie-breaks.

## Phase 3 — simple shop survival

One shared final comparison scale across Jokers, vouchers, boosters, consumables, rerolls and END_SHOP. Immediate survival/scoring value outranks speculative long-horizon cleverness.

## Phase 4 — coherent build authority

Bond/composition and Build Health remain evidence inside one run-winning decision process. No fake score from structural labels.

## Phase 5 — complex packs/consumables/vouchers/economy

Audit existing implementations rather than rebuilding them. One-layer public expectation remains the normal unopened stochastic boundary.

## Phase 6 — live validation

After deterministic/semantic gates are clean, use focused authoritative live attempts to detect integration/runtime defects. Convert obvious failure classes into deterministic/semantic regressions when practical.

## Phase 7 — numerical tuning

Resume only after semantics and authority are trustworthy. Tune preferences/coefficients, never mechanics, legality, boss rules or hidden-information behavior.

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

Then additional decks, currently planned:

1. Blue Deck — v2.x
2. Yellow Deck — v3.x
3. Green Deck — v4.x
4. Black Deck — v5.x

These future versions must reuse the permanent architecture rather than introduce parallel strategy frameworks.

---

# HISTORY / SUPPORTING DOCS

- `docs/balatro/BALATRO_IMPLEMENTATION_HISTORY.md` — completed implementation/tuning history only.
- `docs/balatro/BALATRO_DECISION_AUTHORITY_MAP.md` — architecture inventory/supporting evidence; refresh when stale.
- other `docs/balatro/*.md` files — mechanics, audits, validation records, strategy/Bond design, runtime evidence.

Again: **none of them define the current queue. This file does.**
