# Balatro Bond Realization

Realization is separate from Bond Rank.

```text
Rank        = how much persistent structure has been assembled
Realization = whether that structure is actually functioning in current state
```

Canonical states:

```text
DORMANT = locked/R0, or no currently functioning engine
PARTIAL = developed structure exists but current state does not fully satisfy its mechanic
ACTIVE  = at least one meaningful payoff/engine condition is currently satisfied
MATURE  = an R4+ Bond is actively functioning with strong/stacked realization
```

Realization must never change contribution or rank.

## Coverage status

All 46 frozen Bonds now have exactly one registered Realizer. `games/balatro/bonds/realization.py` is the canonical dispatcher and audit surface.

```text
46 frozen Bond IDs
46 registered Realizers
0 missing
0 extras
```

The dispatcher asserts that rank and contribution are unchanged by Realization.

## Held family

### Held Cards
ACTIVE when at least one actual held-card payoff is functioning: Baron with a held King, Shoot the Moon with a held Queen, Raised Fist with a held card, Blackboard with an all-black-suit held state, or Steel cards currently held.

### Held Retrigger
Mime alone is PARTIAL. ACTIVE requires an actual retriggerable held effect.

### Steel
Deck density is structural; ACTIVE requires Steel currently held.

### Kings / Queens
Density is structural. ACTIVE requires the matching rank in hand plus a matching payoff Joker.

### Blackboard distinction
```text
Baron      -> held King payoff
Blackboard -> all remaining held cards are Spades/Clubs
```

## Common hand/deck family

Pair, High Card, Two Pair, Three of a Kind, Four of a Kind, Straight and Flush are ACTIVE when the corresponding current hand shape is available. MATURE requires R4+ plus consistency evidence.

Played Retrigger is target-specific:

```text
Hack            -> scoring 2-5
Sock and Buskin -> scoring face card
Hanging Chad    -> scoring card
Dusk            -> last-hand timing
Red Seal        -> scoring Red-Seal card
```

Deck Thinning/Growth require actual changed deck structure plus a current engine/payoff for ACTIVE realization.

## Rank / suit / enhancement family

Aces, Face Cards and Low Ranks require matching current scoring cards plus relevant payoff. Jacks is Hit-the-Road/discard driven. No Face Cards requires a currently face-free scoring play.

Suit Bonds require current scoring cards of the relevant suit plus a matching suit payoff. Lucky, Glass and Stone realize from actual current scoring use of that enhancement. Gold Economy realizes from Gold cards currently retained in hand.

## Engine / resource family

### Burnt
ACTIVE when Burnt has a valid target hand and the first-discard opportunity remains available.

### Cash
Cash payoff Jokers such as Bull/Bootstraps require meaningful bankroll; income engines such as Rocket/Cloud 9 can be ACTIVE while generating economy.

### No-Discard / Discard
No-Discard requires its payoff to be live while no discard has been spent in the round. Discard requires both a discard payoff and remaining discard resource.

### Tarot / Planet
ACTIVE when current consumables or persistent generation/access infrastructure can actually produce/use the relevant resource. Blue-Seal Planet realization is based on a currently held Blue Seal rather than deck density alone.

### Blind Skip
Throwback is a persistent live payoff; whether a particular blind should be skipped remains a planner decision.

### Sell Value
Swashbuckler requires actual current Joker sell value to convert into Mult.

### Joker Sacrifice
Ceremonial Dagger requires available fodder; Madness requires a blind-selection opportunity. Historical destruction alone does not realize the Bond.

### Card Destruction
ACTIVE requires a current destruction line/payoff such as Trading Card with a usable hand, Sixth Sense with a 6, Glass Joker with Glass available, or Canio with accumulated destruction payoff.

### Hand Repetition
Card Sharp requires the repeated current hand condition; Supernova remains live for the currently played hand family. Historical repetition raises development but is not by itself realization.

### Enhanced Cards
Driver's License becomes ACTIVE only at its actual enhanced-card threshold. Density below threshold can still develop the Bond without realizing the payoff.

### Vampire
ACTIVE requires current enhancement feedstock or renewable feed infrastructure such as Midas Mask. Historical Vampire scaling alone does not guarantee current feed realization.

## Advanced hands

Full House, Straight Flush, Five of a Kind, Flush House and Flush Five realize only when that advanced hand is actually available/identified. Permanent concentration and hand levels remain structural development when the current hand cannot execute the shape.

## Invariants

Every Realizer must:

1. preserve Bond contribution and rank;
2. use actual mechanical state rather than rank as a proxy;
3. return PARTIAL when structure exists but the current trigger cannot function;
4. only return MATURE when both high structural rank and strong active realization are present;
5. avoid encoding score adequacy. Score adequacy belongs to Build Health / score projection.
