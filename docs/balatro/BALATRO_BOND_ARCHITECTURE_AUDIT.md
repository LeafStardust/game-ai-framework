# Balatro Canonical Bond Architecture Audit

This audit records the production authority chain after the Bond catalogue, Realization, Composer, Build Health, shop-health, pivot, prescription, and mechanical strategy layers were integrated.

```text
explicit Balatro/Joker mechanics
→ Bond catalogue / evaluators + behavior descriptors
→ Realization
→ semantic strategy formation
→ Composer / motifs / sparse Bond relationships
→ ScoreProjection + BuildHealth
→ D1/D2-D14 bounded execution authority
```

## Authority boundaries

1. **Balatro rules are closed-world knowledge.** Stable Joker mechanics should be represented explicitly and accurately; the agent is not required to rediscover known game rules through generic inference.
2. Generic roles/descriptors exist to compose known mechanics and control combinatorial complexity, not to hide or replace exact Joker behavior.
3. Important exceptional interactions may be explicit when generic composition cannot represent them faithfully. Important known combinations should have regression coverage regardless of whether their runtime implementation is generic or explicit.
4. Bond rank is structural development, never chip output.
5. Realization changes only current functional state, never Bond contribution/rank.
6. Composer coherence is planning evidence, not projected score.
7. Strategy commitment must reach construction, preservation, and execution; recognizing an engine while D1/D2/D13 contradict it is an architecture defect.
8. SHOP health weighting can amplify only already-positive/admitted utility.
9. Pivot authority may promote/veto only upstream-eligible economically positive replacements.
10. Prescription authority is bounded preference and cannot rescue unsafe/deferred/negative choices.
11. Offline numerical tuning may alter only approved bounded coefficients/thresholds; it may not redefine any of these authority boundaries or compensate for missing mechanics.

## Hardcoding policy

The project does **not** optimize for minimum Joker-specific code. It optimizes for correct Balatro competence with maintainable composition.

Preferred split:

```text
hard-code / explicitly model:
  each Joker's actual mechanic
  activation/reset/consumption rules
  persistent public scaler state
  unique execution constraints
  genuinely exceptional interactions

generalize:
  Bond development
  realization states
  strategy formation
  acquisition/preservation/pivot logic
  resource arbitration
  common producer/requirement/amplifier/copy relationships
```

Avoid exhaustive Joker-pair/triple strategy tables when the same result follows correctly from exact component semantics. Do not preserve a generic abstraction when it produces behavior that contradicts the known game mechanic.

## Double-count audit

Composer `coherence_score` already includes motif-state bonuses. Pivot transition scoring therefore must not add motif-state delta a second time. Pivot authority may separately use:

- motif-distance improvement;
- pivot-resistance loss;
- explicit disruption cost for degrading active/mature motifs.

The architecture regression suite guards this invariant.

## Cross-layer contradiction audit

A semantic engine is not considered correctly implemented merely because it appears in Bond/strategy telemetry. The downstream action layers must honor it when survival/legal constraints permit.

Required examples include:

- ACTIVE No-Discard engines must not casually choose discard actions that directly damage the engine;
- ACTIVE Hand-Repetition/Card-Sharp engines must prefer valid repeated-hand activation when a sufficiently safe line exists;
- a Joker materially supporting an ACTIVE/MATURE Bond or pinned strategy must not receive zero incumbent preservation value during replacement;
- deck-copy/deck-shaping mechanics must understand the concrete rank/suit/enhancement requirements of the strategy they support;
- D13 skip evaluation must receive real build/strategy readiness and opportunity-cost evidence rather than default-zero placeholders.

Live-log contradiction audits are therefore a semantic acceptance test, not merely gameplay commentary.

## Production installation audit

Importing `games.balatro` must install all canonical integration hooks, including:

- D1 Strategy Health capture;
- SHOP health utility weighting;
- reroll health weighting;
- canonical pivot authority;
- pack/consumable prescription authority;
- Bond-native D1 execution authorities;
- strategy execution guards for realized action-sensitive engines;
- strategy-aware blind-skip inputs;
- per-decision Bond-intent caching where required to keep composition evaluation bounded.

`tests/balatro/test_balatro_bond_architecture_integration_audit.py` should fail if a required hook becomes dead/uninstalled.

## Offline tuning boundary

The Optuna subsystem is documented in [`BALATRO_BOND_TUNING.md`](BALATRO_BOND_TUNING.md). It is deliberately outside the production authority chain above.

```text
production defaults
      ↓
immutable calibration snapshot
      ↓
reproducible live batch evaluation
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
