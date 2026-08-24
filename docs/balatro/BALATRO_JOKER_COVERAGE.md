# Balatro Joker Coverage

Canonical Joker coverage contract for the Bond/strategy system.

## Coverage objective

Balatro's Joker catalogue is finite and its abilities are stable game rules. Production competence should therefore converge toward **complete explicit mechanical knowledge of every Joker**, even when a Joker does not receive Bond quota.

Every strategically relevant Joker must be accounted for as one or more of:

```text
Bond contributor
conditional Bond contributor
motif/composer component
tactical/support component
unique execution mechanic
```

Coverage means the agent knows what the Joker actually does and how its public state affects decisions. Coverage does **not** mean every Joker becomes a Bond or that every Joker pair receives a bespoke strategy rule.

## Modeling rule

Prefer this hierarchy:

```text
1. encode the Joker's real mechanic exactly
2. expose reusable roles/targets/conditions and behavior descriptors
3. let Bonds/strategy composition combine those mechanics
4. encode named motifs/special interactions where generic composition is insufficient
5. regression-test important known synergies and anti-synergies explicitly
```

Examples:

- DNA should explicitly expose first-hand single-card duplication.
- Walkie-Talkie should explicitly expose its 4/10 scoring requirement.
- Green Joker should explicitly expose growth on played hands and loss on discard.
- Card Sharp should explicitly expose same-hand repetition as its activation condition.
- A DNA + Walkie strategy should normally emerge because card copy can feed a required rank, but the combination must still have a regression test.

Correct Balatro behavior takes priority over avoiding Joker-specific code.

## Audited Bond mappings

```text
Square Joker -> Two Pair +3
Erosion      -> Deck Thinning +7
Vampire      -> Vampire Bond
Blackboard   -> Held Cards +4
Superposition-> Straight +2, Tarot +2
Cloud 9      -> Cash +3
8 Ball       -> Tarot +2
Ancient Joker-> Flush +4
```

Notes:

- Ancient Joker is Flush support because Flushes maximize scored cards of its rotating target suit; it does not contribute to any fixed suit Bond.
- 8 Ball is low-authority Tarot generation; it does not establish a Tarot engine alone.
- Cloud 9 is low-authority Cash support; it is an income engine rather than direct cash-scaling payoff.
- Superposition remains low authority in both Straight and Tarot.
- Blackboard is Held Cards support, while mechanical-role metadata distinguishes its all-black-held-state condition from Baron/Shoot-the-Moon/Steel mechanics.

## Motif/composer only

```text
The Idol      dynamic rank+suit payoff for concentrated decks
Hiker         permanent per-card chip growth
Flower Pot    multi-suit scoring condition
Perkeo        consumable duplication; identity depends on held consumable
Baseball Card uncommon-Joker composition payoff
Joker Stencil empty-Joker-slot composition payoff
```

These classifications mean "no Bond quota", not "generic/unknown behavior". Their mechanics still require explicit modeling wherever they affect scoring, scaling, strategy, resource use, or execution.

## Tactical/support only

```text
Seance        niche Straight-Flush Spectral generation
Campfire      sell-to-scale shop engine
Obelisk       brittle hand-rotation scaler
Flash Card    reroll scaler
Red Card      booster-skip scaler
Seltzer       temporary ten-hand played retrigger
Seeing Double broad mixed-suit XMult condition
```

Again, tactical/support-only Jokers must still expose their real activation, growth, reset, consumption, and action-cost semantics to Build Health and the relevant D-policy.

## Remaining Jokers

The remaining Jokers may be handled by normal Joker valuation and tactical logic rather than Bond rank, but they are **not intentionally allowed to remain mechanically opaque**. `games/balatro/bonds/joker_coverage.py` is the classification registry; behavior/mechanic coverage may live in the appropriate scorer, analyzer, realization, execution, or strategy module.

A coverage audit should distinguish:

```text
classified but fully modeled
classified but partially modeled
mechanically unknown/unmodeled
```

The last category is a defect for a strategically relevant production Joker.

## Change rule

New Bond mappings should still require one of:

1. a discovered mechanical omission,
2. a Joker whose persistent engine is not representable by any existing Bond,
3. runtime telemetry showing the current classification is materially wrong.

However, **adding or correcting explicit Joker mechanics does not require adding a Bond**. Mechanical correctness is ordinary maintenance and should be completed whenever a gap is found.
