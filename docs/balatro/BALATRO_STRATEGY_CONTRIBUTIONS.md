# Balatro Strategy Contributions

Canonical home for the component/state -> Bond contribution matrix once the Bond catalogue is frozen.

## Status

**Contract frozen; values not yet formulated.**

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

Persistent/public run state may contribute, including:

- owned Jokers;
- Eternal/otherwise locked Jokers while present;
- rank/suit density;
- enhancements and seals;
- permanent card upgrades;
- hand levels;
- deck size/concentration;
- accumulated persistent Joker scaler state where appropriate;
- persistent consumable/economy infrastructure;
- other mechanically relevant persistent state.

Current-hand coincidences are tactical evidence, not persistent Bond development.

Permanent additions remain contribution while they persist in actual game state. Dynamic owned sources disappear when sold/destroyed. No historical commitment/decay variable is required.

## Density/state weighting

Do not blindly award unbounded quota per card. Bonds may define bands, caps, nonlinear density contribution or conditional contribution where mechanically appropriate.

Example shape only:

```text
useful density  -> +a
strong density  -> +b
extreme density -> +c
```

Exact values are defined per Bond after catalogue freeze.

## Rank conversion

Each Bond converts its weighted contribution into approximately five development ranks. Thresholds are Bond-specific. Mechanically necessary gates may supplement a threshold; gates should be sparse.

Rank is not realization. A Bond can be structurally R4 while only PARTIAL in actual execution.

## Multi-Bond contributors

Overlapping contribution is intentional. A component advancing several relevant Bonds is slot-efficient and should gain contextual acquisition value from:

- relevant Bond progress;
- useful threshold crossings;
- motif progress/activation;
- synergy among advanced Bonds;
- one-slot efficiency.

Do not sum overlapping Bond contribution into fake scoring power. Actual Balatro scoring/economy remains independently projected.

## Relationships

Bond-to-Bond relationships are sparse:

```text
default = NEUTRAL
explicit = SYNERGY or CONFLICT
```

Do not create an exhaustive pair matrix. Complex super-additive packages belong to composition motifs.

## Calibration

Initial weights/thresholds should be mechanically reasoned from the frozen catalogue and Balatro effects. Subsequent tuning should use unchanged-HEAD multi-run telemetry. Do not inflate contribution merely to force a desired rank/commitment outcome.
