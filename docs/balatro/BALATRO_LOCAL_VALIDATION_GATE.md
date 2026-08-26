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

Validation status: **pending user rerun**.

## Rules for this gate

- Do not interpret cascaded import/collection failures as independent gameplay defects until the earliest package-import blocker is repaired.
- Do not run live Red/White baselines while collection/runtime errors remain.
- Do not start Python/Optuna numerical tuning until the unchanged semantic HEAD passes the deterministic suite and a subsequent live baseline contains no obvious semantic contradiction.
