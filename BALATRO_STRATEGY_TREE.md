# Balatro Strategy Tree

> **v1.0F topology development reference.** Relationships and evidence weights live in [`BALATRO_STRATEGY_RELATIONSHIPS.md`](BALATRO_STRATEGY_RELATIONSHIPS.md). Scoring/propagation rules live in [`BALATRO_STRATEGY_TREE_RULES.md`](BALATRO_STRATEGY_TREE_RULES.md).

Legend:
- `[I]` internal/root node.
- `[L]` actionable leaf.
- Standalone `[L]` = root + leaf.

## 1. Poker-hand strategies

```text
High Card [I]
├── Repetition / Level High Card [L]
├── Stuntman / Small-Hand High Card [L]
└── Baron-Mime Steel-King High Card [L]

Pair [L]

Two Pair [I]
├── Two Pair Scoring [L]
└── Spare Trousers + Square Joker Two Pair [L]

Three of a Kind [I]
├── Three of a Kind Scoring [L]
└── DNA / Cryptid Rank-Copy Three of a Kind [L]

Straight [I]
├── Straight Scoring [L]
├── Shortcut / Four Fingers Straight [L]
├── Runner Scaling Straight [L]
└── Superposition Ace-Straight Tarot [L]

Flush [I]
├── Flush Scoring [L]
└── Smeared / Four Fingers Consistency Flush [L]

Full House [L]

Four of a Kind [I]
├── Four of a Kind Scoring [L]
└── DNA / Cryptid Rank-Copy Four of a Kind [L]

Straight Flush [I]
├── Straight Flush Scoring [L]
├── Shortcut / Four Fingers / Smeared Straight Flush [L]
└── Seance Straight-Flush Spectral Engine [L]

Five of a Kind [I]
├── Five of a Kind Scoring [L]
└── DNA / Cryptid Rank-Copy Five of a Kind [L]

Flush House [L]

Flush Five [I]
├── Flush Five Scoring [L]
├── DNA / Cryptid Exact-Card Flush Five [L]
└── The Idol Monoculture Flush Five [L]

Four-Card Hand Spam [I]
├── Square Joker Four-Card Chips [L]
└── Square + Green Joker Four-Card Spam [L]
```

**No natural poker-hand progression edges.**

## 2. Rank and face-card strategies

```text
Aces [I]
├── Scholar Ace Scoring [L]
└── DNA + Scholar Ace Concentration [L]

Low-Rank Scoring [I]
├── Fibonacci Low-Rank Scoring [L]
└── Hack + Fibonacci Retrigger [L]

Twos [I]
├── Wee Joker Twos [L]
└── Wee Joker + Hack Retrigger Twos [L]

Sixes / Sixth Sense [L]
Jacks / Hit the Road [L]
Queens / Shoot the Moon [L]

Face Cards [I]
├── Face-Card Scoring [L]
├── Photograph + Hanging Chad (PhotoChad) [L]
├── Triboulet + Sock and Buskin [L]
├── Pareidolia Universal Face Scoring [L]
├── Held Face-Card Economy [L]
└── Business Card Face Economy [L]

Faceless / No-Face [I]
├── Ride the Bus No-Face Scaling [L]
└── Faceless Joker Discard Economy [L]

The Idol Exact-Card Concentration [L]
```

## 3. Suit and held-card strategies

```text
Hearts [I]
├── Hearts Scoring [L]
├── Bloodstone + Oops! All 6s Hearts [L]
└── Bloodstone Retrigger Hearts [L]

Diamonds [I]
├── Diamonds Scoring [L]
└── Rough Gem Diamond Economy / Scoring [L]

Clubs [I]
├── Clubs Scoring [L]
└── Onyx Agate / Seeing Double Clubs [L]

Spades [I]
├── Spades Scoring [L]
└── Arrowhead Spade Chips [L]

Blackboard Held-Black Cards [L]

Ancient Joker Suit-Rotation [I]
├── Ancient Joker Rotation [L]
└── Ancient + Smeared Suit-Rotation [L]

Flower Pot Multi-Suit [I]
├── Splash + Flower Pot [L]
├── Smeared Joker + Flower Pot [L]
└── Smeared + Splash + Flower Pot [L]
```

## 4. Enhancement strategies

```text
Stone [I]
├── Marble Joker + Stone Joker Scaling [L]
├── Marble Joker + Vampire Stone Feed [L]
├── DNA + Stone Joker Duplication [L]
└── Stone High Card [L]

Glass [I]
├── Glass Joker Breakage Scaling [L]
└── Glass Retrigger Scoring [L]

Steel [I]
├── Steel Held-Card Scaling [L]
├── Steel Joker Density Scaling [L]
└── Mime Steel Retrigger [L]

Lucky [I]
├── Lucky Cat Scaling [L]
├── Lucky Cat + Oops! All 6s [L]
└── Lucky Retrigger [L]

Gold Cards [I]
├── Held Gold + Mime Economy [L]
├── Golden Ticket Gold Scoring [L]
├── Midas Mask Gold Generation [L]
└── Midas Mask + Golden Ticket Economy [L]
```

## 5. Seal strategies

```text
Red Seal [I]
├── Played Red-Seal Retrigger [L]
└── Held Red-Seal Retrigger [L]

Blue Seal Hand-Level Scaling [L]
Purple Seal Tarot Engine [L]

Gold Seal Economy [I]
├── Gold-Seal Scoring Economy [L]
└── Gold-Seal Retrigger Economy [L]
```

## 6. Destruction, sacrifice, consumption, and thinning

```text
Canio Destruction [I]
├── Trading Card Canio [L]
├── Pareidolia Canio [L]
├── Glass Canio [L]
└── Consumable Canio [L]

Vampire [I]
├── Enhancement-Feed Vampire [L]
├── Midas Mask + Vampire [L]
└── Pareidolia + Midas Mask + Vampire [L]

Ceremonial Dagger Sacrifice [I]
├── Dagger Sacrifice [L]
└── Riff-Raff / Disposable-Joker Dagger Feed [L]

Madness Destruction [I]
├── Solo Madness [L]
└── Eternal-Joker Madness [L]

Deck Thinning [I]
├── Trading Card Thinning / Economy [L]
├── Erosion Thinning [L]
└── Trading Card + Erosion [L]
```

## 7. Deck-growth, card-addition, and card-training engines

```text
Hologram Deck-Growth [I]
├── Hologram Growth [L]
├── DNA + Hologram [L]
├── Certificate + Hologram [L]
└── Marble Joker + Hologram [L]

Hiker Card Training [I]
├── Hiker Card Training [L]
└── Hiker Retrigger / Copy Training [L]

Driver's License Enhancement-Density [L]
Blue Joker Large-Deck Chips [L]
```

## 8. Planet, Tarot, and consumable engines

```text
Planet Engine [I]
├── Constellation Planet-Scaling [L]
├── Satellite Planet-Economy [L]
└── Constellation + Satellite Planet Engine [L]

Perkeo Consumable Duplication [I]
├── Perkeo + Observatory Planet Stack [L]
├── Perkeo + Cryptid Copy Engine [L]
└── Perkeo Tarot / Spectral Engine [L]

Fortune Teller Tarot-Use Scaling [L]
Vagabond Low-Money Tarot Engine [L]
```

## 9. Economy, shop, pack, reroll, and blind-skip engines

```text
Cash Hoard / Interest [I]
├── Cash-Reserve Economy [L]
├── Rocket / To the Moon Cash Growth [L]
├── Bull Cash-to-Chips [L]
├── Bootstraps Cash-to-Mult [L]
├── Bull + Bootstraps Cash Scoring [L]
└── Cloud 9 Nines Economy [L]

Campfire Sell-Scaling [L]
Flash Card Reroll-Scaling [L]
Red Card Pack-Skip Scaling [L]
Throwback Blind-Skip Scaling [L]
```

## 10. Joker-board and composition strategies

```text
Joker Stencil [I]
├── Joker Stencil Empty-Slot [L]
└── Joker Stencil + Ankh / Invisible Duplication [L]

Baseball Card Uncommon Stack [L]
Abstract Joker Wide-Board [L]

Swashbuckler Sell-Value Stack [I]
├── Swashbuckler [L]
└── Egg / Gift-Card Swashbuckler [L]
```

## 11. Discard, no-discard, and hand-rotation engines

```text
Discard Utilization [I]
├── Castle Suit-Discard Scaling [L]
├── Mail-In Rebate Rank-Discard Economy [L]
└── Yorick Discard-Scaling [L]

No-Discard / Discard-Preservation [I]
├── Green Joker No-Discard Scaling [L]
├── Banner + Delayed Gratification Discard Reserve [L]
├── Ramen Preservation [L]
└── Burglar Zero-Discard / Extra-Hand [L]

Obelisk Hand-Rotation [L]
Burnt Joker Hand-Level Engine [L]
```

## 12. Hand-scheduling engines

```text
Last-Hand Burst [I]
├── Acrobat Last-Hand XMult [L]
└── Dusk Last-Hand Retrigger [L]
```

## 13. Cross-cutting links

```text
Baron-Mime High Card        <-> Steel / Red Seal / DNA / hand-size support / Shoot the Moon
PhotoChad                   <-> Face Cards / Lucky / Glass / Red Seal / Hiker
Triboulet + Sock and Buskin <-> Face Cards / Red Seal / Glass
Bloodstone Hearts           <-> Oops! All 6s / retriggers / Lucky
Marble Joker                <-> Stone / Hologram / Vampire / Driver's License
DNA                         <-> Aces / Stone / Hologram / Baron / Trips / Quads / Five Kind / Flush Five / Vampire
Pareidolia                  <-> Face scoring / Canio / Midas Mask / Vampire
Perkeo                      <-> Planet / Cryptid / Tarot / Spectral
Blueprint / Brainstorm      <-> strongest copyable active engine
Cash Hoard                  <-> Bull / Bootstraps / Rocket / To the Moon / Cloud 9
Discard Utilization         <-> Castle / Mail-In Rebate / Purple Seal / Hit the Road / Faceless / Yorick
No-Discard                  <-> Green Joker / Banner / Delayed Gratification / Ramen / Burglar
Hack / Fibonacci            <-> Twos / low-rank shaping / retriggers
Hiker                       <-> compact deck / retriggers / DNA / trained scoring cards
Blackboard                  <-> Spades / Clubs / High Card / Pair / held-card preservation
Planet Engine               <-> Constellation / Satellite / Blue Seal / Astronomer / hand levels
Business Card               <-> Face Cards / Pareidolia / retriggers / Red Seal
Midas + Golden Ticket       <-> Face Cards / Gold Cards / retriggers
Ancient Joker               <-> suit flexibility / Smeared Joker
Joker Stencil               <-> Ankh / Invisible Joker / Negative Jokers / empty slots
```

## 14. Not standalone

```text
Blueprint / Brainstorm
Astronomer
Chaos the Clown
Drunkard / Merry Andy
Juggler / Troubadour
Splash
Showman
Invisible Joker
```

**Topology frozen for v1.0F unless deterministic/live validation proves a defect.**
