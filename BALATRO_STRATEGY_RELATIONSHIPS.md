# Balatro Strategy Relationships

Development reference for [`BALATRO_STRATEGY_TREE.md`](BALATRO_STRATEGY_TREE.md).

## Runtime implementation status

- **Part 4 / Section 4 — Enhancements: IMPLEMENTED.** The runtime catalogue contains 5 enhancement roots and 15 leaves. Conditional relationships require real Stone/Glass/Steel/Lucky/Gold infrastructure (or the defining payoff where appropriate) before generic support Jokers can contribute route evidence. Parent/child static components are disjoint.
- **Part 5 / Section 5 — Seals: IMPLEMENTED.** The runtime catalogue contains all 6 seal nodes. Played Red-Seal support requires an actual Red Seal; held Red-Seal support additionally checks material held effects/ranks; Blue, Purple, and Gold Seal support is likewise gated on matching seals in the live deck.
- The current runtime contract also includes Sections 6–12. The tables below remain the canonical relationship/evidence specification; these status notes describe which frozen rows are now enforced by runtime code and tests.

## Evidence weights

| Evidence | Score |
|---|---:|
| Gold Joker | +8.00 |
| Silver Joker | +3.00 |
| Bronze Joker | +1.00 |
| Banned component | -8.00 |
| Matching Planet / permanent hand level gained | +0.50 per level |
| Strategy-directed Tarot use | +0.30 per use |
| Strategy-directed Spectral use | +0.50 per use |
| Matching enhancement in current deck | +0.35 per card |

`—` = intentionally none. All frozen v1.0 relationship rows are audited; no
`TBD` entries remain.

## Universal value versus strategy relationship

Joker value and strategy evidence are independent axes. Gold/Silver/Bronze say
how strongly a Joker supports one route; they do not replace the ordinary
whole-build score, economy, scaling, or survival evaluator.

| Applicability | Meaning | Strategy behavior |
|---|---|---|
| `UNIVERSAL` | The Joker has positive intrinsic/contextual value without requiring the active route. Misprint, Bull, and Cloud 9 are examples. | Keep ordinary value; do not create false strategy evidence and do not apply an off-path penalty. |
| `ALIGNED` | A positive relationship supports the active strategy. | Keep ordinary value and add Gold/Silver/Bronze reinforcement. |
| `PIVOT` | Before Ante 6, a different Gold core supplies enough projected evidence to justify a real pivot. | Keep ordinary value and allow the pivot. |
| `OFF_PATH` | The Joker's trigger or enabling rule requires another route, such as Crafty Joker under Pair. | Remove generic probes from the unrelated route and apply a dynamic opportunity cost. |
| `CONFLICT` | An explicit Banned mechanic harms the active route. | Apply the Banned penalty; survival value can still override a sale. |

Joker editions are universal modifiers on the same independent value axis: Foil
`+0.8`, Holographic `+1.5`, Polychrome `+2.5`, and Negative `+4.0` for
acquisition/retention economics, in addition to their modeled scoring effect.
Negative is also slot-neutral. Edition value cannot override an explicit
`CONFLICT`; non-Negative editions still consume money and a Joker slot, so their
bonus must beat the incumbent and transaction opportunity cost.

`OFF_PATH` is not a fixed `-1` or `-2`. It scales with dominant-strategy score,
the candidate's relationship tier, Ante pressure, and the configured alignment
scale. At full pressure against a score-8 strategy, the strategy term is about
`-0.64` for Bronze, `-1.92` for Silver, and `-5.12` for Gold, before the generic
off-route probe discount. Merely appearing in another strategy table is not enough
to make a portable Joker off-path.

`Branch` is the top-level strategy branch. `Node` is the exact strategy node. `[I]` nodes have specialized descendants; `[L]` nodes have none.

An `[I]` node contains only evidence shared by every specialization beneath it. A child row contains only additional evidence specific to that child. This factoring rule applies to Gold, Silver, Bronze, Banned, Tarot, Planet, Spectral, and Enhancement.

A component must not be duplicated between a parent and child row. If it is specific to one specialization, it belongs only on that specialization.

## 1. Poker hands

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| High Card | High Card `[I]` | Burnt Joker | Card Sharp; Supernova; Space Joker; Half Joker; Green Joker; Burglar | — | Obelisk | The Chariot | Pluto | — | Steel |
| High Card | ↳ Stuntman / Small-Hand High Card `[L]` | Stuntman | — | — | — | — | — | — | — |
| High Card | ↳ Baron-Mime Steel-King High Card `[L]` | Baron; Mime | Blackboard; Shoot the Moon; Troubadour; Juggler | Raised Fist; Reserved Parking | Stuntman | — | — | — | — |
| Pair | Pair `[L]` | The Duo | Jolly Joker; Sly Joker; Half Joker; Supernova; Card Sharp; Space Joker; Burnt Joker; Green Joker; Burglar *(generic support requires Pair commitment)* | DNA; Trading Card *(with Pair commitment)*; Hologram *(with Pair commitment + DNA)* | Obelisk | — | Mercury | — | — |
| Two Pair | Two Pair `[L]` | Spare Trousers | Mad Joker; Clever Joker; Square Joker; The Duo; Supernova; Card Sharp; Space Joker; Burnt Joker *(repeat support requires Two Pair commitment)* | Jolly Joker; Sly Joker | Obelisk | Death; Strength | Uranus | — | — |
| Three of a Kind | Three of a Kind `[L]` | The Trio | Zany Joker; Wily Joker; DNA; Half Joker; The Duo; Supernova; Card Sharp; Space Joker; Burnt Joker *(repeat support requires Trips commitment)* | Jolly Joker; Sly Joker; Trading Card | Obelisk | Death; Strength | Venus | Cryptid; Ouija | — |
| Straight | Straight `[L]` | The Order; Shortcut; Four Fingers; Runner; Superposition | Crazy Joker; Devious Joker; Supernova; Card Sharp; Space Joker; Burnt Joker *(repeat support requires Straight commitment)* | Fibonacci; Hack *(rank support requires Straight commitment)* | Obelisk | Strength; Death | Saturn | — | — |
| Straight Flush | Straight Flush `[L]` | The Order; The Tribe; Shortcut; Four Fingers; Runner; Smeared Joker; Seance | Crazy Joker; Devious Joker; Droll Joker; Crafty Joker; Supernova; Card Sharp; Space Joker; Burnt Joker *(repeat support requires Straight Flush commitment)* | Arrowhead; Bloodstone; Onyx Agate; Rough Gem *(requires an effective same-suit Straight)* | Obelisk | Strength; Death; The Lovers | Neptune | Sigil | Wild |
| Flush | Flush `[L]` | The Tribe | Droll Joker; Crafty Joker; Smeared Joker; Four Fingers; Supernova; Card Sharp; Space Joker; Burnt Joker *(repeat support requires Flush commitment)* | Arrowhead; Bloodstone; Onyx Agate; Rough Gem *(requires matching suit concentration)* | Obelisk | The Lovers | Jupiter | Sigil | Wild |
| Full House | Full House `[L]` | — | The Trio; The Duo; Spare Trousers; Zany Joker; Wily Joker; Mad Joker; Clever Joker; Supernova; Card Sharp; Space Joker; Burnt Joker *(repeat support requires Full House commitment)* | Jolly Joker; Sly Joker; DNA; Trading Card | Obelisk | Death; Strength | Earth | Cryptid; Ouija | — |
| Flush House | Flush House `[L]` | The Tribe | The Trio; The Duo; Spare Trousers; Zany Joker; Wily Joker; Mad Joker; Clever Joker; Smeared Joker; Droll Joker; Crafty Joker; Supernova; Card Sharp; Space Joker; Burnt Joker *(repeat support requires Flush House commitment)* | Jolly Joker; Sly Joker; DNA; Trading Card | Obelisk | Death; Strength; The Lovers | Ceres | Cryptid; Ouija; Sigil | Wild |
| Four of a Kind | Four of a Kind `[L]` | The Family | The Trio; DNA; Zany Joker; Wily Joker; Square Joker; Supernova; Card Sharp; Space Joker; Burnt Joker *(repeat support requires Quads commitment)* | The Duo; Jolly Joker; Sly Joker; Trading Card | Obelisk | Death; Strength | Mars | Cryptid; Ouija | — |
| Five of a Kind | Five of a Kind `[L]` | The Family | The Trio; DNA; The Idol; Zany Joker; Wily Joker; Supernova; Card Sharp; Space Joker; Burnt Joker *(repeat support requires Five Kind commitment)* | The Duo; Jolly Joker; Sly Joker; Trading Card | Obelisk | Death; Strength | Planet X | Cryptid; Ouija | — |
| Flush Five | Flush Five `[L]` | The Family; DNA; The Idol; The Tribe | The Trio; Zany Joker; Wily Joker; Smeared Joker; Droll Joker; Crafty Joker; Supernova; Card Sharp; Space Joker; Burnt Joker *(repeat support requires Flush Five commitment)* | The Duo; Jolly Joker; Sly Joker; Trading Card | Obelisk | Death; Strength; The Lovers | Eris | Cryptid; Ouija; Sigil | Wild |

## 2. Rank and face cards

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Aces | Aces `[L]` | Scholar | DNA *(with Ace commitment)*; Fibonacci *(with Ace commitment)*; Odd Todd *(with Ace commitment)* | The Idol *(Ace target + concentration)* | — | Death; Strength; The Hanged Man | — | Grim; Cryptid | — |
| Low-Rank Scoring | Low-Rank Scoring `[L]` | Fibonacci; Hack | Odd Todd; Even Steven; Hanging Chad; Seltzer; Dusk *(retriggers require low-rank commitment)* | — | — | Death; Strength; The Hanged Man | — | Incantation; Cryptid | — |
| Twos | Twos / Wee-Hack `[L]` | Wee Joker | Hack *(with Two commitment)*; Fibonacci *(with Two commitment)*; Even Steven *(with Two commitment)* | DNA *(with Two commitment)*; Hologram *(with Two commitment)*; The Idol *(Two target + concentration)* | — | Death; Strength; The Hanged Man | — | Cryptid | — |
| Ten-Four | Ten-Four / Walkie Talkie `[L]` | Walkie Talkie | Even Steven *(with Ten-Four commitment)*; Hack *(with Four commitment)* | DNA; Hologram; The Idol *(all with Ten-Four commitment)* | — | Death; Strength; The Hanged Man | — | Cryptid | — |
| Sixes / Sixth Sense | Sixes / Sixth Sense `[L]` | Sixth Sense | Even Steven *(with Six commitment)* | DNA; Hologram *(with Six commitment)*; The Idol *(Six target + concentration)* | — | Death; Strength | — | — | — |
| Jacks / Hit the Road | Jacks / Hit the Road `[L]` | Hit the Road | Faceless Joker *(with Jack commitment)*; Mail-In Rebate *(Jack target)* | Merry Andy *(with Hit the Road)*; Drunkard *(with Hit the Road)* | — | Death; Strength | — | Cryptid | — |
| Queens / Shoot the Moon | Queens / Shoot the Moon `[L]` | Shoot the Moon | Mime *(with Queen commitment)* | Reserved Parking *(with Queen commitment)* | — | Death; Strength | — | Cryptid | Steel Queens |
| Face Cards | Face Cards `[I]` | — | Scary Face; Smiley Face; Midas Mask | — | Ride the Bus | Death; Strength; The Hanged Man | — | Familiar | — |
| Face Cards | ↳ Photograph + Hanging Chad `[L]` | Photograph; Hanging Chad *(with Photograph)* | Sock and Buskin *(with Photograph)*; Seltzer *(with Photograph)*; Dusk *(with Photograph)* | — | — | Justice | — | Deja Vu; Cryptid | Glass face cards |
| Face Cards | ↳ Triboulet + Sock and Buskin `[L]` | Triboulet; Sock and Buskin *(with Triboulet)* | Hanging Chad *(with Triboulet)*; Seltzer *(with Triboulet)*; Dusk *(with Triboulet)* | — | — | Justice | — | Deja Vu; Cryptid | Glass Queens / Kings |
| Face Cards | ↳ Pareidolia Universal Face Scoring `[L]` | Pareidolia *(with inherited face-card payoff)* | — | — | — | — | — | — | — |
| Face Cards | ↳ Held Face-Card Economy `[L]` | Reserved Parking | Mime *(with Reserved Parking)*; Pareidolia *(with Reserved Parking)* | — | — | The Devil | — | — | Gold face cards |
| Face Cards | ↳ Business Card Face Economy `[L]` | Business Card; Oops! All 6s *(with Business Card)* | Pareidolia; Sock and Buskin; Hanging Chad; Seltzer; Dusk *(all with Business Card)* | — | — | — | — | — | — |
| Faceless / No-Face | Faceless / No-Face `[I]` | — | — | — | — | The Hanged Man; Death | — | Incantation; Grim | — |
| Faceless / No-Face | ↳ Ride the Bus No-Face Scaling `[L]` | Ride the Bus | Trading Card *(with Ride the Bus)* | Faceless Joker *(with Ride the Bus)*; Hit the Road *(with Ride the Bus)* | Pareidolia; Splash; Photograph; Sock and Buskin; Triboulet; Scary Face; Smiley Face; Business Card; Midas Mask; Familiar | — | — | — | — |
| Faceless / No-Face | ↳ Faceless Joker Discard Economy `[L]` | Faceless Joker; Pareidolia *(with Faceless Joker)* | Merry Andy; Drunkard; Hit the Road; Mail-In Rebate *(all with Faceless Joker)* | — | — | — | — | Familiar | — |
| The Idol Exact-Card Concentration | The Idol Exact-Card Concentration `[L]` | The Idol *(4+ effective target cards)* | The Idol *(2–3 effective target cards)*; DNA; Trading Card *(support requires active Idol target)* | — | — | Death; The Hanged Man | — | Cryptid | Glass target cards |

## 3. Suits and held cards

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Hearts | Hearts `[I]` | Bloodstone | Lusty Joker; Smeared Joker *(with Heart payoff)* | — | — | The Sun; Death; The Hanged Man | — | Sigil | Wild |
| Hearts | ↳ Bloodstone + Oops! All 6s Hearts `[L]` | Oops! All 6s *(with Bloodstone)* | — | — | — | — | — | — | — |
| Hearts | ↳ Bloodstone Retrigger Hearts `[L]` | — | Hanging Chad; Seltzer; Dusk; Sock and Buskin; Hack *(all with Bloodstone)* | — | — | — | — | Deja Vu | — |
| Diamonds / Rough Gem Economy | Diamonds / Rough Gem Economy `[L]` | Rough Gem | Greedy Joker; Smeared Joker *(with Diamond payoff)*; Hanging Chad; Seltzer; Dusk; Sock and Buskin; Hack *(retrigger support requires Rough Gem or Greedy Joker)* | — | — | The Star; Death; The Hanged Man | — | Sigil | Wild |
| Clubs | Clubs `[I]` | — | Gluttonous Joker; Smeared Joker *(with Club payoff)* | — | — | The Moon; Death; The Hanged Man | — | Sigil | Wild |
| Clubs | ↳ Onyx Agate Club Scoring `[L]` | Onyx Agate | Hanging Chad; Seltzer; Dusk; Sock and Buskin; Hack *(all with Onyx Agate)* | — | — | — | — | Deja Vu | — |
| Clubs | ↳ Seeing Double Mixed-Suit Clubs `[L]` | Seeing Double | — | Splash *(with Seeing Double)* | — | The Lovers | — | — | — |
| Spades / Arrowhead Chips | Spades / Arrowhead Chips `[L]` | Arrowhead | Wrathful Joker; Smeared Joker *(with Spade payoff)*; Hanging Chad; Seltzer; Dusk; Sock and Buskin; Hack *(retrigger support requires Arrowhead or Wrathful Joker)* | — | — | The World; Death; The Hanged Man | — | Sigil | Wild |
| Blackboard Held-Black Cards | Blackboard Held-Black Cards `[L]` | Blackboard | Smeared Joker *(with Blackboard)* | — | — | The Moon; The World | — | — | Wild |
| Raised Fist Held-Minimum | Raised Fist Held-Minimum `[L]` | Raised Fist | Mime *(with Raised Fist)* | — | — | Strength; Death; The Hanged Man | — | Familiar; Grim; Cryptid; Deja Vu | — |
| Ancient Joker Suit-Rotation | Ancient Joker Suit-Rotation `[L]` | Ancient Joker | Smeared Joker; Hanging Chad; Seltzer; Dusk; Sock and Buskin; Hack *(all with Ancient Joker)* | — | — | The Star; The Moon; The Sun; The World | — | Sigil; Deja Vu | Wild |
| Flower Pot Multi-Suit | Flower Pot Multi-Suit `[I]` | Flower Pot | — | — | — | The Star; The Moon; The Sun; The World | — | Sigil | Wild |
| Flower Pot Multi-Suit | ↳ Splash + Flower Pot `[L]` | Splash *(with Flower Pot)* | — | — | — | — | — | — | — |
| Flower Pot Multi-Suit | ↳ Smeared Joker + Flower Pot `[L]` | Smeared Joker *(with Flower Pot)* | — | — | — | — | — | — | — |

## 4. Enhancements — runtime implemented

Runtime status: **complete for Part 4.** The five parent enhancement shells and fifteen leaves are present in the tree-aware tracker. Conditional leaf support is deliberately delayed until the matching enhancement or defining payoff is material; e.g. DNA does not seed Stone duplication from a natural deck, Hanging Chad does not seed Glass retrigger, and Mime does not seed Steel-Mime without Steel infrastructure.

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Stone | Stone `[I]` | — | — | — | — | The Tower; Death | — | Cryptid | Stone |
| Stone | ↳ Marble Joker + Stone Joker Scaling `[L]` | Marble Joker; Stone Joker *(with Marble)* | Hologram; Driver's License *(with Marble)* | Blue Joker; Certificate *(with Marble)* | — | — | — | — | — |
| Stone | ↳ Marble Joker + Vampire Stone Feed `[L]` | Marble Joker; Vampire *(with Marble + Stone shell)* | Hologram *(with Marble)* | Certificate *(with Marble)* | — | — | — | — | — |
| Stone | ↳ DNA + Stone Joker Duplication `[L]` | DNA *(with Stone shell)* | Hologram; Stone Joker *(with Stone shell)* | Certificate; Blue Joker *(with Stone shell)* | — | — | — | — | — |
| Stone | ↳ Stone High Card `[L]` | — | Half Joker; Burnt Joker; Card Sharp; Supernova *(with Stone shell)* | Blue Joker; Raised Fist *(with Stone shell)* | — | — | Pluto | — | — |
| Glass | Glass `[I]` | — | — | — | Vampire; Midas Mask | Justice; Death | — | Cryptid; Ankh | Glass |
| Glass | ↳ Glass Joker Breakage Scaling `[L]` | Glass Joker | DNA; Hologram *(with Glass shell)* | Certificate *(with Glass shell)* | — | — | — | — | — |
| Glass | ↳ Glass Retrigger Scoring `[L]` | Hanging Chad *(with Glass shell)* | Dusk; Seltzer; Sock and Buskin; Hack *(with Glass shell)* | Splash; DNA; Hologram *(with Glass shell)* | — | — | — | Deja Vu | — |
| Steel | Steel `[I]` | — | — | — | Vampire; Midas Mask | The Chariot; Death | — | Cryptid; Trance | Steel |
| Steel | ↳ Steel Joker Density Scaling `[L]` | Steel Joker | DNA; Hologram *(with Steel shell)* | Certificate; Blue Joker *(with Steel shell)* | — | — | — | — | — |
| Steel | ↳ Mime Steel Retrigger `[L]` | Mime *(with Steel shell)* | Troubadour; Juggler *(with Steel shell)* | Raised Fist; Reserved Parking; Shoot the Moon *(with Steel shell)* | — | — | — | Deja Vu | — |
| Lucky | Lucky `[I]` | — | — | — | Vampire; Midas Mask | The Magician; Death | — | Cryptid | Lucky |
| Lucky | ↳ Lucky Cat Scaling `[L]` | Lucky Cat | DNA; Hologram *(with Lucky shell)* | Certificate *(with Lucky shell)* | — | — | — | — | — |
| Lucky | ↳ Lucky Cat + Oops! All 6s `[L]` | Oops! All 6s *(with Lucky Cat)* | — | Business Card *(with Lucky Cat)* | — | — | — | — | — |
| Lucky | ↳ Lucky Retrigger `[L]` | Hanging Chad *(with Lucky shell)* | Dusk; Seltzer; Sock and Buskin; Hack *(with Lucky shell)* | DNA; Hologram *(with Lucky shell)* | — | — | — | Deja Vu | — |
| Gold Cards | Gold Cards `[I]` | — | — | — | Vampire | The Devil; Death | — | Cryptid; Talisman | Gold |
| Gold Cards | ↳ Held Gold + Mime Economy `[L]` | Mime *(with Gold-card shell)* | Reserved Parking; To the Moon; Bull; Bootstraps *(with Gold-card shell)* | Rocket; Cloud 9; Golden Joker *(with Gold-card shell)* | — | — | — | Deja Vu | — |
| Gold Cards | ↳ Golden Ticket Gold Scoring `[L]` | Golden Ticket; Hanging Chad *(with Golden Ticket)* | Dusk; Seltzer; Sock and Buskin; Hack *(with Golden Ticket)* | Business Card; Bull; Bootstraps *(with Golden Ticket)* | — | — | — | — | — |
| Gold Cards | ↳ Midas Mask Gold Generation `[L]` | Midas Mask | Pareidolia; Splash *(with Midas Mask)* | Scary Face; Smiley Face; Business Card; Reserved Parking *(with Midas Mask)* | — | — | — | — | — |
| Gold Cards | ↳ Midas Mask + Golden Ticket Economy `[L]` | Midas Mask; Golden Ticket *(when paired)* | Hanging Chad; Dusk; Seltzer; Sock and Buskin; Hack *(with pair)* | Business Card; Bull; Bootstraps *(with pair)* | — | — | — | — | — |

## 5. Seals — runtime implemented

Runtime status: **implemented for Part 5.** Section 5 contains six runtime nodes: Red Seal plus its played/held leaves, and standalone Blue, Purple, and Gold Seal routes. Generic support remains Neutral until the appropriate live seal context exists. Held Red-Seal Mime additionally requires a material held effect; Red Kings/Queens and low cards gate Baron, Shoot the Moon, and Raised Fist relationships respectively.

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Red Seal | Red Seal `[I]` | — | — | — | — | — | — | Deja Vu; Cryptid | — |
| Red Seal | ↳ Played Red-Seal Retrigger `[L]` | Hanging Chad *(with Red Seal)* | Seltzer; Dusk; Hiker; Splash; Sock and Buskin *(Red face)*; Hack *(Red 2–5)*; Photograph; Triboulet; Bloodstone; Lucky Cat *(matching Red card)* | Scary Face; Smiley Face; Business Card; Fibonacci *(matching Red card)* | — | — | — | — | — |
| Red Seal | ↳ Held Red-Seal Retrigger `[L]` | Mime *(Red held-effect card)*; Baron *(Red King)* | Shoot the Moon *(Red Queen)*; Reserved Parking *(Red face)*; Raised Fist *(Red low card)* | Juggler; Troubadour *(material held Red card)* | — | — | — | — | Steel; Gold |
| Blue Seal Hand-Level Scaling | Blue Seal Hand-Level Scaling `[L]` | Constellation; Satellite *(with Blue Seal)* | Certificate; Perkeo; Astronomer *(with Blue Seal)* | Burnt Joker; Space Joker; Juggler; Troubadour *(with Blue Seal)* | — | — | Any | Trance; Cryptid | — |
| Purple Seal Tarot Engine | Purple Seal Tarot Engine `[L]` | Fortune Teller; Merry Andy; Drunkard *(with Purple Seal)* | Burnt Joker; Castle; Mail-In Rebate; Faceless Joker; Certificate *(with Purple Seal)* | Perkeo; Cartomancer; Hallucination; Vagabond; Mystic Summit *(with Purple Seal)* | Burglar; Delayed Gratification; Green Joker; Ramen; Banner | Any | — | Medium; Cryptid | — |
| Gold Seal Economy | Gold-Seal Retrigger Economy `[L]` | Hanging Chad; Seltzer; Dusk *(with Gold Seal)* | Sock and Buskin *(Gold face)*; Hack *(Gold 2–5)*; Bull; Bootstraps; To the Moon; Rocket *(with Gold Seal)* | Business Card *(Gold face)*; Certificate; DNA; Splash *(with Gold Seal)* | — | — | — | Talisman; Cryptid | — |

## 6. Destruction, sacrifice, consumption, thinning

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Canio Destruction | Canio Destruction `[I]` | Canio | — | — | — | The Hanged Man; Justice | — | Familiar; Immolate | Glass |
| Canio Destruction | ↳ Trading Card Canio `[L]` | Trading Card *(with Canio)* | Pareidolia *(with Canio)* | Faceless Joker; Merry Andy; Drunkard *(with Canio)* | — | — | — | — | — |
| Canio Destruction | ↳ Pareidolia Canio `[L]` | Pareidolia *(with Canio)* | Trading Card *(with Canio)* | Midas Mask; Splash *(with Canio)* | — | — | — | Familiar | — |
| Canio Destruction | ↳ Glass Canio `[L]` | Glass Joker *(with Canio + Glass)* | Hanging Chad; Seltzer; Dusk; Sock and Buskin; Hack *(with Canio + Glass)* | DNA; Hologram *(with Canio + Glass)* | — | Justice | — | Familiar | Glass |
| Canio Destruction | ↳ Consumable Canio `[L]` | Scaled Canio *(public XMult state)* | — | — | — | The Hanged Man | — | Immolate | — |
| Vampire | Vampire `[I]` | Vampire | — | — | — | Any enhancement Tarot | — | Familiar; Grim; Incantation | Any scoring enhancement |
| Vampire | ↳ Midas Mask + Vampire `[L]` | Midas Mask *(with Vampire)* | Pareidolia; Splash *(with Vampire)* | — | — | The Devil | — | — | Gold |
| Vampire | ↳ Pareidolia + Midas Mask + Vampire `[L]` | Pareidolia; Midas Mask *(paired with Vampire)* | Splash *(with trio)* | — | — | The Devil | — | Familiar | Gold |
| Ceremonial Dagger Sacrifice | Ceremonial Dagger / Disposable-Joker Feed `[L]` | Ceremonial Dagger | Riff-Raff; Egg; Gift Card; Blueprint; Brainstorm *(with Dagger)* | Invisible Joker | Eternal sacrifice targets | — | — | — | — |
| Madness Destruction | Madness Destruction `[I]` | Madness | Blueprint; Brainstorm *(with Madness)* | — | — | — | — | — | — |
| Madness Destruction | ↳ Solo Madness `[L]` | Madness *(no other destroyable Jokers)* | Joker Stencil | — | — | — | — | — | — |
| Madness Destruction | ↳ Eternal-Joker Madness `[L]` | Eternal Jokers *(with Madness)* | — | — | — | — | — | — | — |
| Deck Thinning | Deck Thinning `[I]` | — | — | — | — | The Hanged Man | — | Immolate | — |
| Deck Thinning | ↳ Trading Card Thinning / Economy `[L]` | Trading Card | — | — | — | — | — | — | — |
| Deck Thinning | ↳ Erosion Thinning `[L]` | Erosion | — | — | — | — | — | — | — |
| Deck Thinning | ↳ Trading Card + Erosion `[L]` | Trading Card; Erosion *(when paired)* | — | — | — | The Hanged Man | — | Immolate | — |

## 7. Deck growth and card training

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Hologram Deck-Growth | Hologram Deck-Growth `[I]` | Hologram | Blueprint; Brainstorm *(with Hologram)* | — | — | — | — | Cryptid; Familiar; Grim; Incantation | — |
| Hologram Deck-Growth | ↳ DNA + Hologram `[L]` | DNA *(with Hologram)* | Blueprint; Brainstorm *(with pair)* | — | — | — | — | Cryptid | — |
| Hologram Deck-Growth | ↳ Certificate + Hologram `[L]` | Certificate *(with Hologram)* | Blueprint; Brainstorm *(with pair)* | — | — | — | — | — | — |
| Hologram Deck-Growth | ↳ Marble Joker + Hologram `[L]` | Marble Joker *(with Hologram)* | Blueprint; Brainstorm *(with pair)* | — | — | The Tower | — | — | Stone |
| Hiker Card Training | Hiker Retrigger / Copy Training `[L]` | Hiker | Hanging Chad; Seltzer; Dusk; Sock and Buskin; Hack; Splash; DNA; Blueprint; Brainstorm *(with Hiker)* | Certificate *(with Hiker)* | — | — | — | Cryptid; Deja Vu | — |
| Driver's License Enhancement-Density | Driver's License Enhancement-Density `[L]` | Driver's License | Midas Mask; Marble Joker; Certificate; Blueprint; Brainstorm *(with Driver's License)* | DNA; Hologram *(with Driver's License)* | Vampire | The Magician; The Empress; The Hierophant; The Lovers; The Chariot; Justice; The Devil; The Tower | — | Familiar; Grim; Incantation | Any |
| Blue Joker Large-Deck Chips | Blue Joker Large-Deck Chips `[L]` | Blue Joker | Hologram; Certificate; Marble Joker *(with Blue Joker)* | DNA *(with Blue Joker)* | Erosion; Trading Card | — | — | Familiar; Grim; Incantation; Cryptid | — |

## 8. Planet, Tarot, consumable engines

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Planet Engine | Planet Engine `[I]` | — | Astronomer | — | — | The High Priestess | Any | Black Hole | — |
| Planet Engine | ↳ Constellation Planet-Scaling `[L]` | Constellation | Astronomer; Perkeo; Blueprint; Brainstorm *(with Constellation)* | Satellite *(without full pair)* | — | — | Any | — | — |
| Planet Engine | ↳ Satellite Planet-Economy `[L]` | Satellite | Astronomer; Perkeo; Blueprint; Brainstorm *(with Satellite)* | Constellation *(without full pair)* | — | — | Any | — | — |
| Planet Engine | ↳ Constellation + Satellite Planet Engine `[L]` | Constellation; Satellite *(when paired)* | Astronomer; Perkeo *(with pair)* | — | — | — | Any | — | — |
| Perkeo Consumable Duplication | Perkeo Consumable Duplication `[I]` | Perkeo | — | — | — | — | — | — | — |
| Perkeo Consumable Duplication | ↳ Perkeo + Observatory Planet Stack `[L]` | Perkeo *(with Observatory)* | — | — | — | — | Any held Planet | — | — |
| Perkeo Consumable Duplication | ↳ Perkeo + Cryptid Copy Engine `[L]` | Perkeo *(with held Cryptid)* | — | — | — | — | — | Cryptid | — |
| Perkeo Consumable Duplication | ↳ Perkeo Tarot / Spectral Engine `[L]` | Perkeo *(with held Tarot/Spectral)* | — | — | — | Any held Tarot | — | Any held Spectral | — |
| Tarot Engine | Tarot Engine `[I]` | Fortune Teller | — | — | — | Any | — | — | — |
| Tarot Engine | ↳ Cartomancer Blind-Select Generation `[L]` | Cartomancer | — | — | — | Any | — | — | — |
| Tarot Engine | ↳ Hallucination Pack-Open Generation `[L]` | Hallucination | — | — | — | Any | — | — | — |
| Tarot Engine | ↳ 8 Ball / Eights Tarot Generation `[L]` | 8 Ball | Oops! All 6s; Hanging Chad; Seltzer; Dusk *(all with 8 Ball)* | Fibonacci *(with Eight commitment)* | — | Death; Strength; The Hanged Man | — | Cryptid | — |
| Vagabond Low-Money Tarot Engine | Vagabond Low-Money Tarot Engine `[L]` | Vagabond | Fortune Teller; Blueprint; Brainstorm *(with Vagabond)* | — | Cash-hoard commitments that prevent the $4 trigger | Any | — | — | — |

## 9. Economy, shop, reroll, blind skip

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Cash Hoard / Interest | Cash Hoard / Interest `[I]` | — | — | — | Vagabond commitment | The Hermit; Temperance | — | Immolate | — |
| Cash Hoard / Interest | ↳ Rocket / To the Moon Cash Growth `[L]` | Rocket; To the Moon | Blueprint; Brainstorm *(with owned core)* | Golden Joker; Cloud 9; Golden Ticket | Vagabond commitment | The Hermit; Temperance | — | Immolate | — |
| Cash Hoard / Interest | ↳ Bull Cash-to-Chips `[L]` | Bull | Rocket; To the Moon; Blueprint; Brainstorm *(with Bull)* | Golden Joker; Cloud 9; Golden Ticket *(with Bull)* | Vagabond commitment | The Hermit; Temperance | — | Immolate | — |
| Cash Hoard / Interest | ↳ Bootstraps Cash-to-Mult `[L]` | Bootstraps | Rocket; To the Moon; Blueprint; Brainstorm *(with Bootstraps)* | Golden Joker; Cloud 9; Golden Ticket *(with Bootstraps)* | Vagabond commitment | The Hermit; Temperance | — | Immolate | — |
| Cash Hoard / Interest | ↳ Bull + Bootstraps Cash Scoring `[L]` | Bull; Bootstraps *(when paired)* | Rocket; To the Moon *(with pair)* | — | Vagabond commitment | The Hermit; Temperance | — | Immolate | — |
| Cash Hoard / Interest | ↳ Cloud 9 Nines Economy `[L]` | Cloud 9 | DNA; Hologram *(with Cloud 9)* | — | Vagabond commitment | — | — | Ouija | Nines |
| Campfire Sell-Scaling | Campfire Sell-Scaling `[L]` | Campfire | Gift Card; Egg; Riff-Raff; Blueprint; Brainstorm *(with Campfire)* | Cartomancer; Hallucination; Perkeo *(with Campfire)* | — | Temperance | — | — | — |
| Flash Card Reroll-Scaling | Flash Card Reroll-Scaling `[L]` | Flash Card; Chaos the Clown *(with Flash Card)* | Blueprint; Brainstorm *(with Flash Card)* | Rocket; To the Moon *(with Flash Card)* | — | — | — | — | — |
| Red Card Pack-Skip Scaling | Red Card Pack-Skip Scaling `[L]` | Red Card | Hallucination; Blueprint; Brainstorm *(with Red Card)* | Fortune Teller *(with Red Card)* | — | — | — | — | — |
| Throwback Blind-Skip Scaling | Throwback Blind-Skip Scaling `[L]` | Throwback | Diet Cola; Blueprint; Brainstorm *(with Throwback)* | Red Card *(with Throwback)* | — | — | — | — | — |

## 10. Joker board

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Joker Stencil | Joker Stencil / Ankh / Invisible Duplication `[L]` | Joker Stencil | Invisible Joker; Blueprint; Brainstorm *(with Stencil)* | Negative Jokers | Riff-Raff *(fills empty slots)* | — | — | Ankh | — |
| Baseball Card Uncommon Stack | Baseball Card Uncommon Stack `[L]` | Baseball Card | Owned/candidate Uncommon Jokers; Showman; Blueprint; Brainstorm *(with Baseball Card)* | — | — | Judgement | — | Wraith; The Soul | — |
| Abstract Joker Wide-Board | Abstract Joker Wide-Board `[L]` | Abstract Joker | Riff-Raff; Blueprint; Brainstorm *(with Abstract)* | Showman; Invisible Joker *(with Abstract)* | — | Judgement | — | Wraith; The Soul | — |
| Swashbuckler Sell-Value Stack | Egg / Gift-Card Swashbuckler `[L]` | Swashbuckler; Egg; Gift Card *(with Swashbuckler)* | Blueprint; Brainstorm *(with Swashbuckler)* | Riff-Raff; Invisible Joker *(with Swashbuckler)* | — | Judgement | — | Wraith; The Soul | — |

## 11. Discard and hand rotation

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Discard Utilization | Discard Utilization `[I]` | — | — | — | No-discard commitments | — | — | Medium | — |
| Discard Utilization | ↳ Castle Suit-Discard Scaling `[L]` | Castle | Merry Andy; Drunkard; Smeared Joker; Blueprint; Brainstorm *(with Castle)* | — | No-discard commitments | The Star; The Moon; The Sun; The World | — | Sigil | Wild |
| Discard Utilization | ↳ Mail-In Rebate Rank-Discard Economy `[L]` | Mail-In Rebate | Merry Andy; Drunkard; Blueprint; Brainstorm *(with Rebate)* | Trading Card *(with Rebate)* | No-discard commitments | Strength; Death | — | Ouija | — |
| Discard Utilization | ↳ Yorick Discard-Scaling `[L]` | Yorick | Merry Andy; Drunkard; Blueprint; Brainstorm *(with Yorick)* | Certificate *(with Yorick)* | No-discard commitments | — | — | Medium | — |
| No-Discard / Discard-Preservation | No-Discard / Discard-Preservation `[I]` | — | — | — | Discard-engine commitments | — | — | — | — |
| No-Discard / Discard-Preservation | ↳ Green Joker No-Discard Scaling `[L]` | Green Joker; Burglar *(paired)* | Banner; Delayed Gratification; Ramen *(with Green Joker)* | — | Trading Card; Castle; Mail-In Rebate; Yorick *(with Green Joker)* | — | — | — | — |
| No-Discard / Discard-Preservation | ↳ Banner + Delayed Gratification Discard Reserve `[L]` | Banner; Delayed Gratification | Burglar; Green Joker; Ramen *(with reserve core)* | — | Trading Card; Castle; Mail-In Rebate; Yorick *(with reserve core)* | — | — | — | — |
| No-Discard / Discard-Preservation | ↳ Ramen Preservation `[L]` | Ramen; Burglar *(paired)* | Green Joker; Banner; Delayed Gratification *(with Ramen)* | — | Trading Card; Castle; Mail-In Rebate; Yorick *(with Ramen)* | — | — | — | — |
| No-Discard / Discard-Preservation | ↳ Burglar Zero-Discard / Extra-Hand `[L]` | Burglar | Green Joker; Banner; Delayed Gratification; Ramen *(with Burglar)* | — | Trading Card; Castle; Mail-In Rebate; Yorick *(with Burglar)* | — | — | — | — |
| Obelisk Hand-Rotation | Obelisk Hand-Rotation `[L]` | Obelisk | Blueprint; Brainstorm *(with Obelisk)* | — | A committed currently-most-played hand route | — | — | — | — |
| Burnt Joker Hand-Level Engine | Burnt Joker Hand-Level Engine `[L]` | Burnt Joker | Astronomer; Space Joker; Certificate; Blueprint; Brainstorm *(with Burnt Joker)* | Merry Andy; Drunkard *(with Burnt Joker)* | — | — | Any | Black Hole | — |

## 12. Hand scheduling

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Last-Hand Burst | Last-Hand Burst `[I]` | — | — | — | — | — | — | — | — |
| Last-Hand Burst | ↳ Acrobat Last-Hand XMult `[L]` | Acrobat | Blueprint; Brainstorm *(with Acrobat)* | Loyalty Card; Burglar *(with Acrobat)* | — | — | — | — | — |
| Last-Hand Burst | ↳ Dusk Last-Hand Retrigger `[L]` | Dusk | Hanging Chad; Seltzer; Splash; Blueprint; Brainstorm *(with Dusk)* | Sock and Buskin; Hack; Hiker *(with Dusk)* | — | — | — | — | — |
| Loyalty Card Six-Hand Cycle | Loyalty Card Six-Hand Cycle `[L]` | Loyalty Card | Blueprint; Brainstorm *(with Loyalty Card)* | Burglar; Acrobat *(with Loyalty Card)* | — | — | — | — | — |
