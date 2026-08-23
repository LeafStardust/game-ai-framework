# Balatro Canonical Bond Architecture Audit

This audit records the production authority chain after the 46-Bond catalogue, Realization, Composer, Build Health, shop-health, pivot, and prescription layers were integrated.

```text
Bond catalogue / evaluators
→ Realization
→ Composer / motifs / sparse relationships
→ ScoreProjection + BuildHealth
→ D1 post-selection StrategyHealth capture
→ SHOP admitted-option health weighting
→ D2 pivot/replacement authority
→ motif prescription preference
```

## Authority boundaries

1. Bond rank is structural development, never chip output.
2. Realization changes only current functional state, never Bond contribution/rank.
3. Composer coherence is planning evidence, not projected score.
4. D1 survival/search selects the immediate hand action before Strategy Health is derived.
5. SHOP health weighting can amplify only already-positive/admitted utility.
6. Pivot authority may promote/veto only upstream-eligible economically positive replacements.
7. Prescription authority is the final bounded preference layer and cannot rescue unsafe/deferred/negative choices.
8. Offline numerical tuning may alter only approved bounded coefficients/thresholds; it may not redefine any of these authority boundaries.

## Double-count audit

Composer `coherence_score` already includes motif-state bonuses. Pivot transition scoring therefore must not add motif-state delta a second time. Pivot authority may separately use:

- motif-distance improvement;
- pivot-resistance loss;
- explicit disruption cost for degrading active/mature motifs.

The architecture regression suite guards this invariant.

## Production installation audit

Importing `games.balatro` must install all canonical integration hooks:

- D1 Strategy Health capture;
- SHOP health utility weighting;
- reroll health weighting;
- canonical pivot authority;
- pack prescription authority;
- SHOP consumable prescription authority;
- Bond-native D1 execution authorities such as safe Burnt first-discard utilization;
- per-decision Bond-intent caching where required to keep composition evaluation bounded.

`tests/balatro/test_balatro_bond_architecture_integration_audit.py` fails if any required hook becomes dead/uninstalled.

## Offline tuning boundary

The planned Optuna subsystem is documented in [`BALATRO_BOND_TUNING.md`](BALATRO_BOND_TUNING.md). It is deliberately outside the production authority chain above.

```text
production defaults
      ↓
offline immutable calibration snapshot
      ↓
reproducible batch evaluation
      ↓
Optuna trial/study
      ↓
manual + deterministic + holdout promotion gate
      ↓
new reviewed production defaults
```

Required invariants:

- importing/running the live agent must not require Optuna;
- trials may not change semantics during an episode;
- hidden RNG/future draw order remains forbidden;
- illegal/failed/crashed trials fail rather than silently disappearing from the study;
- optimizer output never auto-promotes itself;
- known semantic/execution bugs must be fixed before tuning the affected parameter family;
- default calibration snapshots must reproduce current production behavior exactly.

This boundary prevents automated coefficient search from becoming a second strategy system or learning around broken runtime behavior.
