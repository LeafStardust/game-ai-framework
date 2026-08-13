# D6 consumable targeting autonomy checkpoint

The D6 consumable-targeting autonomy foundation is complete for the currently admitted deterministic playing-card target families.

Cleared contract:

- Target legality is effect-owned: `ContextualConsumableTargetEvaluator` consumes the modeled consumable's real `get_target_cards()` / `can_use()` / `use()` behavior on copied public state rather than duplicating target rules in the executor.
- Supported deterministic Tarot transformations include the current card-transform families, Death directional copy, and Hanged Man destruction when the required public owned-deck composition is available.
- Supported deterministic Spectral target families currently include the exact seal transforms Talisman, Deja Vu, Trance, and Medium.
- Target scoring exposes B6 contextual whole-build delta, intrinsic card/seal delta where applicable, overwrite cost, destruction/thinning value, target indices, and rationale.
- Multi-card target selection is supported for effects whose modeled legality allows more than one selected card.
- First-party held-consumable execution maps the selected cards back to the authoritative live hand and verifies modeled deterministic target postconditions by exact `live_id`, including transformations and destruction.
- Targeted Tarot/Spectral pack choices carry the B6-selected hand targets in the same `SELECT_PACK_CARD` semantic action.
- First-party pack execution verifies the selected target semantics against the authoritative permanent owned-card projection before returning a settled checkpoint.
- Unsupported stochastic, global, generation, or otherwise unmodeled target semantics remain fail-closed; no target is fabricated merely because Balatro exposes a usable pack card.
- No hidden RNG state, seed, ordered future draw information, or mouse fallback is used.
- Focused D6 regressions and the full local test suite were reported green after the Death rationale compatibility regression was repaired.

Scope boundary:

- This closes D6's autonomy foundation, not the entire consumable or pack stack.
- D7 still owns dedicated Planet selection and immediate-use-versus-hold strategy.
- D10 still owns the broader pack-effect targeting layer, including Standard modifier flows, additional stochastic/global/generation Spectrals, dedicated pack-target thresholds, and end-to-end pack-family validation.
- `0.9B` robust held-consumable/pack-effect targeting therefore remains open until the remaining target patterns and live-validation gates are cleared.
- Final decision-layer quality requirements such as playbook-configurable target thresholds, dedicated read-only/armed live validators, and independent run logging remain governed by the shared completion gate.
