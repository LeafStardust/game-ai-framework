# Balatro Strategy Catalogue — Poker Hands

> Concrete universal poker-hand strategy definitions.
>
> The grouping is documentation-only. At runtime every strategy is a peer in the same universal strategy pool. See [`BALATRO_STRATEGY_PLAYBOOKS.md`](BALATRO_STRATEGY_PLAYBOOKS.md) for architecture, tier semantics, Ante progression, and implementation rules.

## Catalogue rule

The Joker tier columns are **explicit implementation data**.

- Every entry is a specific Joker name.
- **Unlisted Joker = Neutral** for that strategy. Neutral is not Bronze and is not banned.
- Bronze is reserved for named Jokers with a real but weaker relationship to the strategy.
- `Banned / conflict Jokers` are explicit Jokers that should normally not be purchased once the strategy is dominant unless the agent is intentionally pivoting or a survival override applies.
- Generic survival/economy value remains outside the strategy catalogue and is handled by the ordinary acquisition evaluator.
- Parenthetical conditions are part of the future rule: e.g. `Baron (King density)` is not equivalent to unconditional Baron evidence.

A Planet is **support for an evidenced poker-hand strategy**, not sufficient strategy evidence by itself. Joker ownership, Tarot/Spectral effects, deck shape, hand-level investment, and actual repeated hand use should establish the direction first.

| Strategy | Planet | Gold Jokers | Silver Jokers | Bronze Jokers | Banned / conflict Jokers | Key Tarot / Spectral support | Entry evidence |
|---|---|---|---|---|---|---|---|
| **High Card** | Pluto | Stuntman; Mime; Baron (King/held-card shell); Burnt Joker | Half Joker; Supernova; Card Sharp; Space Joker; Green Joker; Blackboard; Shoot the Moon; Raised Fist; Troubadour; Juggler | Banner; Delayed Gratification; Burglar; Reserved Parking; Ramen | Jolly Joker; Sly Joker; Mad Joker; Clever Joker; Zany Joker; Wily Joker; Crazy Joker; Devious Joker; Droll Joker; Crafty Joker; Runner; Spare Trousers; The Duo; The Trio; The Family; The Order; The Tribe | The Chariot; Death; The Hanged Man | Repeated High Card use; Stuntman/Mime/Baron/Burnt evidence; held-card value or minimal-hand construction materially benefits the run |
| **Pair** | Mercury | The Duo; Half Joker | Jolly Joker; Sly Joker; Supernova; Card Sharp; Space Joker; Burnt Joker; DNA; Green Joker | Blackboard; Raised Fist; Shoot the Moon | Mad Joker; Clever Joker; Spare Trousers; The Trio; Zany Joker; Wily Joker; The Family; The Order; Runner; Crazy Joker; Devious Joker; The Tribe; Droll Joker; Crafty Joker | Death; Strength; Cryptid; Ouija | Reliable duplicated ranks; repeated Pair use; The Duo/Half/Jolly/Sly evidence |
| **Two Pair** | Uranus | Spare Trousers; Square Joker; The Duo | Mad Joker; Clever Joker; Jolly Joker; Sly Joker; Supernova; Card Sharp; Burnt Joker; Space Joker | DNA; Trading Card | Half Joker; The Trio; Zany Joker; Wily Joker; The Family; The Order; Runner; Crazy Joker; Devious Joker; The Tribe; Droll Joker; Crafty Joker | Death; Strength; Cryptid | Multiple duplicated ranks; repeated Two Pair use; Spare Trousers/Square/Mad/Clever evidence |
| **Three of a Kind** | Venus | The Trio; The Duo; DNA; Half Joker | Zany Joker; Wily Joker; Jolly Joker; Sly Joker; Supernova; Card Sharp; Burnt Joker; Space Joker | Trading Card; Scholar (Ace target); Wee Joker (2 target) | Square Joker; Spare Trousers; Mad Joker; Clever Joker; The Family; The Order; Runner; Crazy Joker; Devious Joker; The Tribe; Droll Joker; Crafty Joker | Death; Strength; Cryptid; Ouija | One rank is meaningfully concentrated; repeated Three of a Kind use; The Trio/DNA evidence |
| **Straight** | Saturn | Shortcut; Four Fingers; Runner; The Order | Crazy Joker; Devious Joker; Superposition; Supernova; Card Sharp; Space Joker; Burnt Joker | Fibonacci | Marble Joker; Stone Joker; The Duo; The Trio; The Family; Spare Trousers; Mad Joker; Clever Joker; The Tribe | Strength; Death; The Hanged Man | Real rank connectivity; repeated Straight attempts/success; Shortcut/Four Fingers/Runner/The Order evidence |
| **Flush** | Jupiter | The Tribe; Smeared Joker; Four Fingers | Droll Joker; Crafty Joker; Castle; Ancient Joker; Greedy Joker; Lusty Joker; Wrathful Joker; Gluttonous Joker; Arrowhead; Bloodstone; Onyx Agate; Rough Gem | Seeing Double (only with compatible mixed/effective-suit structure) | The Order; Runner; Crazy Joker; Devious Joker; The Family; Flower Pot (unless Smeared/Splash multi-suit package is a relevant strategy) | The Star; The Moon; The Sun; The World; Sigil; Death; The Hanged Man | Meaningful real/effective suit density; repeated Flush use; The Tribe/Smeared/Four Fingers/suit-payoff evidence |
| **Full House** | Earth | The Duo; The Trio | Jolly Joker; Sly Joker; Zany Joker; Wily Joker; Mad Joker; Clever Joker; Spare Trousers; Supernova; Card Sharp; Burnt Joker; Space Joker; DNA | Trading Card | Half Joker; Square Joker; The Family; The Order; Runner; Crazy Joker; Devious Joker; The Tribe; Droll Joker; Crafty Joker | Death; Strength; Cryptid | Two meaningful rank clusters; repeated Full House access; simultaneous Pair + Three-of-a-Kind Joker evidence |
| **Four of a Kind** | Mars | The Family; The Trio; The Duo; DNA | Zany Joker; Wily Joker; Jolly Joker; Sly Joker; Square Joker; Supernova; Card Sharp; Burnt Joker; Space Joker; Scholar (Ace target); Wee Joker (2 target) | Trading Card | Half Joker; Spare Trousers; Mad Joker; Clever Joker; The Order; Runner; Crazy Joker; Devious Joker; The Tribe; Droll Joker; Crafty Joker | Death; Cryptid; Ouija; The Hanged Man | High target-rank density; Four of a Kind already plausible; The Family/DNA evidence |
| **Straight Flush** | Neptune | The Order; The Tribe; Four Fingers; Shortcut; Smeared Joker; Séance | Runner; Crazy Joker; Devious Joker; Droll Joker; Crafty Joker; Castle; Ancient Joker | Arrowhead (Spades shell); Bloodstone (Hearts shell); Onyx Agate (Clubs shell); Rough Gem (Diamonds shell) | Marble Joker; Stone Joker; DNA (rank-collapse use); The Family; Spare Trousers | The Star; The Moon; The Sun; The World; Sigil; Strength; Death | Substantial simultaneous Straight + Flush structure. Neptune alone is never entry evidence |
| **Five of a Kind** | Planet X | The Family; The Trio; The Duo; DNA | Zany Joker; Wily Joker; Jolly Joker; Sly Joker; Supernova; Card Sharp; Burnt Joker; Space Joker; Scholar (Ace target); Wee Joker (2 target); The Idol (concentrated rank+suit state) | Trading Card | Half Joker; Square Joker; The Order; Runner; Crazy Joker; Devious Joker; The Tribe; Droll Joker; Crafty Joker | Cryptid; Ouija; Death; The Hanged Man | Strong existing target-rank density; repeated Four/Five-of-a-Kind feasibility; DNA/rank-copy evidence |
| **Flush House** | Ceres | The Tribe; The Trio; The Duo; Smeared Joker | Droll Joker; Crafty Joker; Zany Joker; Wily Joker; Jolly Joker; Sly Joker; Mad Joker; Clever Joker; Spare Trousers; Castle; Ancient Joker; Arrowhead; Bloodstone; Onyx Agate; Rough Gem | DNA; Trading Card | Half Joker; Square Joker; The Family; The Order; Runner; Crazy Joker; Devious Joker | The Star; The Moon; The Sun; The World; Sigil; Death; Cryptid | Mature Full-House rank clustering plus real/effective suit concentration |
| **Flush Five** | Eris | The Tribe; The Family; The Trio; The Duo; DNA; The Idol (identical rank+suit concentration) | Zany Joker; Wily Joker; Jolly Joker; Sly Joker; Droll Joker; Crafty Joker; Arrowhead; Bloodstone; Onyx Agate; Rough Gem; Supernova; Card Sharp | Smeared Joker; Trading Card | Half Joker; Square Joker; The Order; Runner; Crazy Joker; Devious Joker | Cryptid; Ouija; Death; The Star; The Moon; The Sun; The World; Sigil | Strong existing same-rank same-suit nucleus; repeated copy/conversion route; Flush Five already realistically reachable |

## Natural transition relationships

These are **pivot relationships**, not parent/child runtime classes.

| Current evidence | Natural next strategies |
|---|---|
| High Card | Pair; Steel; Face Cards |
| Pair | Two Pair; Three of a Kind; Full House |
| Two Pair | Full House; Three of a Kind; Four of a Kind |
| Three of a Kind | Full House; Four of a Kind; Five of a Kind |
| Straight | Straight Flush only with real suit evidence |
| Flush | Straight Flush; Flush House; Flush Five only with matching structural evidence |
| Full House | Four of a Kind; Five of a Kind; Flush House |
| Four of a Kind | Five of a Kind; Flush Five |

## Planet acquisition rule

Celestial value should be derived from these strategy states:

1. dominant matching poker-hand strategy — high value;
2. relevant matching strategy — meaningful value;
3. convergence-phase hand with strong structural/usage evidence — conditional value;
4. no real hand evidence — normally reject paid Planet acquisition;
5. speculative advanced hand with no structure — strongly reject.
