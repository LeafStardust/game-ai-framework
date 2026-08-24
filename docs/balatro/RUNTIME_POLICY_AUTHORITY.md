# Balatro Runtime Policy Authority

This document defines which policy layers are allowed to own production Red/White decisions after the v1.0.x Bond/composition migration.

## Canonical authority

The production strategic authority is the canonical Bond/composition system documented in `BALATRO_STRATEGY_SYSTEM.md`, together with Build Health, mechanically exact Joker/card/boss rules, legality/survival guards, bounded D1 planning, and the Red/White cartridge.

The runtime must not use historical Gold/Silver/Bronze strategy-tree state, categorical strategy tiers, or batch-specific empirical policy overlays as an independent competing strategy authority.

## Stable mechanics vs empirical overlays

A Joker-specific implementation is valid when it encodes mechanical truth that does not depend on one calibration batch. Examples include DNA first-hand copying, Castle suit state, Hermit payout, Observatory held-Planet scoring, Luchador boss disabling, Blueprint/Brainstorm copy semantics, and boss-specific legal/scoring effects.

A policy is *not* a stable mechanic merely because it mentions a Joker. Batch-derived rules such as static weakness tables, fixed replacement lists, hardcoded build pairs, fixed Ante-specific survival overrides, or reroll/pack thresholds derived from one historical five-run batch are empirical calibration layers. After the Bond migration, those values must be represented by canonical Bond/Build-Health semantics or explicitly tunable calibration parameters rather than monkey-patching D1/D2/shop policy.

## Legacy overlay retirement

The following historical modules may remain in the repository as forensic/release evidence, but must not be installed as production strategic authority unless their stable mechanic portions are first migrated into canonical mechanic modules:

- `five_run_optimization_policy`
- `five_run_followup_policy`
- `five_run_release_candidate_policy`
- `latest_five_run_calibration_policy`
- `latest_zero_five_survival_policy`

Other historically named modules must be reviewed case-by-case. A module may remain active only when it implements a stable mechanic/legality contract and does not independently rank strategy or override canonical Bond/Build-Health decisions.

## Installation-order rule

Production package registration must follow this hierarchy:

1. exact mechanics/state reconstruction;
2. legality and boss constraints;
3. bounded D1 planning/runtime safety;
4. canonical Bond/composition and Build Health;
5. mechanic-specific execution adapters required to realize the canonical strategy;
6. final authoritative capacity/order guards.

No historical batch-derived strategy wrapper may sit above steps 3-5 and silently replace their decisions.

## Validation requirement

Any removal or migration of a legacy overlay invalidates the current live-study SHA. The full `tests/balatro` suite must pass before a fresh Red/White authoritative baseline. Regression tests should cover the specific old behavior being retired so the canonical replacement is proven rather than assumed.
