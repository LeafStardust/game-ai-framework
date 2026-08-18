# Balatro Strategy Tree

Development topology reference. Relationships and evidence weights live in [`BALATRO_STRATEGY_RELATIONSHIPS.md`](BALATRO_STRATEGY_RELATIONSHIPS.md). Scoring/propagation rules live in [`BALATRO_STRATEGY_TREE_RULES.md`](BALATRO_STRATEGY_TREE_RULES.md).

Legend:
- `[I]` indexed strategy with specialized descendants.
- `[L]` specialization with no descendants.
- Standalone `[L]` = strategy with no specializations.

## 1. Poker-hand strategies

```text
High Card [I]
├── Stuntman / Small-Hand High Card [L]
└── Baron-Mime Steel-King High Card [L]

Pair [L]
Two Pair [L]
Three of a Kind [L]

Straight [L]

Flush [L]
Full House [L]
Four of a Kind [L]
Straight Flush [L]
Five of a Kind [L]
Flush House [L]
Flush Five [L]
```

## 2. Rank and face-card strategies

```text
Aces [L]
Low-Rank Scoring [L]
Twos / Wee-Hack [L]
Ten-Four / Walkie Talkie [L]

Sixes / Sixth Sense [L]
Jacks / Hit the Road [L]
Queens / Shoot the Moon [L]

Face Cards [I]
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
├── Bloodstone + Oops! All 6s Hearts [L]
└── Bloodstone Retrigger Hearts [L]

Diamonds / Rough Gem Economy [L]

Clubs [I]
├── Onyx Agate Club Scoring [L]
└── Seeing Double Mixed-Suit Clubs [L]

Spades / Arrowhead Chips [L]

Blackboard Held-Black Cards [L]
Raised Fist Held-Minimum [L]

Ancient Joker Suit-Rotation [L]

Flower Pot Multi-Suit [I]
├── Splash + Flower Pot [L]
└── Smeared Joker + Flower Pot [L]
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

Gold-Seal Retrigger Economy [L]
```

## 6. Destruction, sacrifice, consumption, and thinning

```text
Canio Destruction [I]
├── Trading Card Canio [L]
├── Pareidolia Canio [L]
├── Glass Canio [L]
└── Consumable Canio [L]

Vampire [I]
├── Midas Mask + Vampire [L]
└── Pareidolia + Midas Mask + Vampire [L]

Ceremonial Dagger / Disposable-Joker Feed [L]

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
├── DNA + Hologram [L]
├── Certificate + Hologram [L]
└── Marble Joker + Hologram [L]

Hiker Retrigger / Copy Training [L]

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

Tarot Engine [I]
├── Cartomancer Blind-Select Generation [L]
├── Hallucination Pack-Open Generation [L]
└── 8 Ball / Eights Tarot Generation [L]

Vagabond Low-Money Tarot Engine [L]
```

## 9. Economy, shop, pack, reroll, and blind-skip engines

```text
Cash Hoard / Interest [I]
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
Joker Stencil / Ankh / Invisible Duplication [L]

Baseball Card Uncommon Stack [L]
Abstract Joker Wide-Board [L]

Egg / Gift-Card Swashbuckler [L]
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

Loyalty Card Six-Hand Cycle [L]
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
Walkie Talkie               <-> Fours / Tens / Even Steven / Hack-on-Fours / retriggers
Hiker                       <-> compact deck / retriggers / DNA / trained scoring cards
Blackboard                  <-> Spades / Clubs / High Card / Pair / held-card preservation
Raised Fist                 <-> held-card minimum / Mime / Red Seal / high held ranks
Planet Engine               <-> Constellation / Satellite / Blue Seal / Astronomer / hand levels
Tarot Engine                <-> Fortune Teller / Cartomancer / Hallucination / 8 Ball / Purple Seal / Vagabond / Perkeo
Business Card               <-> Face Cards / Pareidolia / retriggers / Red Seal
Midas + Golden Ticket       <-> Face Cards / Gold Cards / retriggers
Ancient Joker               <-> suit flexibility / Smeared Joker
Joker Stencil               <-> Ankh / Invisible Joker / Negative Jokers / empty slots
```

## 14. Not standalone

These components do not form independent strategies. They are assigned as
conditional support and remain Neutral when their destination engine is absent.

| Component | Integrated destination |
|---|---|
| Blueprint / Brainstorm | Silver support for an owned, copyable defining engine; never independent strategy evidence |
| Astronomer | Planet Engine, Blue Seal hand-level scaling, and Burnt Joker hand-level support |
| Chaos the Clown | Gold support for an owned Flash Card reroll engine |
| Drunkard / Merry Andy | Purple Seal, Castle, Mail-In Rebate, Yorick, and Burnt Joker discard engines |
| Juggler / Troubadour | Held Red-Seal, Blue Seal, Steel-Mime, Baron-Mime, and other material held-card engines |
| Splash | Played Red-Seal, Hiker, Flower Pot, Midas Mask, and Vampire/Canio card-processing engines |
| Showman | Baseball Card duplicate-Uncommon support and Bronze wide-board support for Abstract Joker |
| Invisible Joker | Joker Stencil duplication, Swashbuckler sell-value feed, Abstract wide-board support, and situational engine duplication |

The five former one-child branches (Gold Seal, Ceremonial Dagger, Hiker,
Joker Stencil, and Swashbuckler) are collapsed into leaves. This preserves their
mechanics while satisfying the global rule that an indexed parent must expose at
least two genuine specializations.

**Topology frozen for v1.0F unless deterministic/live validation proves a defect.**
