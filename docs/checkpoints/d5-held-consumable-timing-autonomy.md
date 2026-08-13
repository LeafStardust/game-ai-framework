# D5 held-consumable timing autonomy checkpoint

The D5 autonomous held-consumable timing foundation is complete for the currently admitted first-party paths.

Cleared contract:

- Held consumables produce explicit `USE_CONSUMABLE` or `HOLD` recommendations independently of D4 acquisition mode.
- Blind-phase timing uses current public state, blind urgency, consumable-slot pressure, deterministic effect simulation, analytic Wheel expectation, and B6 contextual target/build value where the effect is targetable.
- The autonomous `SELECTING_HAND` path checks D5/B6 timing before D1 hand action and falls through to D1 on HOLD.
- SHOP timing is deliberately fail-closed and admits only validated no-hand-target held effects: The Hermit, Temperance, and The Wheel of Fortune.
- SHOP HOLD falls through to the existing shop arbiter; a validated USE recommendation preempts shop purchasing/reroll/exit for exactly one action, followed by fresh authoritative observation.
- The first-party injected dispatcher and Lua bridge execute these SHOP-safe no-target uses and verify disappearance of the exact held consumable from a fresh complete snapshot in the same phase.
- Targeted held use remains restricted to `SELECTING_HAND`; SHOP targeting is not inferred or widened by this checkpoint.
- No hidden RNG state, seed, ordered future draw information, or mouse fallback is used.
- Focused D5/B6 regressions and the full local test suite were reported green before this checkpoint was recorded.

Scope boundary:

- This closes D5's autonomy foundation, not the entire consumable stack.
- D6 still owns complete target-family policy, multi-card target choice, target verification, and Tarot/Spectral pack follow-up targeting.
- D7 still owns dedicated Planet selection and immediate-use-versus-hold policy, including positive modeled hold cases.
- `0.9B` robust held-consumable use for all supported target patterns therefore remains open until D6/D7 coverage is complete.
- Final decision-layer quality requirements such as playbook-configurable thresholds, dedicated live validators, and independent run logging remain governed by the shared decision-layer completion gate.
