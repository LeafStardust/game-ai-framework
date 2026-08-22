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

The initial projection layer is an aggregation/pressure model. The authoritative Balatro scoring/search engine should supply candidate score estimates when live integration is added.

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
