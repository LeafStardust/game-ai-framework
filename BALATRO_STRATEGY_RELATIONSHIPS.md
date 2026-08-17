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

`[I]` rows contain only generic evidence shared by every specialization under that indexed strategy. `[L]` rows contain only additional evidence specific to that specialization. This factoring rule applies to every column: Gold, Silver, Bronze, Banned, Tarot, Planet, Spectral, and Enhancement.

A component must not be duplicated between a parent and child row. If it is specific to one specialization, it belongs only on that specialization.

## 1. Poker hands

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|
| High Card `[I]` | Burnt Joker | Card Sharp; Supernova; Space Joker; Half Joker; Green Joker; Burglar | — | Obelisk | — | Pluto | — | — |
| Stuntman / Small-Hand High Card `[L]` | Stuntman | — | — | — | — | — | — | — |
| Baron-Mime Steel-King High Card `[L]` | Baron; Mime | Blackboard; Shoot the Moon; Troubadour; Juggler | Raised Fist; Reserved Parking | Stuntman | The Chariot | — | — | Steel |
| Pair `[L]` | The Duo | Jolly Joker; Sly Joker | — | Obelisk | — | Mercury | — | — |
| Two Pair `[I]` | — | Mad Joker; Clever Joker | — | Obelisk | — | Uranus | — | — |
| Spare Trousers + Square Joker Two Pair `[L]` | Spare Trousers | Square Joker | — | — | — | — | — | — |
| Three of a Kind `[I]` | TBD | TBD | TBD | TBD | TBD | Venus | TBD | TBD |
| DNA / Cryptid Rank-Copy Three of a Kind `[L]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid | TBD |
| Straight `[I]` | TBD | TBD | TBD | TBD | TBD | Saturn | TBD | TBD |
| Shortcut / Four Fingers Straight `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Runner Scaling Straight `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Superposition Ace-Straight Tarot `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Flush `[I]` | TBD | TBD | TBD | TBD | TBD | Jupiter | TBD | TBD |
| Smeared / Four Fingers Consistency Flush `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Full House `[L]` | TBD | TBD | TBD | TBD | TBD | Earth | TBD | TBD |
| Four of a Kind `[I]` | TBD | TBD | TBD | TBD | TBD | Mars | TBD | TBD |
| DNA / Cryptid Rank-Copy Four of a Kind `[L]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid | TBD |
| Straight Flush `[I]` | TBD | TBD | TBD | TBD | TBD | Neptune | TBD | TBD |
| Shortcut / Four Fingers / Smeared Straight Flush `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Seance Straight-Flush Spectral Engine `[L]` | TBD | TBD | TBD | TBD | — | — | TBD | TBD |
| Five of a Kind `[I]` | TBD | TBD | TBD | TBD | TBD | Planet X | TBD | TBD |
| DNA / Cryptid Rank-Copy Five of a Kind `[L]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid | TBD |
| Flush House `[L]` | TBD | TBD | TBD | TBD | TBD | Ceres | TBD | TBD |
| Flush Five `[I]` | TBD | TBD | TBD | TBD | TBD | Eris | TBD | TBD |
| DNA / Cryptid Exact-Card Flush Five `[L]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid | TBD |
| The Idol Monoculture Flush Five `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Four-Card Hand Spam `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Square Joker Four-Card Chips `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Square + Green Joker Four-Card Spam `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## 2. Rank and face cards

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|
| Aces `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Scholar Ace Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| DNA + Scholar Ace Concentration `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Cryptid | TBD |
| Low-Rank Scoring `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Fibonacci Low-Rank Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Hack + Fibonacci Retrigger `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Twos `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Wee Joker Twos `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Wee Joker + Hack Retrigger Twos `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Sixes / Sixth Sense `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Jacks / Hit the Road `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Queens / Shoot the Moon `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Face Cards `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Photograph + Hanging Chad `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Triboulet + Sock and Buskin `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Pareidolia Universal Face Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Familiar | TBD |
| Held Face-Card Economy `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Business Card Face Economy `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Faceless / No-Face `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Ride the Bus No-Face Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Faceless Joker Discard Economy `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| The Idol Exact-Card Concentration `[L]` | TBD | TBD | TBD | TBD | Death | TBD | Cryptid | TBD |

## 3. Suits and held cards

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|
| Hearts `[I]` | TBD | TBD | TBD | TBD | The Sun | TBD | Sigil | Wild |
| Bloodstone + Oops! All 6s Hearts `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Bloodstone Retrigger Hearts `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Diamonds `[I]` | TBD | TBD | TBD | TBD | The Star | TBD | Sigil | Wild |
| Rough Gem Diamond Economy / Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Clubs `[I]` | TBD | TBD | TBD | TBD | The Moon | TBD | Sigil | Wild |
| Onyx Agate / Seeing Double Clubs `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Spades `[I]` | TBD | TBD | TBD | TBD | The World | TBD | Sigil | Wild |
| Arrowhead Spade Chips `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Blackboard Held-Black Cards `[L]` | TBD | TBD | TBD | TBD | The Moon; The World | TBD | Sigil | TBD |
| Ancient Joker Suit-Rotation `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | Sigil | Wild |
| Ancient + Smeared Suit-Rotation `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Flower Pot Multi-Suit `[I]` | TBD | TBD | TBD | TBD | The Star; The Moon; The Sun; The World | TBD | Sigil | Wild |
| Splash + Flower Pot `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Smeared Joker + Flower Pot `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Smeared + Splash + Flower Pot `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## 4. Enhancements

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|
| Stone `[I]` | TBD | TBD | TBD | TBD | The Tower | TBD | TBD | Stone |
| Marble Joker + Stone Joker Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Marble Joker + Vampire Stone Feed `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| DNA + Stone Joker Duplication `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Cryptid | TBD |
| Stone High Card `[L]` | TBD | TBD | TBD | TBD | TBD | Pluto | TBD | TBD |
| Glass `[I]` | TBD | TBD | TBD | TBD | Justice | TBD | TBD | Glass |
| Glass Joker Breakage Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Glass Retrigger Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Cryptid | TBD |
| Steel `[I]` | TBD | TBD | TBD | TBD | The Chariot | TBD | TBD | Steel |
| Steel Joker Density Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Mime Steel Retrigger `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Deja Vu | TBD |
| Lucky `[I]` | TBD | TBD | TBD | TBD | The Magician | TBD | TBD | Lucky |
| Lucky Cat Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Lucky Cat + Oops! All 6s `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Lucky Retrigger `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Deja Vu | TBD |
| Gold Cards `[I]` | TBD | TBD | TBD | TBD | The Devil | TBD | Talisman | Gold |
| Held Gold + Mime Economy `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Deja Vu | TBD |
| Golden Ticket Gold Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Midas Mask Gold Generation `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Midas Mask + Golden Ticket Economy `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## 5. Seals

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|
| Red Seal `[I]` | TBD | TBD | TBD | TBD | — | — | Deja Vu | — |
| Played Red-Seal Retrigger `[L]` | TBD | TBD | TBD | TBD | — | — | TBD | — |
| Held Red-Seal Retrigger `[L]` | TBD | TBD | TBD | TBD | — | — | TBD | — |
| Blue Seal Hand-Level Scaling `[L]` | TBD | TBD | TBD | TBD | — | — | Trance | — |
| Purple Seal Tarot Engine `[L]` | TBD | TBD | TBD | TBD | — | — | Medium | — |
| Gold Seal Economy `[I]` | TBD | TBD | TBD | TBD | — | — | Talisman | — |
| Gold-Seal Retrigger Economy `[L]` | TBD | TBD | TBD | TBD | — | — | Deja Vu | — |

## 6. Destruction, sacrifice, consumption, thinning

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|
| Canio Destruction `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Trading Card Canio `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Pareidolia Canio `[L]` | TBD | TBD | TBD | TBD | TBD | — | Familiar | TBD |
| Glass Canio `[L]` | TBD | TBD | TBD | TBD | Justice | — | Familiar | Glass |
| Consumable Canio `[L]` | TBD | TBD | TBD | TBD | The Hanged Man | — | Immolate | TBD |
| Vampire `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Midas Mask + Vampire `[L]` | TBD | TBD | TBD | TBD | The Devil | — | TBD | Gold |
| Pareidolia + Midas Mask + Vampire `[L]` | TBD | TBD | TBD | TBD | The Devil | — | Familiar | Gold |
| Ceremonial Dagger Sacrifice `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Riff-Raff / Disposable-Joker Dagger Feed `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Madness Destruction `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Solo Madness `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Eternal-Joker Madness `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Deck Thinning `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Trading Card Thinning / Economy `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Erosion Thinning `[L]` | TBD | TBD | TBD | TBD | The Hanged Man | — | Immolate | TBD |
| Trading Card + Erosion `[L]` | TBD | TBD | TBD | TBD | The Hanged Man | — | Immolate | TBD |

## 7. Deck growth and card training

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|
| Hologram Deck-Growth `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| DNA + Hologram `[L]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid | TBD |
| Certificate + Hologram `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Marble Joker + Hologram `[L]` | TBD | TBD | TBD | TBD | The Tower | — | TBD | Stone |
| Hiker Card Training `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Hiker Retrigger / Copy Training `[L]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid; Deja Vu | TBD |
| Driver's License Enhancement-Density `[L]` | TBD | TBD | TBD | TBD | The Magician; The Empress; The Hierophant; The Lovers; The Chariot; Justice; The Devil; The Tower | — | Familiar; Grim; Incantation | Any |
| Blue Joker Large-Deck Chips `[L]` | TBD | TBD | TBD | TBD | TBD | — | Familiar; Grim; Incantation; Cryptid | TBD |

## 8. Planet, Tarot, consumable engines

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|
| Planet Engine `[I]` | TBD | TBD | TBD | TBD | The High Priestess | Any | Black Hole | — |
| Constellation Planet-Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | — |
| Satellite Planet-Economy `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | — |
| Constellation + Satellite Planet Engine `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | — |
| Perkeo Consumable Duplication `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Perkeo + Observatory Planet Stack `[L]` | TBD | TBD | TBD | TBD | — | TBD | — | — |
| Perkeo + Cryptid Copy Engine `[L]` | TBD | TBD | TBD | TBD | — | — | Cryptid | — |
| Perkeo Tarot / Spectral Engine `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Fortune Teller Tarot-Use Scaling `[L]` | TBD | TBD | TBD | TBD | Any | — | — | — |
| Vagabond Low-Money Tarot Engine `[L]` | TBD | TBD | TBD | TBD | Any | — | — | — |

## 9. Economy, shop, reroll, blind skip

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|
| Cash Hoard / Interest `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Rocket / To the Moon Cash Growth `[L]` | TBD | TBD | TBD | TBD | The Hermit; Temperance | — | Immolate | TBD |
| Bull Cash-to-Chips `[L]` | TBD | TBD | TBD | TBD | The Hermit; Temperance | — | Immolate | TBD |
| Bootstraps Cash-to-Mult `[L]` | TBD | TBD | TBD | TBD | The Hermit; Temperance | — | Immolate | TBD |
| Bull + Bootstraps Cash Scoring `[L]` | TBD | TBD | TBD | TBD | The Hermit; Temperance | — | Immolate | TBD |
| Cloud 9 Nines Economy `[L]` | TBD | TBD | TBD | TBD | TBD | — | Ouija | TBD |
| Campfire Sell-Scaling `[L]` | TBD | TBD | TBD | TBD | Temperance | — | TBD | TBD |
| Flash Card Reroll-Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Red Card Pack-Skip Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Throwback Blind-Skip Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |

## 10. Joker board

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|
| Joker Stencil `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Joker Stencil + Ankh / Invisible Duplication `[L]` | TBD | TBD | TBD | TBD | — | — | Ankh | TBD |
| Baseball Card Uncommon Stack `[L]` | TBD | TBD | TBD | TBD | Judgement | — | Wraith; The Soul | TBD |
| Abstract Joker Wide-Board `[L]` | TBD | TBD | TBD | TBD | Judgement | — | Wraith; The Soul | TBD |
| Swashbuckler Sell-Value Stack `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD |
| Egg / Gift-Card Swashbuckler `[L]` | TBD | TBD | TBD | TBD | Judgement | — | Wraith; The Soul | TBD |

## 11. Discard and hand rotation

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|
| Discard Utilization `[I]` | TBD | TBD | TBD | TBD | — | — | TBD | — |
| Castle Suit-Discard Scaling `[L]` | TBD | TBD | TBD | TBD | The Star; The Moon; The Sun; The World | — | Sigil | Wild |
| Mail-In Rebate Rank-Discard Economy `[L]` | TBD | TBD | TBD | TBD | Strength; Death | — | Ouija | — |
| Yorick Discard-Scaling `[L]` | TBD | TBD | TBD | TBD | — | — | Medium | — |
| No-Discard / Discard-Preservation `[I]` | TBD | TBD | TBD | TBD | — | — | — | — |
| Green Joker No-Discard Scaling `[L]` | TBD | TBD | TBD | TBD | — | — | — | — |
| Banner + Delayed Gratification Discard Reserve `[L]` | TBD | TBD | TBD | TBD | — | — | — | — |
| Ramen Preservation `[L]` | TBD | TBD | TBD | TBD | — | — | — | — |
| Burglar Zero-Discard / Extra-Hand `[L]` | TBD | TBD | TBD | TBD | — | — | — | — |
| Obelisk Hand-Rotation `[L]` | TBD | TBD | TBD | TBD | — | — | — | — |
| Burnt Joker Hand-Level Engine `[L]` | TBD | TBD | TBD | TBD | — | Any | Black Hole | — |

## 12. Hand scheduling

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement |
|---|---|---|---|---|---|---|---|---|
| Last-Hand Burst `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Acrobat Last-Hand XMult `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Dusk Last-Hand Retrigger `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
