# Balatro Strategy Catalogue — Poker Hands

> Concrete universal poker-hand strategy definitions.
>
> The grouping is documentation-only. At runtime every strategy is a peer in the same universal strategy pool. See [`BALATRO_STRATEGY_PLAYBOOKS.md`](BALATRO_STRATEGY_PLAYBOOKS.md) for architecture, tier semantics, Ante progression, and implementation rules.

## Shared rule

A Planet is **support for an evidenced poker-hand strategy**, not sufficient strategy evidence by itself. Joker ownership, Tarot/Spectral effects, deck shape, hand-level investment, and actual repeated hand use should establish the direction first.

| Strategy | Planet | Gold | Silver | Bronze | Must avoid / conflicts | Key support / consumables | Entry evidence |
|---|---|---|---|---|---|---|---|
| **High Card** | Pluto | Stuntman; Baron + Mime when held Kings are real; Burnt Joker when first-discard scaling is safe; defining High-Card repetition/scaling engines | Supernova after repetition is established; Card Sharp; Half Joker; Space Joker targeting High Card; Green Joker; Blackboard when maintainable; held-card scorers | Generic flat Chips/Mult; generic economy; card-independent bridge scoring | Five-card-only engines when minimal-card play matters; heavy unrelated rank/suit restructuring | Deck thinning; Steel creation; held-card preservation; Death/copy on valuable held cards | Repeated High Card use; low construction burden is materially valuable; held-card/Joker package supports few-card play |
| **Pair** | Mercury | The Duo; defining Pair payoff/scaling; Half Joker when two-card Pair play is reliable | Jolly Joker; Sly Joker; Supernova after Pair repetition; Card Sharp; Burnt/Space Joker when Pair is the level target; matching rank-specific payoff | Generic scoring/economy; temporary compatible rank payoff | Heavy Straight structure; five-card-only packages with no compatible payoff | Death; Strength; selective rank duplication; selective thinning | Reliable duplicated ranks; Pair repeatedly available; direct Pair Joker evidence |
| **Two Pair** | Uranus | Spare Trousers; defining Two-Pair scaling | Mad Joker; Clever Joker; Pair-compatible payoff; Square Joker when four-card play is reliable; Supernova/Card Sharp after repetition | Generic scoring/economy; temporary Pair support | Heavy Straight spacing requirements; excessive single-rank concentration unless pivoting | Death/Strength to create several duplicated-rank clusters; selective thinning | Multiple duplicated ranks; repeated Two Pair; Spare Trousers or other direct support |
| **Three of a Kind** | Venus | The Trio; defining Three-of-a-Kind scaling; strong rank-copy engine after target rank exists | Zany Joker; Wily Joker; Pair-condition effects that remain active; matching rank payoff; Half Joker when three-card play is advantageous | Generic scoring/economy compatible with rank concentration | Mature Straight structure; broad rank-diversity requirements | Death; Strength; Cryptid-style copying; off-rank destruction | One rank already meaningfully concentrated; repeated Three of a Kind; direct Joker evidence |
| **Straight** | Saturn | Shortcut; Four Fingers; Runner; The Order | Crazy Joker; Devious Joker; Superposition when Ace Straights are realistic; Card Sharp/Supernova after consistency | Generic scoring/economy that preserves rank coverage | Mature single-rank concentration; held-card shells that cannot spare construction cards | Preserve central connectors; Death/Strength to repair gaps; remove isolated/excess duplicate ranks | Real rank connectivity; repeated Straight attempts/success; Shortcut/Four Fingers/Runner-type evidence |
| **Flush** | Jupiter | The Tribe; Smeared Joker when it materially increases effective suit density; Four Fingers; Bloodstone in Hearts; Arrowhead in Spades; Onyx Agate in Clubs; Rough Gem in Diamonds when strategically relevant | Droll Joker; Crafty Joker; Castle when safely scalable; Ancient Joker when exploitable; matching suit-specific payoff | Generic scoring/economy; temporary suit support | Random conversion that lowers effective dominant-suit density; mature single-rank concentration unless transitioning to Flush House/Five | Suit-conversion Tarots; selective off-suit destruction; Smeared-aware suit shaping | Meaningful actual/effective suit density; repeated Flush use; direct Flush/suit Joker evidence |
| **Full House** | Earth | The Family; strong rank-manipulation package preserving two useful clusters | Dedicated Full-House Chips/Mult; Pair/Three-kind pieces that remain useful; repetition scaling after reliability | Generic scoring/economy compatible with clustered ranks | Indiscriminate collapse to one rank unless intentionally pivoting; mature Straight structure | Controlled duplication/destruction; maintain primary triple-capable and secondary pair-capable ranks | Two meaningful rank clusters; repeated Full House access; direct Full-House support |
| **Four of a Kind** | Mars | The Family; powerful target-rank copy/destruction engine after concentration exists | Direct Four-kind Chips/Mult; matching rank-specific payoff; Three-kind engines that survive transition | Generic scaling compatible with concentrated ranks | Premature rank collapse without density; Straight/rank-diversity packages | Death; Cryptid; Ouija-style concentration when safe; off-rank destruction | High target-rank density or repeatable copying capacity; Four-kind already plausible |
| **Straight Flush** | Neptune | Combined Shortcut/Four Fingers + real suit control; The Order/The Tribe when both conditions are repeatable; other true combined consistency packages | Existing compatible Straight and Flush engines | Generic scoring that damages neither requirement | **Do not chase from an ordinary deck**; Neptune alone; rank collapse incompatible with Straights | Suit conversion only when it preserves Straight bands; targeted thinning | Substantial **simultaneous** Straight and Flush evidence. Neptune is never entry evidence by itself |
| **Five of a Kind** | Planet X | Cryptid/Ouija/rank-copy engines after one rank is already dominant; major matching-rank payoff | Four/Three-kind engines that remain useful while transitioning | Generic scaling compatible with rank collapse | Early speculative rank collapse; Straight/rank-diversity packages | Repeated target-rank copying; off-rank destruction | Strong existing target-rank density; repeated Four/Five-kind feasibility |
| **Flush House** | Ceres | Rank-copy + suit-conversion package capable of repeatedly making 3+2 in one effective suit | Existing Full-House and Flush components supported simultaneously | Generic compatible scoring only after structure exists | Speculative purchase from ordinary deck; Ceres alone; conversions that destroy either rank-cluster or suit structure | Controlled rank duplication + suit conversion | Mature Full-House **and** Flush structural evidence |
| **Flush Five** | Eris | Rank-copy + suit-copy/conversion package around an existing identical rank+suit nucleus | Existing Five-kind and Flush components supported simultaneously | Generic compatible scaling only after structure exists | Speculative purchase from ordinary deck; Eris alone | Copy identical cards; targeted suit/rank conversion; aggressive off-plan thinning only after nucleus exists | Strong existing identical-card concentration |

## Natural transition relationships

These are **pivot relationships**, not parent/child runtime classes.

| Current evidence | Natural next strategies |
|---|---|
| High Card | Pair; Steel; Face Cards |
| Pair | Two Pair; Three of a Kind; Full House |
| Two Pair | Full House; Three/Four of a Kind |
| Three of a Kind | Full House; Four of a Kind; Five of a Kind |
| Straight | Straight Flush only with real suit evidence |
| Flush | Straight Flush; Flush House; Flush Five only with matching structural evidence |
| Full House | Four/Five of a Kind; Flush House |
| Four of a Kind | Five of a Kind; Flush Five |

## Planet acquisition rule

Celestial value should be derived from these strategy states:

1. dominant matching poker-hand strategy — high value;
2. relevant matching strategy — meaningful value;
3. convergence-phase hand with strong structural/usage evidence — conditional value;
4. no real hand evidence — normally reject paid Planet acquisition;
5. speculative advanced hand with no structure — strongly reject.
