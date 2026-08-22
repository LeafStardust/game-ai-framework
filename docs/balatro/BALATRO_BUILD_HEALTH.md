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

The live bridge consumes the public scoring/search evidence already produced by the Balatro runtime. Bond rank and composer coherence remain absent from chip arithmetic.

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

## Live strategy-health authority

The exact D1-selected blind plan is converted into canonical strategy posture only after D1 has finished survival selection:

```text
COLLAPSING -> SURVIVE    authority 0.00
FRAGILE    -> REPAIR     authority 0.20
STABLE     -> HOLD       authority 0.50
STRONG     -> REINFORCE  authority 0.75
DOMINANT   -> EXPLOIT    authority 1.00
```

The production base `LiveHandActionDecisionEngine` records this result after its final decision. This is intentionally downstream of D1; strategy health cannot replace a safer hand action.

## SHOP integration

Canonical 46-Bond Strategy Health is installed last in the Balatro policy stack and therefore sits above the existing SHOP child legality/admission layers.

Weak health may increase urgency only for options that those child policies have already admitted:

```text
SURVIVE:
  positive Joker utility      x1.25
  replacement Joker utility   x1.125
  positive consumable utility x1.15
  admitted reroll margin      x1.35

REPAIR:
  positive Joker utility      x1.15
  replacement Joker utility   x1.075
  positive consumable utility x1.08
  admitted reroll margin      x1.20

HOLD / REINFORCE / EXPLOIT:
  no canonical health multiplier
```

The SHOP bridge obeys these invariants:

1. Negative or zero utility is never turned positive by Strategy Health.
2. A purchase rejected by D2/D4/D8 remains rejected.
3. A reroll rejected by D11 remains rejected; only an already-admitted positive reroll margin may be amplified.
4. Affordability, reserve, slot, Eternal, replacement, and transaction guards remain authoritative.
5. Strong/dominant health does not manufacture extra spending. Existing strategy tiers, motifs, and item valuation remain the reinforcement authority, avoiding double-counting.
