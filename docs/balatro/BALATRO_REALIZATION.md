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

## Opportunity versus exact trigger frame

`ACTIVE` does **not** mean an effect must be firing on this exact observation frame. Realization answers whether the engine/payoff is currently usable or mechanically available from public state. When authoritative action-window telemetry exists, the Realizer may enforce the exact trigger condition; when only ordinary run/hand state is available, it must not incorrectly mark a valid engine PARTIAL merely because no play/discard/round-end event is in progress.

Examples:

- Trading Card can be ACTIVE before the first discard is selected when its first-discard opportunity remains.
- Sixth Sense can be ACTIVE when the first-hand opportunity remains and a usable 6 is available, even before cards are selected.
- Certificate/Marble/DNA can be ACTIVE as currently available deck-growth engines before their first generated card.
- held Gold Cards and Reserved Parking face-card infrastructure can be ACTIVE as available economy payoffs before the end-of-round/scoring trigger actually resolves.
- if explicit `cards_to_play`, `cards_to_discard`, scoring, blind-selection, or round-end telemetry is supplied, trigger-specific checks remain strict.

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

Deck Thinning/Growth are ACTIVE when a present engine has a currently available legal growth/thinning opportunity, or when changed deck structure is already feeding a surviving payoff. Hologram without any actual growth remains PARTIAL.

## Rank / suit / enhancement family

Aces, Face Cards and Low Ranks require matching current scoring cards plus relevant payoff. The Low Ranks Bond remains deliberately scoped to ranks 2-5; Fibonacci Ace/8 and Even Steven/Walkie-Talkie higher-rank effects belong to their other relevant Bonds rather than widening this one. Jacks is Hit-the-Road/discard driven. No Face Cards requires a currently face-free scoring play.

Suit Bonds require current scoring cards of the relevant suit plus a matching suit payoff. Lucky, Glass and Stone realize from actual current scoring use of that enhancement. Gold Economy realizes from currently retained Gold-card/held-economy opportunity; Golden Ticket and Midas still require their relevant played-card condition.

## Engine / resource family

### Burnt
ACTIVE when Burnt has a selected High Card or Pair target and the first-discard opportunity remains available. More complex poker hands are never selected as Burnt targets because they are not reliable first-discard material.

### Cash
Cash payoff Jokers such as Bull/Bootstraps require meaningful bankroll outside an exact scoring frame; income engines such as Rocket/Cloud 9 can be ACTIVE while their economy engine remains available. Exact scoring/round-end telemetry may narrow realization to the current trigger window.

### No-Discard / Discard
No-Discard requires a functioning no-discard payoff/opportunity; Delayed Gratification still requires no discard to have been spent. Green Joker and Ramen remain mechanically live while scoring even after a discard, although the no-discard plan has been weakened. Discard requires both a discard payoff and remaining discard resource; exact discarded-card telemetry narrows target-specific effects such as Castle, Mail-In Rebate, Faceless Joker and Hit the Road.

### Tarot / Planet
ACTIVE when current consumables or persistent generation/access infrastructure can actually produce/use the relevant resource. Blue-Seal Planet realization is based on a currently held Blue Seal rather than deck density alone.

### Blind Skip
Throwback is a persistent live payoff; whether a particular blind should be skipped remains a planner decision.

### Sell Value
Swashbuckler requires actual current Joker sell value to convert into Mult.

### Joker Sacrifice
Ceremonial Dagger requires available fodder and the relevant blind-selection opportunity; Madness requires a non-boss blind-selection opportunity. Historical destruction alone does not realize the Bond.

### Card Destruction
ACTIVE requires a current destruction line/payoff such as Trading Card with first-discard access, Sixth Sense with first-hand access, Glass Joker with Glass available, or Canio with accumulated face-card destruction payoff. Exact selected-card telemetry, when present, is authoritative.

### Hand Repetition
Card Sharp requires the current poker-hand type to have been played earlier in the round; it does not require the immediately previous hand to match. Supernova remains live for the currently played hand family. Run-level repetition history raises development but does not substitute for the current-round condition.

### Enhanced Cards
Driver's License becomes ACTIVE only at its actual enhanced-card threshold. Density below threshold can still develop the Bond without realizing the payoff.

### Vampire
ACTIVE requires current enhancement feedstock or renewable feed infrastructure such as Midas Mask. Renewable Midas feed may be recognized from public hand/deck face availability before the exact scoring frame. Historical Vampire scaling alone does not guarantee current feed realization.

## Advanced hands

Full House, Straight Flush, Five of a Kind, Flush House and Flush Five realize only when that advanced hand is actually available/identified. Permanent concentration and hand levels remain structural development when the current hand cannot execute the shape.

## Invariants

Every Realizer must:

1. preserve Bond contribution and rank;
2. use actual mechanical state rather than rank as a proxy;
3. distinguish a currently available engine/opportunity from a merely historical or theoretical one;
4. use exact trigger-window telemetry when it is available without requiring such telemetry when ordinary public state already proves the engine is usable;
5. only return MATURE when both high structural rank and strong active realization are present;
6. avoid encoding score adequacy. Score adequacy belongs to Build Health / score projection.
