# Balatro Score Projection and Build Health

Score projection and Build Health are separate from Bond development, realization, motifs, and composer coherence.

```text
Bond rank        = what persistent strategy structure exists
Realization      = whether that structure is currently functioning
Composition      = whether selected Bonds/motifs form a coherent plan
Score projection = whether actual/runtime score estimates clear the blind
Build Health     = whether the current build is safe, stable, and scaling adequately
```

## Score projection

`ScoreProjection` consumes actual/runtime hand-score estimates. It must never convert Bond ranks, realization values, motif states, or composer coherence into chips.

For candidate hand-score estimates it exposes:

```text
conservative hand score
expected hand score
ceiling hand score

conservative total / margin
expected total / margin
ceiling total / margin
expected clear ratio
expected hands to clear
optional externally supplied clear probability
```

The live bridge consumes the runtime's existing scoring evidence rather than inventing a second scorer:

```text
LivePlayProjection.minimum/expected/maximum
        -> ScoreProjection conservative/expected/ceiling

LiveBlindPlanValue.clear_probability + expected terminal score
        -> search-level ScoreProjection
```

`LiveBlindPlanValue.expected_score` is an expected terminal round score, not a guaranteed hand score. The search adapter therefore never treats it as a conservative floor.

The generic projector also understands the live state shape directly:

```text
state.score
state.blind.requirement
state.hands_remaining
```

## Build Health

Canonical states:

```text
COLLAPSING
FRAGILE
STABLE
STRONG
DOMINANT
```

Classification is dominated by actual score adequacy. Structural signals may affect stability/confidence but cannot manufacture scoring power.

Inputs include:

- `ScoreProjection` clear margin/ratio/probability;
- realization ratio of selected Bonds;
- active/mature motifs;
- composer coherence as a planning signal only;
- economy runway;
- remaining scaling runway.

Important invariants:

1. If even the ceiling projection cannot clear, a high-rank/high-coherence build remains `COLLAPSING`.
2. A mature motif may stabilize an already-clearing build; it cannot rescue a projection that does not clear.
3. Low realization may downgrade confidence in a theoretically strong composition.
4. Bond rank and composer coherence never enter chip arithmetic.
5. Build Health is advisory planning state; survival/score search remains final authority for immediate actions.

## Live strategy authority

The frozen catalogue now has one unified live evaluator:

```text
live state
  -> evaluate all 46 Bond developments
  -> realize all 46 Bonds
  -> compose compatible Bonds/motifs
  -> selected D1 LiveBlindPlan score evidence
  -> ScoreProjection
  -> Build Health
  -> strategy-health mode
```

Strategy-health modes are deliberately downstream of D1 survival selection:

```text
COLLAPSING -> SURVIVE   authority 0.00
FRAGILE    -> REPAIR    authority 0.20
STABLE     -> HOLD      authority 0.50
STRONG     -> REINFORCE authority 0.75
DOMINANT   -> EXPLOIT   authority 1.00
```

`PathAwareLiveHandActionDecisionEngine` evaluates this after its final action, including consensus-recovery replacement, has already been selected. The result is exposed as `last_strategy_health`. This ordering is mandatory: Build Health may govern reinforcement, shop/pivot pressure, prescriptions and telemetry, but it must not replace a safer immediate D1 action with a strategically attractive losing action.
