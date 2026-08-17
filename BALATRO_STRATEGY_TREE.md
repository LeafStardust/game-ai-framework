# Balatro Strategy Tree

> **v1.0F topology freeze.** This file is intentionally topology-first and compact. Scoring, propagation, Ante behavior, Negative-Joker retention, and Gold/Silver/Bronze/Banned semantics live in [`BALATRO_STRATEGY_TREE_RULES.md`](BALATRO_STRATEGY_TREE_RULES.md).
>
> Only `[L]` leaves are actionable/ranked. `[I]` nodes provide foundation to their descendants. Further topology changes should require a real defect or live-validation finding rather than ordinary Joker synergy.

Legend:
- `[I]` internal/root node.
- `[L]` actionable leaf.
- A standalone `[L]` is both root and leaf.
- `Core ...` is the fallback leaf for a valid unspecialized branch.

## 1. Poker-hand strategies

```text
High Card [I]
├── Core Repetition / Level High Card [L]
├── Stuntman / Small-Hand High Card [L]
└── Baron-Mime Steel-King High Card [L]

Pair [L]

Two Pair [I]
├── Core Two Pair [L]
└── Spare Trousers + Square Joker Two Pair [L]

Three of a Kind [I]
├── Core Three of a Kind [L]
└── DNA / Cryptid Rank-Copy Three of a Kind [L]

Straight [I]
├── Core Straight [L]
├── Shortcut / Four Fingers Straight [L]
├── Runner Scaling Straight [L]
└── Superposition Ace-Straight Tarot [L]

Flush [I]
├── Core Flush [L]
└── Smeared / Four Fingers Consistency Flush [L]

Full House [L]

Four of a Kind [I]
├── Core Four of a Kind [L]
└── DNA / Cryptid Rank-Copy Four of a Kind [L]

Straight Flush [I]
├── Core Straight Flush [L]
├── Shortcut / Four Fingers / Smeared Straight Flush [L]
└── Seance Straight-Flush Spectral Engine [L]

Five of a Kind [I]
├── Core Five of a Kind [L]
└── DNA / Cryptid Rank-Copy Five of a Kind [L]

Flush House [L]

Flush Five [I]
├── Core Flush Five [L]
├── DNA / Cryptid Exact-Card Flush Five [L]
└── The Idol Monoculture Flush Five [L]

Four-Card Hand Spam [I]
├── Square Joker Four-Card Chips [L]
└── Square + Green Joker Four-Card Spam [L]
```

There are deliberately no natural-poker-hand edges such as `High Card -> Pair -> Three of a Kind -> Four of a Kind -> Five of a Kind`.

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
├── Core Face-Card Scoring [L]
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
├── Core Hearts Scoring [L]
├── Bloodstone + Oops! All 6s Hearts [L]
└── Bloodstone Retrigger Hearts [L]

Diamonds [I]
├── Core Diamonds Scoring [L]
└── Rough Gem Diamond Economy / Scoring [L]

Clubs [I]
├── Core Clubs Scoring [L]
└── Onyx Agate / Seeing Double Clubs [L]

Spades [I]
├── Core Spades Scoring [L]
└── Arrowhead Spade Chips [L]

Blackboard Held-Black Cards [L]

Ancient Joker Suit-Rotation [I]
├── Core Ancient Joker Suit-Rotation [L]
└── Ancient + Smeared Suit-Rotation [L]

Flower Pot Multi-Suit [I]
├── Splash + Flower Pot [L]
├── Smeared Joker + Flower Pot [L]
└── Smeared + Splash + Flower Pot [L]
```

Suit strategies remain independent from Flush; suit concentration can support several poker-hand leaves.

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
├── Core Steel Held-Card Scaling [L]
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
├── Core Gold-Seal Scoring Economy [L]
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
├── Core Enhancement-Feed Vampire [L]
├── Midas Mask + Vampire [L]
└── Pareidolia + Midas Mask + Vampire [L]

Ceremonial Dagger Sacrifice [I]
├── Core Dagger Sacrifice [L]
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
├── Core Hologram Growth [L]
├── DNA + Hologram [L]
├── Certificate + Hologram [L]
└── Marble Joker + Hologram [L]

Hiker Card Training [I]
├── Core Hiker Card Training [L]
└── Hiker Retrigger / Copy Training [L]

Driver's License Enhancement-Density [L]
Blue Joker Large-Deck Chips [L]
```

DNA is a copy engine used by concrete leaves; it is not itself a ranked strategy.

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
├── Core Cash-Reserve Economy [L]
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

An economy leaf may dominate early/midgame and later be overtaken by a scoring leaf; a ranked strategy does not have to be the final Ante-8 scoring engine.

## 10. Joker-board and composition strategies

```text
Joker Stencil [I]
├── Core Joker Stencil Empty-Slot [L]
└── Joker Stencil + Ankh / Invisible Duplication [L]

Baseball Card Uncommon Stack [L]
Abstract Joker Wide-Board [L]

Swashbuckler Sell-Value Stack [I]
├── Core Swashbuckler [L]
└── Egg / Gift-Card Swashbuckler [L]
```

Blueprint and Brainstorm are amplifiers, not standalone leaves.

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

Last-hand strategies remain subordinate to blind survival; the agent must not waste safe hands merely to force activation.

## 13. Important cross-cutting relationships

These are compatibility/evidence relationships for the later catalogue, **not extra parent edges**.

```text
Baron-Mime High Card        <-> Steel / Red Seal / DNA / hand-size support / Shoot the Moon
PhotoChad                   <-> Face Cards / Lucky / Glass / Red Seal / Hiker
Triboulet + Sock and Buskin <-> Face Cards / Red Seal / Glass
Bloodstone Hearts           <-> Oops! All 6s / retriggers / Lucky
Marble Joker                <-> Stone / Hologram / Vampire / Driver's License
DNA                         <-> Aces / Stone / Hologram / Baron / Trips / Quads / Five Kind / Flush Five / Vampire
Pareidolia                  <-> Face scoring / Canio / Midas Mask / Vampire
Perkeo                      <-> chosen Planet / Cryptid / transformation consumables
Blueprint / Brainstorm      <-> strongest copyable engine in the active leaf
Cash Hoard                  <-> Bull / Bootstraps / Rocket / To the Moon / Cloud 9 / economy sources
Discard Utilization         <-> Castle / Mail-In Rebate / Purple Seal / Hit the Road / Faceless / Yorick
No-Discard                  <-> Green Joker / Banner / Delayed Gratification / Ramen / Burglar
Hack / Fibonacci            <-> Twos / low-rank shaping / retriggers
Hiker                       <-> compact-deck shaping / retriggers / DNA / high-value scoring cards
Blackboard                  <-> Spades / Clubs / High Card / Pair / held-card preservation
Planet Engine               <-> Constellation / Satellite / Blue Seal / Astronomer / poker-hand investment
Business Card               <-> Face Cards / Pareidolia / retriggers / Red Seal
Midas + Golden Ticket       <-> Face Cards / Gold Cards / retriggers
Ancient Joker               <-> suit flexibility / Smeared Joker
Joker Stencil               <-> Ankh / Invisible Joker / Negative Jokers / deliberate empty slots
```

## 14. Deliberately not standalone strategies

```text
Blueprint / Brainstorm -> active-leaf copy amplifiers
Astronomer             -> Planet access/support
Chaos the Clown        -> reroll economy support
Drunkard / Merry Andy  -> discard-supply support
Juggler / Troubadour   -> hand-size support
Splash                 -> support outside explicit Flower Pot leaves
Showman                -> duplicate-access support
Invisible Joker        -> duplication support except in an explicit leaf such as Stencil duplication
```

## 15. Freeze rule

This topology is **frozen for the v1.0F catalogue migration**. Gold/Silver/Bronze/Banned assignment now proceeds node-by-node, beginning with High Card. Add or restructure nodes only when deterministic/live validation proves that the current topology cannot represent a materially distinct run-level policy.