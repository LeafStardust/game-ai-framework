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

Validation status: **pending user rerun**.

## Rules for this gate

- Do not interpret cascaded import/collection failures as independent gameplay defects until the earliest package-import blocker is repaired.
- During runtime recursion/fan-out failures, identify the first repeated constructor cycle before treating downstream tests as separate defects.
- Do not run live Red/White baselines while collection/runtime errors remain.
- Do not start Python/Optuna numerical tuning until the unchanged semantic HEAD passes the deterministic suite and a subsequent live baseline contains no obvious semantic contradiction.
