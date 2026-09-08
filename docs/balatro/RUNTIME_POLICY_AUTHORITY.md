# Balatro Runtime Policy Authority

This document defines which policy layers are allowed to own production Red/White decisions after the v1.0.x Bond/composition migration.

## Canonical authority

The production strategic authority is the canonical Bond/composition system documented in `BALATRO_STRATEGY_SYSTEM.md`, together with Build Health, mechanically exact Joker/card/boss rules, legality/survival guards, bounded D1 planning, and the Red/White cartridge.

The runtime must not use historical Gold/Silver/Bronze strategy-tree state, the retired categorical `PlaystyleIntent`/Ante lock, categorical strategy tiers, or batch-specific empirical policy overlays as an independent competing strategy authority.

## Stable mechanics vs empirical overlays

A Joker-specific implementation is valid when it encodes mechanical truth that does not depend on one calibration batch. Examples include DNA first-hand copying, Castle suit state, Hermit payout, Observatory held-Planet scoring, Luchador boss disabling, Blueprint/Brainstorm copy semantics, and boss-specific legal/scoring effects.

A policy is *not* a stable mechanic merely because it mentions a Joker. Batch-derived rules such as static weakness tables, fixed replacement lists, hardcoded build pairs, fixed Ante-specific survival overrides, or reroll/pack thresholds derived from one historical five-run batch are empirical calibration layers. After the Bond migration, those values must be represented by canonical Bond/Build-Health semantics or explicitly tunable calibration parameters rather than monkey-patching D1/D2/shop policy.

## Legacy overlay retirement

The following historical modules have been removed from the production source tree. Their history remains available through version control; they must not return as production strategic authority:

- `five_run_optimization_policy`
- `five_run_followup_policy`
- `five_run_release_candidate_policy`
- `latest_five_run_calibration_policy`
- `latest_zero_five_survival_policy`

Installed policy modules must use stable mechanic/authority names. A module may remain active only when it implements a stable mechanic/legality contract and does not independently rank strategy or override canonical Bond/Build-Health decisions.

## Installation-order rule

Production package registration must follow this hierarchy:

1. exact mechanics/state reconstruction;
2. legality and boss constraints;
3. bounded D1 planning/runtime safety;
4. canonical Bond/composition and Build Health;
5. mechanic-specific execution adapters required to realize the canonical strategy;
6. final authoritative capacity/order guards.

No historical batch-derived strategy wrapper may sit above steps 3-5 and silently replace their decisions.

## Decision-boundary invariants

- D1 owns the final hand action. A materially superior completed adaptive-search root must not be replaced by contradictory one-step pace advice; after the deadline, recovery must remain structural, bounded, and preserve made Pair-or-better shapes when possible.
- D2 and the shop arbiter recruit components for a mechanically realizable combined build. Raw stock-deck rank/suit counts, an inactive copy/retrigger Joker, or an isolated future scaler do not by themselves constitute an engine.
- Multi-action shop sequences execute one mutation at a time and require authoritative re-observation between steps. This includes complementary Joker bundles and Campfire's buy-then-sell fuel transaction.
- Joker ordering is evaluated for the exact selected hand when order is material. Live center-key aliases must normalize before scoring, and an already-correct order must not generate another reorder action.
- Child policies may expose Planet-scaler or Bond value, but they may not promote an option that the authoritative target/compatibility layer rejected.

## Validation requirement

Any removal or migration of a legacy overlay invalidates the current live-study SHA. The full `tests/balatro` suite must pass before a fresh Red/White authoritative baseline. Regression tests should cover the specific old behavior being retired so the canonical replacement is proven rather than assumed.
