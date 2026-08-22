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

## Held-family first slice

### Held Cards
ACTIVE when at least one actual held-card payoff is currently functioning, e.g. Baron with a held King, Shoot the Moon with a held Queen, Raised Fist with a held card, Blackboard with an all-black-suit held state, or Steel cards currently held.

### Held Retrigger
Mime alone does not make the Bond ACTIVE. A retriggerable held effect must actually be present in hand.

### Steel
Deck density alone can create high structural rank, but realization is only ACTIVE when Steel is actually held.

### Kings / Queens
Rank density alone is structural. Realization requires the matching rank to be in the current hand and a matching payoff Joker to be present.

### Blackboard distinction
```text
Baron      -> held King payoff
Blackboard -> all remaining held cards are Spades/Clubs
```

## Common hand/deck realization batch

### Pair / High Card / Two Pair / Three of a Kind / Four of a Kind / Straight / Flush
ACTIVE when the corresponding hand shape is actually available in current public hand state (or the runtime exposes the current hand type). MATURE requires R4+ plus consistency evidence.

### Played Retrigger
```text
Hack            -> requires played/scoring 2-5 cards
Sock and Buskin -> requires played/scoring face cards
Hanging Chad    -> requires a scoring card
Dusk            -> requires last-hand timing
Red Seal        -> requires a played/scoring Red-Seal card
```

### Deck Thinning / Deck Growth
Structural size change alone affects rank. ACTIVE requires that changed deck structure to be usable with a current engine/payoff.

## Rank / suit / enhancement realization batch

### Aces / Face Cards / Low Ranks
ACTIVE requires a matching current scoring card plus a relevant payoff Joker. Density alone remains structural.

### Jacks
Hit the Road is discard-driven. Scoring a Jack does not realize the Jacks Bond for Hit the Road; discarding Jacks does.

### No Face Cards
Ride the Bus realization is based on the current scoring play being face-free. A face-depleted deck can raise structural rank, but a scoring face card leaves the Bond PARTIAL for that play.

### Hearts / Spades / Clubs / Diamonds
Suit Bonds realize when current scoring cards match the relevant suit and the build has the corresponding suit payoff. Rotating-payoff mechanics such as Ancient Joker are handled through Flush/composer logic rather than fixed-suit realization.

### Lucky / Glass / Stone
These enhancement Bonds realize from actual current scoring use of the matching enhancement. Persistent deck density can raise rank while a draw with no usable matching cards remains PARTIAL.

### Gold Economy
Gold cards realize when they are actually retained in hand for end-of-round value. Gold density without a currently held Gold card remains structural only.

## Rule for future batches

Every Realizer must:

1. preserve Bond contribution and rank;
2. use actual mechanical state rather than rank as a proxy;
3. return PARTIAL when structure exists but the current trigger cannot function;
4. only return MATURE when both high structural rank and strong active realization are present;
5. avoid encoding score adequacy. Score adequacy belongs to Build Health / score projection.
