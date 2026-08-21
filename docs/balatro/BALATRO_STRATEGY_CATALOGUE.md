# Balatro Strategy Catalogue

Canonical catalogue of Balatro strategy tracks (Bonds).

## Status

**Architecture is frozen; catalogue membership is not.**

The previous strategy-tree nodes and Gold/Silver/Bronze relationships are migration input only. The next design task is to prune/formulate the actual Bond list under `BALATRO_STRATEGY_SYSTEM.md`.

Do not implement the earlier broad candidate list as final truth until it is reviewed and pruned.

## Admission rule

A Bond is a persistent, developable strategic axis. It should normally have meaningful further investment, multiple contributors/persistent state inputs, increasing payoff, and behavior/build consequences at higher development.

A single defining Joker may establish a Bond if it creates a sufficiently deep strategic axis for other components/state to develop (Burnt is the canonical example).

Do not create Bonds for:

- every Joker;
- every famous build;
- every pair of synergistic Jokers;
- generic value that does not create a developable plan.

Those may instead be contributors, specializations, or composition motifs.

## Classification during catalogue audit

For every old node/candidate classify it as:

- `BOND` — independently developable track;
- `MINOR_BOND` — useful auxiliary track with limited strategic authority if we retain this category;
- `SPECIALIZATION` — meaningful sub-form of another Bond;
- `CONTRIBUTOR` — strengthens one or more Bonds but is not itself a Bond;
- `MOTIF` — known composition of multiple Bonds/components;
- `MERGE` — concept belongs inside another Bond;
- `REMOVE` — not useful as a strategic concept.

## Required definition for every accepted Bond

After membership is frozen, every Bond must receive:

1. identity / strategic purpose;
2. weighted contributors (Jokers and persistent state);
3. Bond-specific R1-R5 thresholds;
4. mandatory gates only where mechanically necessary;
5. Bond-specific effects/prescriptions at each rank under the shared rank framework;
6. realization conditions (`DORMANT/PARTIAL/ACTIVE/MATURE`);
7. explicit sparse `SYNERGY` / `CONFLICT` edges only where meaningful;
8. relevant motif participation;
9. pivot/transition considerations where unusual.

## Important distinction

Bonds are not named builds.

```text
Held Cards       = Bond
Held Retrigger   = Bond
Steel            = Bond

Baron + Mime + Steel Kings
                  = composition motif / strategy
```

Likewise, a component can contribute to several Bonds without becoming a Bond itself. Blueprint/Brainstorm/DNA-like components may be strategically crucial bridge contributors while remaining outside the catalogue.

## Candidate catalogue status

A broad candidate set has been discussed but deliberately remains outside this canonical file until pruning is complete. The working direction includes poker-hand axes, rank/suit axes, enhancement/seal axes, retrigger/held-card axes, defining-Joker engines, deck shaping, economy/resource engines and consumable engines, but each candidate must pass the admission rule.

The immediate next task is catalogue pruning, merging and naming. Only after that should `BALATRO_STRATEGY_CONTRIBUTIONS.md` be populated.
