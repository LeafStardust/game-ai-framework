# Balatro Local Validation — Batch 3

Date: 2026-08-26

This file records the third local deterministic-suite repair batch for Red/White competence. It does **not** claim the full Balatro suite is green; validation remains user-run only.

## Production defects repaired

### Standard Pack deck-growth literal scoring

Observed regression:

```text
test_d8_standard_exact_generator_integrates_deck_growth_value
```

The exact Standard generator already asks `DeckGrowthScoreValueEvaluator` for the literal value of adding a card, but that evaluator depended on concrete Python Joker class identity. Public/fallback Joker records carrying an authoritative `Blue Joker` or `Hologram` name therefore produced no score delta.

Repair: commit `fc9f855` recognizes the public mechanical identity and materializes only those two exact executable mechanics on copied projection states. Blue Joker remains exactly `+2 Chips/card`; Hologram remains exactly `+0.25 XMult/card`. No generic deck-growth bonus was restored.

### Spectral classification metadata

Observed regression:

```text
test_d9_every_current_spectral_is_explicitly_classified
```

Ectoplasm and Ouija had dedicated exact opened-pack expectation paths and were removed from `DEFERRED_SPECTRALS`, but their installers did not add them to `STOCHASTIC_MODELED_SPECTRALS`. `classified_spectrals()` therefore omitted mechanically supported current Spectrals even though runtime scoring supported them.

Repairs:

- `25b84c7` — Ectoplasm remains explicitly classified as modeled;
- `af2b74b` — Ouija remains explicitly classified as modeled.

### Deterministic Tarot intrinsic target value

Observed regressions included context-free Chariot selection paths falling below Skip after the synthetic per-transformation bonus was retired.

The repair keeps that synthetic bonus at zero. Instead, commit `d55f20e` restores the evaluator's already-existing intrinsic before/after card-property delta for deterministic Tarot transformations. This means real modeled changes such as Steel, Glass, or rank improvement can carry their own card value, while merely changing any arbitrary property does not receive free utility. Death remains on its existing directional-copy path; Hanged Man remains on its dedicated thinning path.

### Targeted-pack diagnostics

Commit `54274d5` keeps current `D10/B6` diagnostics while retaining older `B6 pack target`/`no positive B6 target` wording as compatibility notes. This changes no admission value or authority.

### Spectral pool fail-closed rationale

Commit `1af0074` standardizes the missing-public-pool diagnostic wording. Semantics remain fail-closed.

## Regression fixtures aligned with current authority contracts

### FORMING retention projection

Commit `2d62ae0` updates mocked projected states to be mutable and cash-bearing. FORMING/PINNED retention now intentionally projects post-transaction money before Build Health evaluation, so a bare immutable `object()` is no longer a valid state fixture.

### D8 shared resource valuation

Commit `252d6b9` stops requiring an exact single invocation of the shared resource valuator. Layered Celestial expectation may recompute the same transaction cost after replacing the generic family EV. The regression now requires every call to use the same parent valuator and identical D8-owned coefficients; child-specific economics remain forbidden.

### Early-spend Buffoon fixture

Commit `71465a8` removes a rationale assertion that assumed the early cash-floor wrapper must be the first HOLD authority. A bare Buffoon fixture with no observed public Joker pool now legitimately fails closed upstream. The cash-floor predicate itself remains directly tested.

### Verdant Leaf integration fixture

Commit `dcf6010` gives the Verdant sale regression a real future draw horizon. The previous fixture had one debuffed card and an empty draw pile, so selling a Joker could not improve the bounded planner's clear probability and the repaired policy correctly returned no sale. The updated fixture supplies debuffed future Aces such that lifting Verdant changes the modeled blind outcome; the test can therefore exercise the intended survival-authorized lowest-retention-cost sale.

## Validation status

Pending the user's next local run. Do not start live Red/White baselines or numerical tuning until the deterministic Balatro suite is green.
