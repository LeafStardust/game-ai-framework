# Balatro Strategy Relationships

Development reference for [`BALATRO_STRATEGY_TREE.md`](BALATRO_STRATEGY_TREE.md).

## Evidence weights

| Evidence | Score |
|---|---:|
| Gold Joker | +5.00 |
| Silver Joker | +3.00 |
| Bronze Joker | +1.00 |
| Banned component | -8.00 |
| Matching Planet / permanent hand level gained | +0.50 per level |
| Strategy-directed Tarot use | +0.30 per use |
| Strategy-directed Spectral use | +0.50 per use |
| Matching enhancement in current deck | +0.35 per card |

`TBD` = not audited yet. `—` = intentionally none.

`Branch` is the top-level strategy branch. `Node` is the exact strategy node. `[I]` nodes have specialized descendants; `[L]` nodes have none.

An `[I]` node contains only evidence shared by every specialization beneath it. A child row contains only additional evidence specific to that child. This factoring rule applies to Gold, Silver, Bronze, Banned, Tarot, Planet, Spectral, and Enhancement.

A component must not be duplicated between a parent and child row. If it is specific to one specialization, it belongs only on that specialization.

## 1. Poker hands

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| High Card | High Card `[I]` | Burnt Joker | Card Sharp; Supernova; Space Joker; Half Joker; Green Joker; Burglar | — | Obelisk | The Chariot | Pluto | — | Steel |
| High Card | ↳ Stuntman / Small-Hand High Card `[L]` | Stuntman | — | — | — | — | — | — | — |
| High Card | ↳ Baron-Mime Steel-King High Card `[L]` | Baron; Mime | Blackboard; Shoot the Moon; Troubadour; Juggler | Raised Fist; Reserved Parking | Stuntman | — | — | — | — |
| Pair | Pair `[L]` | The Duo | Jolly Joker; Sly Joker; Half Joker | — | Obelisk | — | Mercury | — | — |
| Two Pair | Two Pair `[L]` | Spare Trousers | Mad Joker; Clever Joker; Square Joker; The Duo | Jolly Joker; Sly Joker | Obelisk | Death; Strength | Uranus | — | — |
| Three of a Kind | Three of a Kind `[L]` | The Trio | Zany Joker; Wily Joker; DNA; Half Joker; The Duo | Jolly Joker; Sly Joker; Trading Card | Obelisk | Death; Strength | Venus | Cryptid; Ouija | — |
| Straight | Straight `[L]` | The Order; Shortcut; Four Fingers; Runner; Superposition | Crazy Joker; Devious Joker | — | Obelisk | Strength; Death | Saturn | — | — |
| Straight Flush | Straight Flush `[L]` | The Order; The Tribe; Shortcut; Four Fingers; Runner; Smeared Joker; Seance | Crazy Joker; Devious Joker; Droll Joker; Crafty Joker | — | Obelisk | Strength; Death; The Lovers | Neptune | Sigil | Wild |
| Flush | Flush `[L]` | The Tribe | Droll Joker; Crafty Joker; Smeared Joker; Four Fingers | — | Obelisk | The Lovers | Jupiter | Sigil | Wild |
| Full House | Full House `[L]` | — | The Trio; The Duo; Spare Trousers; Zany Joker; Wily Joker; Mad Joker; Clever Joker | Jolly Joker; Sly Joker; DNA; Trading Card | Obelisk | Death; Strength | Earth | Cryptid; Ouija | — |
| Flush House | Flush House `[L]` | The Tribe | The Trio; The Duo; Spare Trousers; Zany Joker; Wily Joker; Mad Joker; Clever Joker; Smeared Joker; Droll Joker; Crafty Joker | Jolly Joker; Sly Joker; DNA; Trading Card | Obelisk | Death; Strength; The Lovers | Ceres | Cryptid; Ouija; Sigil | Wild |
| Four of a Kind | Four of a Kind `[L]` | The Family | The Trio; DNA; Zany Joker; Wily Joker; Square Joker | The Duo; Jolly Joker; Sly Joker; Trading Card | Obelisk | Death; Strength | Mars | Cryptid; Ouija | — |
| Five of a Kind | Five of a Kind `[L]` | The Family | The Trio; DNA; The Idol; Zany Joker; Wily Joker | The Duo; Jolly Joker; Sly Joker; Trading Card | Obelisk | Death; Strength | Planet X | Cryptid; Ouija | — |
| Flush Five | Flush Five `[L]` | The Family; DNA; The Idol; The Tribe | The Trio; Zany Joker; Wily Joker; Smeared Joker; Droll Joker; Crafty Joker | The Duo; Jolly Joker; Sly Joker; Trading Card | Obelisk | Death; Strength; The Lovers | Eris | Cryptid; Ouija; Sigil | Wild |

## 2. Rank and face cards

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Aces | Aces `[L]` | Scholar | DNA *(with Ace commitment)*; Fibonacci *(with Ace commitment)*; Odd Todd *(with Ace commitment)* | The Idol *(Ace target + concentration)* | — | Death; Strength; The Hanged Man | — | Grim; Cryptid | — |
| Low-Rank Scoring | Low-Rank Scoring `[L]` | Fibonacci; Hack | Odd Todd; Even Steven | Walkie Talkie | — | Death; Strength; The Hanged Man | — | Incantation; Cryptid | — |
| Twos | Twos / Wee-Hack `[L]` | Wee Joker | Hack *(with Two commitment)*; Fibonacci *(with Two commitment)*; Even Steven *(with Two commitment)* | DNA *(with Two commitment)*; Hologram *(with Two commitment)*; The Idol *(Two target + concentration)* | — | Death; Strength; The Hanged Man | — | Cryptid | — |
| Sixes / Sixth Sense | Sixes / Sixth Sense `[L]` | Sixth Sense | Even Steven *(with Six commitment)* | — | — | Death; Strength | — | — | — |
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
| Hearts | Hearts `[I]` | TBD | TBD | TBD | TBD | The Sun | TBD | Sigil | Wild |
| Hearts | ↳ Bloodstone + Oops! All 6s Hearts `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Hearts | ↳ Bloodstone Retrigger Hearts `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Diamonds | Diamonds `[I]` | TBD | TBD | TBD | TBD | The Star | TBD | Sigil | Wild |
| Diamonds | ↳ Rough Gem Diamond Economy / Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Clubs | Clubs `[I]` | TBD | TBD | TBD | TBD | The Moon | TBD | Sigil | Wild |
| Clubs | ↳ Onyx Agate / Seeing Double Clubs `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Spades | Spades `[I]` | TBD | TBD | TBD | TBD | The World | TBD | Sigil | Wild |
| Spades | ↳ Arrowhead Spade Chips `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Blackboard Held-Black Cards | Blackboard Held-Black Cards `[L]` | TBD | TBD | TBD | TBD | The Moon; The World | TBD | Sigil | TBD |
| Ancient Joker Suit-Rotation | Ancient Joker Suit-Rotation `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | Sigil | Wild |
| Ancient Joker Suit-Rotation | ↳ Ancient + Smeared Suit-Rotation `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Flower Pot Multi-Suit | Flower Pot Multi-Suit `[I]` | TBD | TBD | TBD | TBD | The Star; The Moon; The Sun; The World | TBD | Sigil | Wild |
| Flower Pot Multi-Suit | ↳ Splash + Flower Pot `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Wild |
| Flower Pot Multi-Suit | ↳ Smeared Joker + Flower Pot `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Wild |
| Flower Pot Multi-Suit | ↳ Smeared + Splash + Flower Pot `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Wild |

## 4. Enhancements

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Stone | Stone `[I]` | TBD | TBD | TBD | TBD | The Tower | TBD | TBD | Stone |
| Stone | ↳ Marble Joker + Stone Joker Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Stone | ↳ Marble Joker + Vampire Stone Feed `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Stone | ↳ DNA + Stone Joker Duplication `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Cryptid | TBD |
| Stone | ↳ Stone High Card `[L]` | TBD | TBD | TBD | TBD | TBD | Pluto | TBD | TBD |
| Glass | Glass `[I]` | TBD | TBD | TBD | TBD | Justice | TBD | TBD | Glass |
| Glass | ↳ Glass Joker Breakage Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Glass | ↳ Glass Retrigger Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Cryptid | TBD |
| Steel | Steel `[I]` | TBD | TBD | TBD | TBD | The Chariot | TBD | TBD | Steel |
| Steel | ↳ Steel Joker Density Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Steel | ↳ Mime Steel Retrigger `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Deja Vu | TBD |
| Lucky | Lucky `[I]` | TBD | TBD | TBD | TBD | The Magician | TBD | TBD | Lucky |
| Lucky | ↳ Lucky Cat Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Lucky | ↳ Lucky Cat + Oops! All 6s `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Lucky | ↳ Lucky Retrigger `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Deja Vu | TBD |
| Gold Cards | Gold Cards `[I]` | TBD | TBD | TBD | TBD | The Devil | TBD | Talisman | Gold |
| Gold Cards | ↳ Held Gold + Mime Economy `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Deja Vu | TBD |
| Gold Cards | ↳ Golden Ticket Gold Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Gold Cards | ↳ Midas Mask Gold Generation `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Gold Cards | ↳ Midas Mask + Golden Ticket Economy `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## 5. Seals

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Red Seal | Red Seal `[I]` | TBD | TBD | TBD | TBD | — | — | Deja Vu | — |
| Red Seal | ↳ Played Red-Seal Retrigger `[L]` | TBD | TBD | TBD | TBD | — | — | TBD | — |
| Red Seal | ↳ Held Red-Seal Retrigger `[L]` | TBD | TBD | TBD | TBD | — | — | TBD | — |
| Blue Seal Hand-Level Scaling | Blue Seal Hand-Level Scaling `[L]` | TBD | TBD | TBD | TBD | — | — | Trance | — |
| Purple Seal Tarot Engine | Purple Seal Tarot Engine `[L]` | TBD | TBD | TBD | TBD | — | — | Medium | — |
| Gold Seal Economy | Gold Seal Economy `[I]` | TBD | TBD | TBD | TBD | — | — | Talisman | — |
| Gold Seal Economy | ↳ Gold-Seal Retrigger Economy `[L]` | TBD | TBD | TBD | TBD | — | — | Deja Vu | — |

## 6. Destruction, sacrifice, consumption, thinning

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Canio Destruction | Canio Destruction `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Canio Destruction | ↳ Trading Card Canio `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Canio Destruction | ↳ Pareidolia Canio `[L]` | TBD | TBD | TBD | TBD | TBD | — | Familiar | TBD |
| Canio Destruction | ↳ Glass Canio `[L]` | TBD | TBD | TBD | TBD | Justice | — | Familiar | Glass |
| Canio Destruction | ↳ Consumable Canio `[L]` | TBD | TBD | TBD | TBD | The Hanged Man | — | Immolate | TBD |
| Vampire | Vampire `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Vampire | ↳ Midas Mask + Vampire `[L]` | TBD | TBD | TBD | TBD | The Devil | — | TBD | Gold |
| Vampire | ↳ Pareidolia + Midas Mask + Vampire `[L]` | TBD | TBD | TBD | TBD | The Devil | — | Familiar | Gold |
| Ceremonial Dagger Sacrifice | Ceremonial Dagger Sacrifice `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Ceremonial Dagger Sacrifice | ↳ Riff-Raff / Disposable-Joker Dagger Feed `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Madness Destruction | Madness Destruction `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Madness Destruction | ↳ Solo Madness `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Madness Destruction | ↳ Eternal-Joker Madness `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Deck Thinning | Deck Thinning `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Deck Thinning | ↳ Trading Card Thinning / Economy `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Deck Thinning | ↳ Erosion Thinning `[L]` | TBD | TBD | TBD | TBD | The Hanged Man | — | Immolate | TBD |
| Deck Thinning | ↳ Trading Card + Erosion `[L]` | TBD | TBD | TBD | TBD | The Hanged Man | — | Immolate | TBD |

## 7. Deck growth and card training

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Hologram Deck-Growth | Hologram Deck-Growth `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Hologram Deck-Growth | ↳ DNA + Hologram `[L]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid | TBD |
| Hologram Deck-Growth | ↳ Certificate + Hologram `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Hologram Deck-Growth | ↳ Marble Joker + Hologram `[L]` | TBD | TBD | TBD | TBD | The Tower | — | TBD | Stone |
| Hiker Card Training | Hiker Card Training `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Hiker Card Training | ↳ Hiker Retrigger / Copy Training `[L]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid; Deja Vu | TBD |
| Driver's License Enhancement-Density | Driver's License Enhancement-Density `[L]` | TBD | TBD | TBD | TBD | The Magician; The Empress; The Hierophant; The Lovers; The Chariot; Justice; The Devil; The Tower | — | Familiar; Grim; Incantation | Any |
| Blue Joker Large-Deck Chips | Blue Joker Large-Deck Chips `[L]` | TBD | TBD | TBD | TBD | TBD | — | Familiar; Grim; Incantation; Cryptid | TBD |

## 8. Planet, Tarot, consumable engines

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Planet Engine | Planet Engine `[I]` | TBD | TBD | TBD | TBD | The High Priestess | Any | Black Hole | — |
| Planet Engine | ↳ Constellation Planet-Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | — |
| Planet Engine | ↳ Satellite Planet-Economy `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | — |
| Planet Engine | ↳ Constellation + Satellite Planet Engine `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | — |
| Perkeo Consumable Duplication | Perkeo Consumable Duplication `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Perkeo Consumable Duplication | ↳ Perkeo + Observatory Planet Stack `[L]` | TBD | TBD | TBD | TBD | — | TBD | — | — |
| Perkeo Consumable Duplication | ↳ Perkeo + Cryptid Copy Engine `[L]` | TBD | TBD | TBD | TBD | — | — | Cryptid | — |
| Perkeo Consumable Duplication | ↳ Perkeo Tarot / Spectral Engine `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Fortune Teller Tarot-Use Scaling | Fortune Teller Tarot-Use Scaling `[L]` | TBD | TBD | TBD | TBD | Any | — | — | — |
| Vagabond Low-Money Tarot Engine | Vagabond Low-Money Tarot Engine `[L]` | TBD | TBD | TBD | TBD | Any | — | — | — |

## 9. Economy, shop, reroll, blind skip

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Cash Hoard / Interest | Cash Hoard / Interest `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Cash Hoard / Interest | ↳ Rocket / To the Moon Cash Growth `[L]` | TBD | TBD | TBD | TBD | The Hermit; Temperance | — | Immolate | TBD |
| Cash Hoard / Interest | ↳ Bull Cash-to-Chips `[L]` | TBD | TBD | TBD | TBD | The Hermit; Temperance | — | Immolate | TBD |
| Cash Hoard / Interest | ↳ Bootstraps Cash-to-Mult `[L]` | TBD | TBD | TBD | TBD | The Hermit; Temperance | — | Immolate | TBD |
| Cash Hoard / Interest | ↳ Bull + Bootstraps Cash Scoring `[L]` | TBD | TBD | TBD | TBD | The Hermit; Temperance | — | Immolate | TBD |
| Cash Hoard / Interest | ↳ Cloud 9 Nines Economy `[L]` | TBD | TBD | TBD | TBD | TBD | — | Ouija | TBD |
| Campfire Sell-Scaling | Campfire Sell-Scaling `[L]` | TBD | TBD | TBD | TBD | Temperance | — | TBD | TBD |
| Flash Card Reroll-Scaling | Flash Card Reroll-Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Red Card Pack-Skip Scaling | Red Card Pack-Skip Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Throwback Blind-Skip Scaling | Throwback Blind-Skip Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |

## 10. Joker board

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Joker Stencil | Joker Stencil `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Joker Stencil | ↳ Joker Stencil + Ankh / Invisible Duplication `[L]` | TBD | TBD | TBD | TBD | — | — | Ankh | TBD |
| Baseball Card Uncommon Stack | Baseball Card Uncommon Stack `[L]` | TBD | TBD | TBD | TBD | Judgement | — | Wraith; The Soul | TBD |
| Abstract Joker Wide-Board | Abstract Joker Wide-Board `[L]` | TBD | TBD | TBD | TBD | Judgement | — | Wraith; The Soul | TBD |
| Swashbuckler Sell-Value Stack | Swashbuckler Sell-Value Stack `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Swashbuckler Sell-Value Stack | ↳ Egg / Gift-Card Swashbuckler `[L]` | TBD | TBD | TBD | TBD | Judgement | — | Wraith; The Soul | TBD |

## 11. Discard and hand rotation

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Discard Utilization | Discard Utilization `[I]` | TBD | TBD | TBD | TBD | — | — | TBD | — |
| Discard Utilization | ↳ Castle Suit-Discard Scaling `[L]` | TBD | TBD | TBD | TBD | The Star; The Moon; The Sun; The World | — | Sigil | Wild |
| Discard Utilization | ↳ Mail-In Rebate Rank-Discard Economy `[L]` | TBD | TBD | TBD | TBD | Strength; Death | — | Ouija | — |
| Discard Utilization | ↳ Yorick Discard-Scaling `[L]` | TBD | TBD | TBD | TBD | — | — | Medium | — |
| No-Discard / Discard-Preservation | No-Discard / Discard-Preservation `[I]` | TBD | TBD | TBD | TBD | — | — | — | — |
| No-Discard / Discard-Preservation | ↳ Green Joker No-Discard Scaling `[L]` | TBD | TBD | TBD | TBD | — | — | — | — |
| No-Discard / Discard-Preservation | ↳ Banner + Delayed Gratification Discard Reserve `[L]` | TBD | TBD | TBD | TBD | — | — | — | — |
| No-Discard / Discard-Preservation | ↳ Ramen Preservation `[L]` | TBD | TBD | TBD | TBD | — | — | — | — |
| No-Discard / Discard-Preservation | ↳ Burglar Zero-Discard / Extra-Hand `[L]` | TBD | TBD | TBD | TBD | — | — | — | — |
| Obelisk Hand-Rotation | Obelisk Hand-Rotation `[L]` | TBD | TBD | TBD | TBD | — | — | — | — |
| Burnt Joker Hand-Level Engine | Burnt Joker Hand-Level Engine `[L]` | TBD | TBD | TBD | TBD | — | Any | Black Hole | — |

## 12. Hand scheduling

| Branch | Node | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|---|
| Last-Hand Burst | Last-Hand Burst `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Last-Hand Burst | ↳ Acrobat Last-Hand XMult `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Last-Hand Burst | ↳ Dusk Last-Hand Retrigger `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
