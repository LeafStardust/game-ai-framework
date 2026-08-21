# Balatro Strategy Contributions

Canonical home for component/state -> Bond contribution values.

## Status

**Contract frozen. Burnt and Held Cards are formulated; all other Bond values remain undefined.**

Do not copy or mechanically translate the old Gold/Silver/Bronze table. It is migration evidence only.

## Contribution model

Every relevant source receives its own Bond-specific numerical value:

```text
Source
  Bond A -> +x
  Bond B -> +y
  Bond C -> +z
```

There are no categorical Gold/Silver/Bronze replacements. Different contributors to the same Bond may have materially different weights. The same source may contribute different weights to several Bonds.

Contribution measures structural development, not direct score power and not global strategy commitment.

## Allowed sources

Persistent/public run state may contribute, including owned/locked Jokers, rank/suit density, enhancements/seals, permanent card upgrades, hand levels, deck size/concentration, persistent scaler state, consumable/economy infrastructure and other mechanically relevant persistent state.

Current-hand coincidences are tactical evidence, not persistent Bond development. Permanent additions remain contribution while present in game state; sold/destroyed dynamic sources disappear. No artificial history/decay variable is used.

## Density/state weighting

Do not blindly award unbounded quota per card. Bonds may define bands, caps or nonlinear density contribution where mechanically appropriate.

## Rank conversion

Each Bond converts one shared weighted contribution pool into approximately five development ranks. Thresholds are Bond-specific. Contributors are **alternative/additive progression paths**, not sequential rank keys.

Some Bonds have a hard unlock prerequisite and can be `LOCKED`; naturally emerging Bonds use `R0` below their first threshold.

Functional execution belongs to Realization, not rank gating.

---

# Formulated contributions

## Burnt Bond — provisional Red/White calibration

**Hard unlock prerequisite:** Burnt Joker owned. Without Burnt Joker, Burnt is `LOCKED` regardless of other infrastructure.

Once unlocked, every source below adds to the same pool:

| Source | Contribution | Notes |
|---|---:|---|
| Burnt Joker | +8 | Defining source; also establishes/unlocks the Bond. |
| Blueprint | +5 | Conditional on Burnt Bond existing; can copy Burnt's first-discard level-up and later be repositioned. |
| Brainstorm | +5 | Conditional on Burnt Bond existing; same copy-engine rationale. |
| Telescope | +4 | Celestial Packs reliably offer the most-played hand's Planet, strongly reinforcing Burnt's chosen specialization. |
| Space Joker | +2 | Additional repeatable permanent hand-level source, but stochastic and weaker than direct Burnt copying. |
| Blue Seal infrastructure: 1 card | +1 | Useful controlled hand-level support. |
| Blue Seal infrastructure: 2 cards | +3 | Density band. |
| Blue Seal infrastructure: 3 cards | +5 | Strong density band. |
| Blue Seal infrastructure: 4+ cards | +6 cap | Capped to avoid unbounded per-card inflation. |
| Target hand level 2-3 | +1 | Persistent specialization already present in the selected Burnt target. |
| Target hand level 4-6 | +3 | Density/development band. |
| Target hand level 7-10 | +5 | Strong specialization. |
| Target hand level 11+ | +7 cap | Deep permanent specialization; capped. |
| Extra discard capacity above ordinary 3 | +1 each, max +3 | Reliability/cost support, intentionally weaker than direct scaling sources. |

**Excluded from Burnt contribution:** Astronomer, generic Planets, Scholar/Aces infrastructure, generic poker-hand Jokers and generic scoring. They may still be ordinary value, contributors to other Bonds, or composition-level synergy.

### Burnt thresholds

```text
R1 >= 8
R2 >= 12
R3 >= 17
R4 >= 23
R5 >= 30
```

These values deliberately permit different RNG paths to reach the same rank. Examples:

```text
Burnt alone                              -> 8  -> R1
Burnt + Telescope                        -> 12 -> R2
Burnt + 3 Blue Seals                     -> 13 -> R2
Burnt + Blueprint                        -> 13 -> R2
Burnt + Blueprint + Telescope            -> 17 -> R3
```

No example above is a required recipe. It merely demonstrates alternative ways of crossing the same numerical thresholds.

---

## Held Cards Bond — provisional Red/White calibration

**Hard unlock prerequisite:** none. Held Cards is naturally available as a strategic axis and remains `R0` until contribution reaches 4.

Every source below feeds the same pool:

| Source | Contribution | Notes |
|---|---:|---|
| Baron | +6 | Strongest direct held-card payoff currently admitted; holding Kings directly creates XMult. |
| Shoot the Moon | +4 | Direct held-Queen payoff and independent R1 route. |
| Raised Fist | +2 | Direct held-card payoff, but only one lowest held card is relevant each hand. |
| Mime | +2 | Deliberately modest bridge contribution; primary identity belongs to Held Retrigger. |
| Steel cards: 1 | +1 | Genuine held payoff infrastructure. |
| Steel cards: 2-3 | +3 | Density band. |
| Steel cards: 4-5 | +5 | Strong density band. |
| Steel cards: 6+ | +7 cap | Deep held-card infrastructure; Steel remains its own Bond too. |
| Gold cards: 1-2 | +0.5 | Held end-of-round economy; weaker than scoring held effects. |
| Gold cards: 3-4 | +1.5 | Density band. |
| Gold cards: 5+ | +2.5 cap | Capped auxiliary held infrastructure. |
| Blue Seals: 1-2 | +0.5 | Held-to-end-of-round value, but primary purpose is not Held Cards. |
| Blue Seals: 3-4 | +1.5 | Density band. |
| Blue Seals: 5+ | +2 cap | Capped cross-Bond support. |
| Hand size above ordinary 8 | +1 per card, max +3 | More capacity to retain payoff cards; support, not a defining engine. |

### Held Cards thresholds

```text
R1 >= 4
R2 >= 8
R3 >= 13
R4 >= 19
R5 >= 26
```

Alternative-path examples:

```text
Baron alone                              -> 6  -> R1
Shoot the Moon alone                     -> 4  -> R1
4 Steel cards                            -> 5  -> R1
Mime alone                               -> 2  -> R0
Baron + Mime                             -> 8  -> R2
```

Again, none of these is a recipe or sequential requirement.

### Boundary decisions

- Mime gets only modest Held Cards credit because its main Bond is Held Retrigger.
- Steel density legitimately contributes to Held Cards and Steel simultaneously; this is intended multi-Bond slot/state efficiency, not additive score power.
- Blue Seal and Gold-card contribution is deliberately small because holding them matters, but their primary strategic purposes sit elsewhere.
- Generic hand size does not create Held Cards by itself: even extreme extra hand size is capped below R1 without another held-value source.

## Multi-Bond contributors

Overlapping contribution is intentional. A component advancing several relevant Bonds is slot-efficient and should gain contextual acquisition value from useful Bond progress, threshold crossings, motif progress/activation, synergy among advanced Bonds and one-slot efficiency.

Do not sum overlapping Bond contribution into fake scoring power. Actual Balatro scoring/economy remains independently projected.

## Relationships

Bond-to-Bond relationships are sparse:

```text
default = NEUTRAL
explicit = SYNERGY or CONFLICT
```

Do not create an exhaustive pair matrix. Complex super-additive packages belong to composition motifs.

## Calibration

Initial weights/thresholds are mechanically reasoned. Subsequent tuning should use unchanged-HEAD multi-run telemetry. Do not inflate contribution merely to force a desired rank outcome.
