# Balatro Joker Coverage

Canonical post-freeze Joker coverage audit for the Bond system.

Purpose: every strategically relevant Joker must be accounted for as one of:

```text
Bond contributor
conditional Bond contributor
motif/composer component
tactical/support component
```

Coverage does **not** mean every Joker receives Bond quota.

## Final post-freeze Bond mappings

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
- Blackboard is Held Cards support, but mechanical-role metadata must later distinguish its all-black-held-state condition from Baron/Shoot-the-Moon/Steel mechanics.

## Motif/composer only

```text
The Idol      dynamic rank+suit payoff for concentrated decks
Hiker         permanent per-card chip growth
Flower Pot    multi-suit scoring condition
Perkeo        consumable duplication; identity depends on held consumable
Baseball Card uncommon-Joker composition payoff
Joker Stencil empty-Joker-slot composition payoff
```

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

## Generic / temporary / boss / slot-value pieces

The remaining unwired Jokers are intentionally handled by normal Joker valuation and tactical logic rather than Bond rank. See `games/balatro/bonds/joker_coverage.py` for the explicit registry.

## Freeze rule

After this audit, new Bond mappings should require one of:

1. a discovered mechanical omission,
2. a Joker whose persistent engine is not representable by any existing Bond,
3. runtime telemetry showing the current classification is materially wrong.

Next architecture work is contributor mechanical roles, then Bond realization.
