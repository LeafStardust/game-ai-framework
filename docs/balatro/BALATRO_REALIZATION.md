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

MATURE requires R4+ development plus multiple/strong simultaneous held-payoff conditions.

### Held Retrigger

Mime alone does not make the Bond ACTIVE. A retriggerable held effect must actually be present in hand. Steel/Gold cards, relevant seals, or held-effect Jokers supply the retrigger target.

### Steel

Deck density alone can create high structural rank, but realization is only ACTIVE when Steel is actually held. Multiple held Steel cards, especially with Mime, can make an R4+ Steel Bond MATURE.

### Kings / Queens

Rank density alone is structural. Realization requires the matching rank to be in the current hand and a payoff Joker such as Baron/Triboulet or Shoot the Moon/Triboulet to be present.

### Blackboard distinction

Blackboard shares the Held Cards Bond but has a different realization condition from Baron:

```text
Baron      -> held King payoff
Blackboard -> all remaining held cards are Spades/Clubs
```

This is why contributor mechanical roles exist. Bond membership defines strategic axis; role/condition defines actual execution.

## Rule for future batches

Every Realizer must:

1. preserve Bond contribution and rank;
2. use actual mechanical state rather than rank as a proxy;
3. return PARTIAL when structure exists but the current trigger cannot function;
4. only return MATURE when both high structural rank and strong active realization are present;
5. avoid encoding score adequacy. Score adequacy belongs to Build Health / score projection.
