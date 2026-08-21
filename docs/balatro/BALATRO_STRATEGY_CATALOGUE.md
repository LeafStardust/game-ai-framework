# Balatro Strategy Catalogue

Canonical catalogue of Balatro strategy tracks (the Balatro analogue of Currency Wars Bonds).

This document supersedes `BALATRO_STRATEGY_TREE.md`.

## Status

The catalogue is intentionally **not frozen yet**. The previous strategy-tree nodes are migration input only. We will now decide from first principles which mechanics deserve to exist as independently developable strategy tracks, which are specializations, which are contributors only, and which old nodes should be merged or removed.

A strategy track must represent a coherent mechanic/plan that can accumulate meaningful support from multiple game components and whose increasing development can materially change the run's power plan and/or execution.

The final catalogue will be defined before the Joker/component contribution matrix is rebuilt.

## Architecture

```text
components (especially Jokers)
        ↓ contribute to one or more
strategy tracks
        ↓ develop independently
track ranks
        ↓ compose through compatibility/synergy/conflict
combined build
        ↓
power engine + supporting tracks
        ↓
rank-aware prescriptions
```

There is no requirement that exactly one or exactly three strategy tracks win. RNG determines what can be assembled. A run may max one strong engine and supplement it with several lesser tracks, combine several medium tracks, pivot when new components create a better composition, or fail to assemble sufficient power.

## Catalogue formulation workflow

For every candidate mechanic from the old tree and from Balatro itself, classify it as one of:

- `TRACK` — independently developable strategy/Bond;
- `SPECIALIZATION` — meaningful sub-form of a broader track;
- `CONTRIBUTOR` — component/mechanic that strengthens tracks but is not itself a track;
- `MERGE` — old node whose concept belongs inside another track;
- `REMOVE` — not useful as a strategy concept.

For every accepted track, subsequently define:

1. identity and win/power concept;
2. contribution sources;
3. rank thresholds;
4. rank effects/prescriptions;
5. compatible/synergistic tracks;
6. conflicts;
7. realized-strength conditions;
8. transition/pivot considerations.

## Known architectural examples (not a frozen catalogue)

These examples are retained only because they motivated the redesign:

- Burnt hand-level engine is incompatible with Green and Burglar because it requires a first discard.
- Green and Burglar strongly reinforce a no-discard/extra-hand composition.
- Aces/Scholar can combine with Burnt and a cheap repeatable poker-hand plan; DNA may reinforce several of those tracks simultaneously.
- Ride the Bus/no-face, when sufficiently developed, must influence D1 to avoid playing face cards where survival permits.
- Blueprint/Brainstorm-style copy effects may be contributors rather than independent tracks because their value follows another engine.

Do not infer the final catalogue from these examples. The next design task is the catalogue audit itself.
