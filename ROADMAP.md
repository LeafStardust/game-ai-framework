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

Do not start:

- Red Stake or higher-stake progression;
- another deck;
- collection-first behavior;
- Endless-first behavior;
- a new strategic framework;
- broad numerical tuning intended to compensate for semantic/authority defects.

Literal Balatro scoring and legality remain authoritative over strategy labels.

---

# CURRENT STATE — 2026-08-31

## High-level state

Ordinary Red/White mechanics/runtime stabilization is substantially complete. Previous D14/D11 SHOP latency and D1 root-budget blockers are closed unless fresh evidence reproduces them. Phase-A Bond calibration completed its exploratory gate with **no promotion**; production calibration remains unchanged.

The active engineering phase is:

> **Phase 0 — D1 authority consolidation: remove installation-order-dependent wrappers by moving valid behavior into canonical owners without changing intended production semantics.**

Do not reopen closed runtime/tuning work without fresh evidence.

## Canonical D1 authority shape

- D1 search/projection: `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`.
- D1 action arbitration: `LiveHandActionPolicy`; effective production strategy-aware policy: `StrategyAwareLiveHandActionPolicy`.
- D1 orchestration/final return: `LiveHandActionDecisionEngine` / path-aware production engine.
- D14 SHOP final authority: `BuildAwareShopArbiter`.
- D11 reroll authority: `BuildAwareShopRerollPolicy`.
- D9 opened-pack authority: `BalatroPackPolicy`.

Target architectural shape:

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

## D1 consolidation already completed

The following behavior has already been moved away from installation-order-dependent D1 wrappers into canonical production ownership:

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
- Runner / To Do List target-hand evidence.

The current sequence is an **ownership refactor**, not a new tuning family. Preserve intended behavior while eliminating late mutation.

---

# LAST LOCAL TEST RESULT AND WHY IT FAILED

The user last ran:

```powershell
python -m pytest -q tests/balatro -k "target_hand or runner or todo or strategy_hand"
```

Result reported by the user before the latest test correction:

```text
....................................F..
1 failed, 38 passed, 2743 deselected

FAILED tests/balatro/test_balatro_target_hand_engine_policy.py::test_production_stack_installs_target_hand_guard
AssertionError: assert False
getattr(StrategyAwareLiveHandActionPolicy, "_target_hand_engine_policy_installed", False) == False
```

This failure did **not** indicate missing target-hand behavior.

What happened:

1. `target_hand_engine_policy` production mutation had already been deliberately retired.
2. Runner/To Do List target-hand evidence had already been moved natively into D1 / `StrategyAwareLiveHandActionPolicy` ownership.
3. Production therefore correctly no longer exposed `_target_hand_engine_policy_installed`.
4. One old regression still asserted that the retired installer sentinel must exist.
5. The stale test was therefore checking the old architecture while the implementation and newer native-evidence test checked the new architecture.

Relevant commits:

- `0defc8a7bb91d5b11b7d3e4905c996e0f50f0474` — `refactor(balatro): make target hand evidence native to D1`
- `65f352cbedae67a246f0c27774549d8e8a36a99a` — `test(balatro): lock native target hand evidence`
- `e32231503bc9aef72d76cd2c4f1818335afd77e0` — `docs(balatro): hand off D1 authority consolidation`
- `60f7245939fb29e7e63cadee1cd508efea61cdf6` — `test(balatro): remove stale target hand installer assertion`

`60f72459...` changed the obsolete production-stack assertion so tests now validate the intended architecture: native behavior exists and the old installer sentinel is absent.

**Important:** ChatGPT has not run the corrected test. Local validation is pending from the user.

---

# EXACT NEXT ACTION

## First: validate the already-committed target-hand test correction locally

Ask the user to pull and rerun the same focused command:

```powershell
python -m pytest -q tests/balatro -k "target_hand or runner or todo or strategy_hand"
```

Do not run it from ChatGPT.

### If that command fails

- inspect the new failure directly;
- determine whether it is a real target-hand semantic regression or another stale architecture assertion;
- do not reintroduce `install_target_hand_engine_policy()` merely to satisfy a sentinel test;
- preserve native Runner/To Do List target-hand evidence in canonical D1 ownership.

### If that command is green

Continue immediately to the next D1 consolidation target:

> **`purple_seal_discard_policy`**

Do not spend a turn replanning after a green result.

---

# ORDERED D1 CONSOLIDATION QUEUE

Handle one ownership migration at a time. Preserve semantics, move valid behavior native, retire installer, add/update focused regression coverage, then have the user validate locally.

## 1. Target-hand evidence — IMPLEMENTED, LOCAL RETEST PENDING

Expected architecture:

- Runner / To Do List target-hand evidence is consumed natively by `StrategyAwareLiveHandActionPolicy` / canonical D1 path;
- no production startup installer for target-hand evidence;
- no `_target_hand_engine_policy_installed` sentinel requirement;
- pure compatibility helpers may remain if harmless and tested.

Current code/test correction ends at commit `60f72459...`.

## 2. Purple Seal discard beam coverage — NEXT AFTER GREEN TARGET-HAND RETEST

Current known architecture problem:

- `purple_seal_discard_policy` still mutates D1 candidate/beam behavior late;
- it wraps discard-subset construction/diversification so Purple-Seal Tarot-generation opportunities survive candidate truncation;
- the behavior is legitimate but ownership is wrong.

Migration contract:

- inspect `games/balatro/purple_seal_discard_policy.py` and canonical planner methods before editing;
- move Purple-Seal discard opportunity preservation directly into the canonical D1 planner (`D1LiveBlindClearPlanner` / its owning hand planner methods as actually defined on the branch);
- preserve exact mechanic: a useful Purple-Seal discard branch must not disappear merely because generic beam truncation removes it;
- preserve legality and ordinary discard ranking semantics;
- remove its production installer from `games/balatro/__init__.py` once behavior is native;
- make the old module inert/compatibility-only or delete it if nothing valid depends on it;
- update regression coverage so it proves native behavior and absence of installation-order mutation rather than presence of an installer sentinel.

## 3. Held round-end resources

Likely target: `held_round_end_resource_policy`.

Migration contract:

- move Blue-Seal/Gold-card projection and survival-equivalent final ordering into canonical planner/evaluator ownership;
- do not let resource preservation override a materially better clear probability;
- resource value is a later tie-break among survival-equivalent or otherwise appropriately comparable lines;
- retire startup mutation once native behavior is covered.

## 4. `semantic_search_guard_policy`

This is a larger mixed runtime/search wrapper. Do not treat it like a narrow evidence hook.

Before changing it:

- classify every behavior it owns;
- separate legality/mechanics, projection, evaluation, search bounds, arbitration, guard and diagnostics;
- migrate each concern to its canonical owner;
- preserve bounded runtime and root/child candidate behavior;
- do not perform a giant blind rewrite.

## 5. Remaining exact-mechanics / boss / Cerulean wrappers

Only after narrower evidence/projection wrappers are consolidated.

Exact mechanics must remain authoritative even if their ownership changes.

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
3. ask the user for the smallest targeted pytest command covering that item;
4. if green, continue to the next closely related consolidation item;
5. after a coherent consolidation batch, ask for:

```powershell
python -m pytest -q tests/balatro
```

6. if decision semantics changed materially, also ask for:

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

The checked-in Red/White semantic benchmark exists to detect bad composition between individually reasonable components.

Priority properties include:

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
