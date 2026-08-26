# Balatro Local Validation Gate

Date: 2026-08-26

This document records defects discovered only when the user runs the local Balatro deterministic suite. It is not a claim that current HEAD is green.

## Current gate

The semantic/runtime implementation pass is complete enough for local validation, but current HEAD must remain frozen for tuning/live baselines until `python -m pytest tests/balatro` completes without collection/runtime failures.

## Collection blocker 1 — stale discovery tie-break import

Observed failure:

```text
ImportError: cannot import name 'DISCOVERY_TIEBREAK_CAP' from 'games.balatro.discovery'
```

Root cause:

- `voucher_parent_literal_policy.py` introduced Blank/Antimatter progression using the historical `DISCOVERY_TIEBREAK_CAP` symbol;
- `discovery.py` exposes the newer value-aware `bounded_discovery_tiebreak()` primitive and no longer defined that compatibility symbol;
- importing `games.balatro` therefore aborted during package initialization, creating many secondary collection errors including `KeyError: 'games.balatro'`.

Repair:

- commit `7746ac5` restores a compatibility-only `DISCOVERY_TIEBREAK_CAP` derived from floating-point spacing (`nextafter(4.0, inf) - 4.0`);
- this is a machine-precision exact-tie increment, not a gameplay/tuning utility coefficient;
- ordinary discovery decisions continue to use `bounded_discovery_tiebreak()`.

Validation status: **resolved in the user's next collection run; suite then collected 2644 tests with one remaining collection error**.

## Collection blocker 2 — eager `games.balatro.live` package imports

Observed failure:

```text
ImportError: cannot import name 'Composition' from partially initialized module
'games.balatro.bonds.composer' (most likely due to a circular import)
```

Root cause:

- `bonds.composer` imports build strategy/scoring support;
- `build.literal_score_expectation` imports the specific scoring submodule `live.final_joker_outcomes`;
- Python initializes `games.balatro.live.__init__` before loading that submodule;
- the old live package initializer eagerly imported `live.bond_health`;
- `live.bond_health` imports `bonds.build_health`, which imports `bonds.composer` again before its `Composition` definition exists.

The resulting cycle was:

```text
bonds.composer
-> build.literal_score_expectation
-> live.final_joker_outcomes
-> live.__init__
-> live.bond_health
-> bonds.build_health
-> bonds.composer
```

Repair:

- commit `48ab397` converts the convenience exports in `games.balatro.live.__init__` to PEP-562-style lazy `__getattr__` resolution;
- direct submodule imports no longer initialize unrelated Bond-health/strategy/shop subsystems;
- the existing public package exports remain available when accessed explicitly.

Validation status: **resolved in the next user run; collection completed and execution reached runtime test failures**.

## Runtime blocker 1 — recursive D14/pack expectation construction

Observed failure pattern repeated deeply through the traceback:

```text
BalatroShopPolicy()
-> VoucherParentLiteralEvaluator
-> RerollJokerExpectationEvaluator
-> ShopUtilityScale
-> HeldConsumableOptionEvaluator
-> BalatroPackPolicy
-> EctoplasmExpectationEvaluator
-> BalatroShopPolicy()
-> ...
```

Root cause:

- `EctoplasmExpectationEvaluator.__init__` eagerly constructed a default `BalatroShopPolicy` only to build its future-Joker expectation authority;
- Ectoplasm itself is installed underneath pack/consumable/shop policy constructors;
- constructing that nested shop policy therefore rebuilt the entire D14/pack expectation graph recursively before the outer graph finished initialization.

Repair:

- commit `1671ab4` removes eager `BalatroShopPolicy` construction from `EctoplasmExpectationEvaluator.__init__`;
- injected `future_joker` evaluators remain supported exactly as before;
- the default future-Joker evaluator is now constructed lazily only when Ectoplasm is actually evaluated, after the outer policy graph has completed wiring;
- no gameplay utility, thresholds, or Ectoplasm semantics were changed.

Validation status: **resolved enough for the next run to execute tests; later failures are behavioral rather than constructor recursion**.

## Runtime blocker 2 — Hanged Man simulated permanent destruction applied twice

Observed failures included:

```text
test_held_hanged_man_uses_two_independently_positive_thinning_targets
test_held_hanged_man_preserves_single_good_thinning_target_with_free_slot
test_full_slots_can_use_single_positive_hanged_man_target
test_hanged_man_timing_fails_closed_on_ambiguous_owned_live_id
test_hanged_man_simulation_removes_exact_owned_ids_without_mutating_live_state
```

Root cause:

- permanent playing-card destruction was centralized in `project_destroyed_playing_cards`;
- `HangedMan.use()` now already removes destroyed cards from the authoritative copied `owned_deck` and applies destruction-triggered Joker state;
- `LiveConsumableTimingPolicy._simulate_use()` still contained its older second `_remove_from_owned_deck()` pass;
- valid Hanged Man simulations therefore destroyed the owned cards once, failed to find them during the second removal, and returned `None`;
- the same ordering meant duplicate/ambiguous live IDs were not validated before the shared destruction transition selected one match.

Repair:

- commit `38411ed` validates each selected Hanged Man live ID against `owned_deck` before applying the copied use;
- missing or non-unique authoritative identities fail closed before mutation;
- `HangedMan.use()` remains the sole permanent-destruction transition during simulation;
- the simulator no longer attempts a second owned-deck removal;
- live state remains untouched because all work occurs on the deep copied state.

Validation status: **pending user rerun**.

## Regression-fixture update — D8/D9/D11 contracts

The same runtime batch exposed several assertions that encoded retired pre-repair behavior rather than production defects.

### Opened-pack targeted cards

Death and generic targeted-Tarot tests explicitly supplied `skip_bias=0.35` while also expecting any positive literal target to be selected. That contradicts the repaired D9 contract: opened-pack acquisition cost is sunk, production Skip is `0.0`, and deterministic targeted cards receive only their literal D10/B6 target value rather than a generic Tarot/shop utility floor.

Repairs:

- commit `fd73379` updates the Death directional-target regression to use the sunk-cost zero baseline;
- commit `ee7aae1` updates the generic targeted-pack regression likewise and checks the current `D10/B6 target gain` rationale.

### Unobserved future pools

Legacy autonomous shop tests created bare synthetic `BalatroState` objects with no observed Joker/Planet/Tarot/Spectral generation catalogues, then expected paid rerolls or stochastic boosters to proceed from fixed family priors. Repaired D8/D11 intentionally fail closed when those public catalogues are unavailable.

Repairs:

- commit `db2fe3d` updates bare-state Celestial/Arcana shop regressions to assert fail-closed `END_SHOP` instead of restoring fixed family priors;
- commit `f10fea5` updates the bare-state paid-reroll regression to assert `HOLD_REROLL`/`END_SHOP` when the future public pool is absent;
- dedicated public-pool expectation tests remain responsible for proving positive D8/D11 behavior when authoritative catalogue state is supplied.

Validation status: **pending user rerun**.

## Regression-fixture update — exact D6/D8 mechanics

A later ten-failure batch exposed another set of old scaffold assumptions.

### Castle tolerance ownership

`_safe_castle_discard_alternative()` no longer owns a private survival-loss constant. It consumes D1's `safe_clear_probability_tolerance`. The direct unit fixture omitted `result.thresholds`, which correctly produced a zero tolerance and rejected its 0.50 -> 0.49 redirect.

Repair:

- commit `157d9b9` supplies the canonical D1 tolerance in the direct Castle fixture; production code is unchanged.

### Blue Joker / Hanged Man

The old pack-action test expected Blue Joker to remove Hanged Man from the action set entirely. That hard veto was intentionally retired: B6 now subtracts the exact `2 Chips × cards removed × active Blue Jokers` opportunity cost and may still admit profitable thinning.

Repair:

- commit `36da4d1` updates the regression to keep Hanged Man as a candidate and leave value admission to D6.

### Targeted Tarot/Spectral literal value

After generic per-transformation utility was removed, a plain Chariot target is not automatically positive merely because it changes a card. Opened-pack targeting must demonstrate actual modeled value. The Tarot coverage now uses Death's positive directional copy, while Spectral coverage uses Deja Vu's explicit Red-Seal intrinsic value, both against sunk-cost Skip=0.

Repairs:

- commit `eb31f96` updates targeted Tarot coverage to a positive literal Death target;
- commit `5ac3153` aligns targeted Spectral coverage with the same literal/sunk-cost contract.

### Exact D8 pack expectations

The original `test_balatro_d8_booster_policy.py` assertions predated the exact production expectation layers:

- Celestial now enumerates the finite currently eligible Planet pool and draws without replacement when Showman is absent. Early ordinary pool size is nine, so one relevant Planet in a normal three-offer pack has exact hit probability `1/3`, not the retired `1/4` from a synthetic 12-card denominator.
- Celestial literal option EV need not monotonically increase with specialization because specialization also makes off-path Planet upgrades less valuable; directional useful-offer probability is the appropriate monotonic signal.
- Standard now integrates the complete public rank/suit/enhancement/seal/edition generator through D9 literal value. Zero scoped build need is not an automatic veto, and held Death does not fabricate demand.
- Blue Joker/Hologram deck-growth value is already integrated per generated Standard card; the old separate +1 pack override is no longer authoritative.
- Arcana/Spectral exact unopened expectations require observed public generation pools and fail closed on bare synthetic states.

Repairs:

- commit `b86f240` preserves known Buffoon `offer_count/selection_count` metadata even when public Joker valuation fails closed;
- commit `5c7b611` rewrites the old D8 scaffold assertions around the installed exact expectation contracts rather than restoring synthetic family priors.

Validation status: **pending user rerun**.

## Rules for this gate

- Do not interpret cascaded import/collection failures as independent gameplay defects until the earliest package-import blocker is repaired.
- During runtime recursion/fan-out failures, identify the first repeated constructor cycle before treating downstream tests as separate defects.
- Do not restore retired synthetic priors merely to satisfy legacy fixtures; update fixtures when the implemented authority contract changed deliberately.
- Do not run live Red/White baselines while collection/runtime errors remain.
- Do not start Python/Optuna numerical tuning until the unchanged semantic HEAD passes the deterministic suite and a subsequent live baseline contains no obvious semantic contradiction.
