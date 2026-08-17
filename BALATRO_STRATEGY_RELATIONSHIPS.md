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
| Matching seal in current deck | +0.40 per card |

`TBD` = not audited yet. `—` = intentionally none. `[condition]` is an inline runtime condition. Internal nodes own shared evidence inherited by descendants.

A component may appear on multiple strategy rows only when the mechanical requirements are distinct. Otherwise one node owns it.

## 1. Poker hands

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement | Seal |
|---|---|---|---|---|---|---|---|---|---|
| High Card `[I]` | — | — | — | — | — | Pluto | — | — | — |
| Repetition / Level High Card `[L]` | Burnt Joker | Card Sharp; Supernova; Space Joker; Half Joker; Green Joker; Burglar | — | Obelisk[most-played=High Card] | — | — | — | — | — |
| Stuntman / Small-Hand High Card `[L]` | Stuntman | — | — | — | — | — | — | — | — |
| Baron-Mime Steel-King High Card `[L]` | Baron; Mime | Blackboard; Shoot the Moon; Troubadour; Juggler | Raised Fist; Reserved Parking | Stuntman[material held engine] | The Chariot | — | — | Steel | Red |
| Pair `[L]` | The Duo | Jolly Joker; Sly Joker | — | Obelisk[most-played=Pair] | — | Mercury | — | — | — |
| Two Pair `[I]` | — | — | — | Obelisk[most-played=Two Pair] | — | Uranus | — | — | — |
| Two Pair Scoring `[L]` | — | Mad Joker; Clever Joker | — | — | — | — | — | — | — |
| Spare Trousers + Square Joker Two Pair `[L]` | Spare Trousers | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Three of a Kind `[I]` | TBD | TBD | TBD | TBD | TBD | Venus | TBD | TBD | TBD |
| Three of a Kind Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| DNA / Cryptid Rank-Copy Three of a Kind `[L]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid | TBD | TBD |
| Straight `[I]` | TBD | TBD | TBD | TBD | TBD | Saturn | TBD | TBD | TBD |
| Straight Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Shortcut / Four Fingers Straight `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Runner Scaling Straight `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Superposition Ace-Straight Tarot `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Flush `[I]` | TBD | TBD | TBD | TBD | The Star; The Moon; The Sun; The World | Jupiter | Sigil | TBD | TBD |
| Flush Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Smeared / Four Fingers Consistency Flush `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Full House `[L]` | TBD | TBD | TBD | TBD | TBD | Earth | TBD | TBD | TBD |
| Four of a Kind `[I]` | TBD | TBD | TBD | TBD | TBD | Mars | Cryptid; Ouija | TBD | TBD |
| Four of a Kind Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| DNA / Cryptid Rank-Copy Four of a Kind `[L]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid | TBD | TBD |
| Straight Flush `[I]` | TBD | TBD | TBD | TBD | TBD | Neptune | TBD | TBD | TBD |
| Straight Flush Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Shortcut / Four Fingers / Smeared Straight Flush `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Seance Straight-Flush Spectral Engine `[L]` | TBD | TBD | TBD | TBD | — | — | TBD | TBD | TBD |
| Five of a Kind `[I]` | TBD | TBD | TBD | TBD | TBD | Planet X | Cryptid; Ouija | TBD | TBD |
| Five of a Kind Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| DNA / Cryptid Rank-Copy Five of a Kind `[L]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid | TBD | TBD |
| Flush House `[L]` | TBD | TBD | TBD | TBD | TBD | Ceres | TBD | TBD | TBD |
| Flush Five `[I]` | TBD | TBD | TBD | TBD | TBD | Eris | Cryptid; Ouija | TBD | TBD |
| Flush Five Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| DNA / Cryptid Exact-Card Flush Five `[L]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid | TBD | TBD |
| The Idol Monoculture Flush Five `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Four-Card Hand Spam `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Square Joker Four-Card Chips `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Square + Green Joker Four-Card Spam `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## 2. Rank and face cards

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement | Seal |
|---|---|---|---|---|---|---|---|---|---|
| Aces `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | Grim; Ouija | TBD | TBD |
| Scholar Ace Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| DNA + Scholar Ace Concentration `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Cryptid | TBD | TBD |
| Low-Rank Scoring `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | Incantation | TBD | TBD |
| Fibonacci Low-Rank Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Hack + Fibonacci Retrigger `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Red |
| Twos `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | Ouija | TBD | TBD |
| Wee Joker Twos `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Wee Joker + Hack Retrigger Twos `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Red |
| Sixes / Sixth Sense `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Jacks / Hit the Road `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Ouija | TBD | TBD |
| Queens / Shoot the Moon `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Ouija | TBD | TBD |
| Face Cards `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | Familiar | TBD | TBD |
| Face-Card Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Photograph + Hanging Chad `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Red |
| Triboulet + Sock and Buskin `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Red |
| Pareidolia Universal Face Scoring `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Familiar | TBD | TBD |
| Held Face-Card Economy `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Business Card Face Economy `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Red |
| Faceless / No-Face `[I]` | TBD | TBD | TBD | TBD | The Hanged Man | TBD | Immolate | TBD | TBD |
| Ride the Bus No-Face Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Faceless Joker Discard Economy `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| The Idol Exact-Card Concentration `[L]` | TBD | TBD | TBD | TBD | Death | TBD | Cryptid | TBD | TBD |

## 3. Suits and held cards

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement | Seal |
|---|---|---|---|---|---|---|---|---|---|
| Hearts `[I]` | TBD | TBD | TBD | TBD | The Sun | TBD | Sigil | Wild | TBD |
| Hearts Scoring `[L]` | TBD | TBD | TBD | TBD | The Sun | TBD | Sigil | Wild | TBD |
| Bloodstone + Oops! All 6s Hearts `[L]` | TBD | TBD | TBD | TBD | The Sun | TBD | Sigil | Wild | Red |
| Bloodstone Retrigger Hearts `[L]` | TBD | TBD | TBD | TBD | The Sun | TBD | Sigil | Wild | Red |
| Diamonds `[I]` | TBD | TBD | TBD | TBD | The Star | TBD | Sigil | Wild | TBD |
| Diamonds Scoring `[L]` | TBD | TBD | TBD | TBD | The Star | TBD | Sigil | Wild | TBD |
| Rough Gem Diamond Economy / Scoring `[L]` | TBD | TBD | TBD | TBD | The Star | TBD | Sigil | Wild | Red |
| Clubs `[I]` | TBD | TBD | TBD | TBD | The Moon | TBD | Sigil | Wild | TBD |
| Clubs Scoring `[L]` | TBD | TBD | TBD | TBD | The Moon | TBD | Sigil | Wild | TBD |
| Onyx Agate / Seeing Double Clubs `[L]` | TBD | TBD | TBD | TBD | The Moon | TBD | Sigil | Wild | TBD |
| Spades `[I]` | TBD | TBD | TBD | TBD | The World | TBD | Sigil | Wild | TBD |
| Spades Scoring `[L]` | TBD | TBD | TBD | TBD | The World | TBD | Sigil | Wild | TBD |
| Arrowhead Spade Chips `[L]` | TBD | TBD | TBD | TBD | The World | TBD | Sigil | Wild | Red |
| Blackboard Held-Black Cards `[L]` | TBD | TBD | TBD | TBD | The Moon; The World | TBD | Sigil | TBD | TBD |
| Ancient Joker Suit-Rotation `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | Sigil | Wild | TBD |
| Ancient Joker Rotation `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Sigil | Wild | TBD |
| Ancient + Smeared Suit-Rotation `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | Sigil | Wild | TBD |
| Flower Pot Multi-Suit `[I]` | TBD | TBD | TBD | TBD | The Star; The Moon; The Sun; The World | TBD | Sigil | Wild | TBD |
| Splash + Flower Pot `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Wild | TBD |
| Smeared Joker + Flower Pot `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Wild | TBD |
| Smeared + Splash + Flower Pot `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Wild | TBD |

## 4. Enhancements

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement | Seal |
|---|---|---|---|---|---|---|---|---|---|
| Stone `[I]` | TBD | TBD | TBD | TBD | The Tower | TBD | TBD | Stone | TBD |
| Marble Joker + Stone Joker Scaling `[L]` | TBD | TBD | TBD | TBD | The Tower | TBD | TBD | Stone | TBD |
| Marble Joker + Vampire Stone Feed `[L]` | TBD | TBD | TBD | TBD | The Tower | TBD | TBD | Stone | TBD |
| DNA + Stone Joker Duplication `[L]` | TBD | TBD | TBD | TBD | The Tower | TBD | Cryptid | Stone | TBD |
| Stone High Card `[L]` | TBD | TBD | TBD | TBD | The Tower | Pluto | TBD | Stone | TBD |
| Glass `[I]` | TBD | TBD | TBD | TBD | Justice | TBD | TBD | Glass | TBD |
| Glass Joker Breakage Scaling `[L]` | TBD | TBD | TBD | TBD | Justice | TBD | TBD | Glass | TBD |
| Glass Retrigger Scoring `[L]` | TBD | TBD | TBD | TBD | Justice | TBD | Cryptid | Glass | Red |
| Steel `[I]` | TBD | TBD | TBD | TBD | The Chariot | TBD | TBD | Steel | TBD |
| Steel Held-Card Scaling `[L]` | TBD | TBD | TBD | TBD | The Chariot | TBD | TBD | Steel | TBD |
| Steel Joker Density Scaling `[L]` | TBD | TBD | TBD | TBD | The Chariot | TBD | TBD | Steel | TBD |
| Mime Steel Retrigger `[L]` | TBD | TBD | TBD | TBD | The Chariot | TBD | Deja Vu | Steel | Red |
| Lucky `[I]` | TBD | TBD | TBD | TBD | The Magician | TBD | TBD | Lucky | TBD |
| Lucky Cat Scaling `[L]` | TBD | TBD | TBD | TBD | The Magician | TBD | TBD | Lucky | TBD |
| Lucky Cat + Oops! All 6s `[L]` | TBD | TBD | TBD | TBD | The Magician | TBD | TBD | Lucky | TBD |
| Lucky Retrigger `[L]` | TBD | TBD | TBD | TBD | The Magician | TBD | Deja Vu | Lucky | Red |
| Gold Cards `[I]` | TBD | TBD | TBD | TBD | The Devil | TBD | Talisman | Gold | Gold |
| Held Gold + Mime Economy `[L]` | TBD | TBD | TBD | TBD | The Devil | TBD | Talisman; Deja Vu | Gold | Gold; Red |
| Golden Ticket Gold Scoring `[L]` | TBD | TBD | TBD | TBD | The Devil | TBD | Talisman | Gold | Gold |
| Midas Mask Gold Generation `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Gold | TBD |
| Midas Mask + Golden Ticket Economy `[L]` | TBD | TBD | TBD | TBD | The Devil | TBD | Talisman | Gold | Gold |

## 5. Seals

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement | Seal |
|---|---|---|---|---|---|---|---|---|---|
| Red Seal `[I]` | TBD | TBD | TBD | TBD | — | — | Deja Vu | — | Red |
| Played Red-Seal Retrigger `[L]` | TBD | TBD | TBD | TBD | — | — | Deja Vu | — | Red |
| Held Red-Seal Retrigger `[L]` | TBD | TBD | TBD | TBD | — | — | Deja Vu | — | Red |
| Blue Seal Hand-Level Scaling `[L]` | TBD | TBD | TBD | TBD | — | — | Trance | — | Blue |
| Purple Seal Tarot Engine `[L]` | TBD | TBD | TBD | TBD | — | — | Medium | — | Purple |
| Gold Seal Economy `[I]` | TBD | TBD | TBD | TBD | — | — | Talisman | — | Gold |
| Gold-Seal Scoring Economy `[L]` | TBD | TBD | TBD | TBD | — | — | Talisman | — | Gold |
| Gold-Seal Retrigger Economy `[L]` | TBD | TBD | TBD | TBD | — | — | Talisman; Deja Vu | — | Gold; Red |

## 6. Destruction, sacrifice, consumption, thinning

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement | Seal |
|---|---|---|---|---|---|---|---|---|---|
| Canio Destruction `[I]` | TBD | TBD | TBD | TBD | The Hanged Man | — | Immolate | TBD | TBD |
| Trading Card Canio `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Pareidolia Canio `[L]` | TBD | TBD | TBD | TBD | TBD | — | Familiar | TBD | TBD |
| Glass Canio `[L]` | TBD | TBD | TBD | TBD | Justice | — | Familiar | Glass | TBD |
| Consumable Canio `[L]` | TBD | TBD | TBD | TBD | The Hanged Man | — | Immolate | TBD | TBD |
| Vampire `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Enhancement-Feed Vampire `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | Any | TBD |
| Midas Mask + Vampire `[L]` | TBD | TBD | TBD | TBD | The Devil | — | TBD | Gold | TBD |
| Pareidolia + Midas Mask + Vampire `[L]` | TBD | TBD | TBD | TBD | The Devil | — | Familiar | Gold | TBD |
| Ceremonial Dagger Sacrifice `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Dagger Sacrifice `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Riff-Raff / Disposable-Joker Dagger Feed `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Madness Destruction `[I]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Solo Madness `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Eternal-Joker Madness `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Deck Thinning `[I]` | TBD | TBD | TBD | TBD | The Hanged Man | — | Immolate | TBD | TBD |
| Trading Card Thinning / Economy `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Erosion Thinning `[L]` | TBD | TBD | TBD | TBD | The Hanged Man | — | Immolate | TBD | TBD |
| Trading Card + Erosion `[L]` | TBD | TBD | TBD | TBD | The Hanged Man | — | Immolate | TBD | TBD |

## 7. Deck growth and card training

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement | Seal |
|---|---|---|---|---|---|---|---|---|---|
| Hologram Deck-Growth `[I]` | TBD | TBD | TBD | TBD | TBD | — | Familiar; Grim; Incantation; Cryptid | TBD | TBD |
| Hologram Growth `[L]` | TBD | TBD | TBD | TBD | TBD | — | Familiar; Grim; Incantation; Cryptid | TBD | TBD |
| DNA + Hologram `[L]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid | TBD | TBD |
| Certificate + Hologram `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Marble Joker + Hologram `[L]` | TBD | TBD | TBD | TBD | The Tower | — | TBD | Stone | TBD |
| Hiker Card Training `[I]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid | TBD | Red |
| Hiker Card Training `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Hiker Retrigger / Copy Training `[L]` | TBD | TBD | TBD | TBD | TBD | — | Cryptid; Deja Vu | TBD | Red |
| Driver's License Enhancement-Density `[L]` | TBD | TBD | TBD | TBD | The Magician; The Empress; The Hierophant; The Lovers; The Chariot; Justice; The Devil; The Tower | — | Familiar; Grim; Incantation | Any | TBD |
| Blue Joker Large-Deck Chips `[L]` | TBD | TBD | TBD | TBD | TBD | — | Familiar; Grim; Incantation; Cryptid | TBD | TBD |

## 8. Planet, Tarot, consumable engines

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement | Seal |
|---|---|---|---|---|---|---|---|---|---|
| Planet Engine `[I]` | TBD | TBD | TBD | TBD | The High Priestess | Any | Black Hole | — | Blue |
| Constellation Planet-Scaling `[L]` | TBD | TBD | TBD | TBD | The High Priestess | Any | Black Hole | — | Blue |
| Satellite Planet-Economy `[L]` | TBD | TBD | TBD | TBD | The High Priestess | Unique | Black Hole | — | Blue |
| Constellation + Satellite Planet Engine `[L]` | TBD | TBD | TBD | TBD | The High Priestess | Any/Unique | Black Hole | — | Blue |
| Perkeo Consumable Duplication `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Perkeo + Observatory Planet Stack `[L]` | TBD | TBD | TBD | TBD | — | TBD | — | — | — |
| Perkeo + Cryptid Copy Engine `[L]` | TBD | TBD | TBD | TBD | — | — | Cryptid | — | — |
| Perkeo Tarot / Spectral Engine `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Fortune Teller Tarot-Use Scaling `[L]` | TBD | TBD | TBD | TBD | Any | — | — | — | Purple |
| Vagabond Low-Money Tarot Engine `[L]` | TBD | TBD | TBD | TBD | Any | — | — | — | Purple |

## 9. Economy, shop, reroll, blind skip

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement | Seal |
|---|---|---|---|---|---|---|---|---|---|
| Cash Hoard / Interest `[I]` | TBD | TBD | TBD | TBD | The Hermit; Temperance | — | Immolate | TBD | Gold |
| Cash-Reserve Economy `[L]` | TBD | TBD | TBD | TBD | The Hermit; Temperance | — | Immolate | TBD | Gold |
| Rocket / To the Moon Cash Growth `[L]` | TBD | TBD | TBD | TBD | The Hermit; Temperance | — | Immolate | TBD | Gold |
| Bull Cash-to-Chips `[L]` | TBD | TBD | TBD | TBD | The Hermit; Temperance | — | Immolate | TBD | Gold |
| Bootstraps Cash-to-Mult `[L]` | TBD | TBD | TBD | TBD | The Hermit; Temperance | — | Immolate | TBD | Gold |
| Bull + Bootstraps Cash Scoring `[L]` | TBD | TBD | TBD | TBD | The Hermit; Temperance | — | Immolate | TBD | Gold |
| Cloud 9 Nines Economy `[L]` | TBD | TBD | TBD | TBD | TBD | — | Ouija | TBD | Gold |
| Campfire Sell-Scaling `[L]` | TBD | TBD | TBD | TBD | Temperance | — | TBD | TBD | TBD |
| Flash Card Reroll-Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Red Card Pack-Skip Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |
| Throwback Blind-Skip Scaling `[L]` | TBD | TBD | TBD | TBD | TBD | — | TBD | TBD | TBD |

## 10. Joker board

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement | Seal |
|---|---|---|---|---|---|---|---|---|---|
| Joker Stencil `[I]` | TBD | TBD | TBD | TBD | Judgement | — | Ankh; Ectoplasm; Wraith; The Soul | TBD | TBD |
| Joker Stencil Empty-Slot `[L]` | TBD | TBD | TBD | TBD | Judgement | — | Wraith; The Soul | TBD | TBD |
| Joker Stencil + Ankh / Invisible Duplication `[L]` | TBD | TBD | TBD | TBD | — | — | Ankh | TBD | TBD |
| Baseball Card Uncommon Stack `[L]` | TBD | TBD | TBD | TBD | Judgement | — | Wraith; The Soul | TBD | TBD |
| Abstract Joker Wide-Board `[L]` | TBD | TBD | TBD | TBD | Judgement | — | Wraith; The Soul | TBD | TBD |
| Swashbuckler Sell-Value Stack `[I]` | TBD | TBD | TBD | TBD | Judgement | — | Wraith; The Soul | TBD | TBD |
| Swashbuckler `[L]` | TBD | TBD | TBD | TBD | Judgement | — | Wraith; The Soul | TBD | TBD |
| Egg / Gift-Card Swashbuckler `[L]` | TBD | TBD | TBD | TBD | Judgement | — | Wraith; The Soul | TBD | TBD |

## 11. Discard and hand rotation

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement | Seal |
|---|---|---|---|---|---|---|---|---|---|
| Discard Utilization `[I]` | TBD | TBD | TBD | TBD | — | — | Medium | — | Purple |
| Castle Suit-Discard Scaling `[L]` | TBD | TBD | TBD | TBD | The Star; The Moon; The Sun; The World | — | Sigil | Wild | Purple |
| Mail-In Rebate Rank-Discard Economy `[L]` | TBD | TBD | TBD | TBD | Strength; Death | — | Ouija | — | Purple |
| Yorick Discard-Scaling `[L]` | TBD | TBD | TBD | TBD | — | — | Medium | — | Purple |
| No-Discard / Discard-Preservation `[I]` | TBD | TBD | TBD | TBD | — | — | — | — | — |
| Green Joker No-Discard Scaling `[L]` | TBD | TBD | TBD | TBD | — | — | — | — | — |
| Banner + Delayed Gratification Discard Reserve `[L]` | TBD | TBD | TBD | TBD | — | — | — | — | — |
| Ramen Preservation `[L]` | TBD | TBD | TBD | TBD | — | — | — | — | — |
| Burglar Zero-Discard / Extra-Hand `[L]` | TBD | TBD | TBD | TBD | — | — | — | — | — |
| Obelisk Hand-Rotation `[L]` | TBD | TBD | TBD | TBD | — | — | — | — | — |
| Burnt Joker Hand-Level Engine `[L]` | TBD | TBD | TBD | TBD | — | Any | Black Hole | — | Blue |

## 12. Hand scheduling

| Strategy | Gold | Silver | Bronze | Banned | Tarot | Planet | Spectral | Enhancement | Seal |
|---|---|---|---|---|---|---|---|---|---|
| Last-Hand Burst `[I]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Acrobat Last-Hand XMult `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Dusk Last-Hand Retrigger `[L]` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Red |
