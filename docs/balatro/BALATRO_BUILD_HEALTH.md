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

Canonical 46-Bond Strategy Health is installed late in the Balatro policy stack and therefore sits above the existing SHOP child legality/admission layers.

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

## Pivot / replacement authority

Canonical pivot authority runs after existing D2 replacement legality and protection layers. It compares the current realized composition against each eligible projected replacement state using only public-state structure.

The transition score includes:

```text
+ composition coherence delta
+ motif-state improvement
+ reduced motif distance
- lost pivot resistance
- disruption from degrading active/mature motifs
```

Health determines how much net structural improvement is required before a pivot is allowed:

```text
SURVIVE    0.50
REPAIR     1.00
HOLD       2.50
REINFORCE  4.00
EXPLOIT    6.00
```

Therefore weak builds may escape into a clearly better already-legal route, while strong/mature builds require a substantially better transition before abandoning realized structure.

Pivot invariants:

1. Canonical authority may consider only D2 options whose replacement legality is already `eligible`.
2. The candidate transition must remain economically positive (`total_advantage > 0`).
3. Canonical authority cannot bypass Eternal, committed-component, affordability, reserve, or other upstream guards.
4. Existing replacements may be vetoed when realized Bond/motif disruption exceeds the health-adjusted structural gain.
5. A prior `HOLD` may become `REPLACE` only when an upstream-eligible positive option exceeds the canonical structural threshold.

### Critical-survival escape from strategy retention

FORMING and PINNED strategy-retention wrappers install after Build Health/pivot logic, so they previously had enough authority to turn an already-admitted `REPLACE` back into `HOLD` solely to preserve the current plan. That is correct for ordinary churn prevention but wrong when the run is already survival-critical.

Both retention layers now share a narrow existing-health escape:

- the upstream D2 decision must already be a legal `REPLACE`;
- current `RuntimeBuildHealthEvaluator` must report `critical=True` using its existing critical-survival threshold;
- the exact projected replacement roster must strictly improve modeled survival.

When those conditions hold, FORMING/PINNED retention cannot veto the replacement merely because it breaks the current strategy. No new survival threshold or strategy score is introduced. If current Build Health is not critical, or the replacement does not improve survival, normal retention/pivot structure remains authoritative.

This makes the intended hierarchy explicit: an unfinished or pinned Currency-Wars strategy is worth preserving while the run is viable; once the modeled run is already in the critical survival state, a legal survival rescue outranks structural loyalty.

## Motif prescription authority

Active and mature motifs emit concrete prescriptions. `bond_prescription_policy.py` converts only prescriptions with directly observable public semantics into bounded preference value for safe pack choices and already-admitted shop consumables.

Initial mappings are deliberately narrow:

```text
Baron-Mime-Steel
  prefer The Chariot / Steel creation
  prefer Deja Vu / Red Seal creation
  prefer King, Steel and Red-Seal playing cards
  prefer targeting Kings with Steel/Red-Seal transformations

Photograph-Hanging Chad
  prefer face-card playing choices
  prefer Deja Vu, especially on face cards

Vampire-Midas
  prefer face-card feedstock
  recognize enhanced playing cards as Vampire feedstock

Burnt target-hand leveling
  prefer the Planet matching the Bond's selected High Card or Pair target
  prefer Trance / Blue Seal support
  prefer Blue-Seal playing cards

Low-rank Hack retrigger
  prefer ranks 2-5
  prefer Deja Vu, especially on ranks 2-5
```

Prescription invariants:

1. Only `ACTIVE` or `MATURE` motifs emit prescription authority; `POTENTIAL` motifs do not receive the same reinforcement pressure.
2. Unsupported, deferred, unavailable, zero-value, or negative-value pack choices cannot be rescued by a prescription bonus.
3. Shop consumables must first be admitted by D4 and retain positive normalized utility before motif preference is applied.
4. Prescription bonuses are bounded (`2.50` in visible pack ranking and `1.25` on admitted SHOP consumable utility).
5. Burnt targets only High Card or Pair: whichever has stronger public permanent investment and use, with High Card as the exact-tie default. Complex hands never receive first-discard leveling authority.
6. Prescription authority does not alter chip arithmetic, Build Health classification, legality, affordability, or immediate survival authority.
