# Balatro Strategy Tree

Development topology reference. Relationships and evidence weights live in [`BALATRO_STRATEGY_RELATIONSHIPS.md`](BALATRO_STRATEGY_RELATIONSHIPS.md). Scoring/propagation rules live in [`BALATRO_STRATEGY_TREE_RULES.md`](BALATRO_STRATEGY_TREE_RULES.md).

Implementation status:
- **Part 4 / Section 4 — Enhancements: IMPLEMENTED.** Runtime support exists for the enhancement strategies below; this document is the canonical topology reference and folds synergy-only variants back into their defining route.
- **Part 5 / Section 5 — Seals: IMPLEMENTED.** Red-Seal played/held support and Blue/Purple/Gold Seal engines are conditionally activated from matching live deck state instead of static Joker ownership alone.
- Sections 6–12 are also present in the current runtime forest; this file remains the canonical topology reference rather than a progress checklist.

Legend:
- `[I]` indexed strategy with specialized descendants.
- `[L]` specialization with no descendants.
- Standalone `[L]` = strategy with no specializations.
- A child exists only when it represents a genuinely distinct build/play route. Synergy-only variants stay inside the defining node's relationship row.

Runtime role note:
- The tree is topology, **not** a requirement that exactly one positive node survives.
- Runtime orchestration resolves one **Primary** scoring/win-condition route plus compatible **Secondary** scoring engines and **Support** engines.
- Ante 6+ keeps the Primary fully prescriptive while compatible engines may remain active at reduced influence; incompatible hand prescriptions and explicit conflicts are suppressed.
- A standalone strategy must contain a plausible run-clearing scoring engine, not merely cash generation, static filler value, or generic support.
- Support-only catalogue IDs may remain internally for topology compatibility but are retired from active strategy competition.

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
└── Pareidolia Universal Face Scoring [L]

Faceless / No-Face [I]
└── Ride the Bus No-Face Scaling [L]

The Idol Exact-Card Concentration [L]
```

Relationship notes:
- Aces is Scholar-defined: DNA, Fibonacci, and Odd Todd are support only after Scholar establishes the route.
- Ride the Bus is Silver evidence for its no-face scaling leaf, not a Gold self-defining core.
- Pareidolia can protect compatible face-payoff Jokers such as Smiley Face while its leaf is active, but inherited Face Cards evidence is counted only once.
- Reserved Parking, Business Card, and Faceless Joker economy are support components, not standalone run-clearing routes.

## 3. Suit and held-card strategies

```text
Hearts / Bloodstone [L]

Diamonds / Rough Gem Economy [L]

Clubs [I]
├── Onyx Agate Club Scoring [L]
└── Seeing Double Mixed-Suit Clubs [L]

Spades / Arrowhead Chips [L]

Blackboard Held-Black Cards [L]
Ancient Joker Suit-Rotation [L]
Flower Pot Multi-Suit [L]
```

Raised Fist is held-card support rather than an independent strategy.

## 4. Enhancement strategies — runtime implemented

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
└── Lucky Retrigger [L]

Gold Cards [I]
├── Held Gold + Mime Economy [L]
├── Golden Ticket Gold Scoring [L]
└── Midas Mask Gold Generation [L]
```

## 5. Seal strategies — runtime implemented

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
├── Trading Card / Pareidolia Canio [L]
├── Glass Canio [L]
└── Consumable Canio [L]

Vampire [L]

Ceremonial Dagger / Disposable-Joker Feed [L]

Madness Destruction [I]
├── Solo Madness [L]
└── Eternal-Joker Madness [L]

Deck Thinning [I]
├── Trading Card Thinning / Economy [L]
└── Erosion Thinning [L]
```

## 7. Deck-growth, card-addition, and card-training engines

```text
Hologram Deck-Growth [L]

Hiker Retrigger / Copy Training [L]
Driver's License Enhancement-Density [L]
Blue Joker Large-Deck Chips [L]
```

These are often compatible engines rather than mutually exclusive replacements for the Primary poker-hand/scoring route. Driver's License, Hiker, and Blue Joker may remain active beside a compatible Primary when their mechanics reinforce the same build.

## 8. Planet, Tarot, and consumable engines

```text
Planet Engine [I]
└── Constellation Planet-Scaling [L]

Perkeo Consumable Duplication [I]
├── Perkeo + Observatory Planet Stack [L]
├── Perkeo + Cryptid Copy Engine [L]
└── Perkeo Tarot / Spectral Engine [L]

Tarot Engine [I]
├── Passive Tarot Generation [L]
└── 8 Ball / Eights Tarot Generation [L]

Vagabond Low-Money Tarot Engine [L]
```

Constellation is dependency-gated: it is not a self-starting Planet core. Astronomer enables it as Silver support. Satellite is economy support for a real Planet/Constellation engine and is no longer a standalone strategy.

## 9. Economy, shop, pack, reroll, and blind-skip engines

```text
Cash Hoard / Interest [I]
├── Rocket / To the Moon Cash Growth [L]
└── Bull / Bootstraps Cash Scoring [L]

Campfire Sell-Scaling [L]
Flash Card Reroll-Scaling [L]
Red Card Pack-Skip Scaling [L]
Throwback Blind-Skip Scaling [L]
```

Cloud 9 is economy support, not a standalone run-clearing route.

## 10. Joker-board and composition strategies

```text
Joker Stencil / Ankh / Invisible Duplication [L]

Baseball Card Uncommon Stack [L]
Egg / Gift-Card Swashbuckler [L]
```

Abstract Joker is generic wide-board additive Mult and is not a standalone strategy. It remains an ordinary Joker/support component where relevant.

## 11. Discard, no-discard, and hand-rotation engines

```text
Discard Utilization [I]
├── Castle Suit-Discard Scaling [L]
└── Yorick Discard-Scaling [L]

No-Discard / Discard-Preservation [I]
├── Green Joker No-Discard Scaling [L]
├── Ramen Preservation [L]
└── Burglar Zero-Discard / Extra-Hand [L]

Obelisk Hand-Rotation [L]
Burnt Joker Hand-Level Engine [L]
```

Mail-In Rebate and Banner + Delayed Gratification are support/economy packages rather than independent strategies. No-discard incentives never override the tactical survival rule that discarding is mandatory when the final hand cannot clear and legal discards remain.

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
DNA                         <-> Scholar-backed Aces / Stone / Hologram / Baron / Trips / Quads / Five Kind / Flush Five / Vampire
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
Planet Engine               <-> Constellation (Astronomer/Satellite gated) / Satellite / Blue Seal / Astronomer / hand levels
Tarot Engine                <-> Fortune Teller / Cartomancer / Hallucination / 8 Ball / Purple Seal / Vagabond / Perkeo
Business Card               <-> Face Cards / Pareidolia / retriggers / Red Seal
Midas + Golden Ticket       <-> Face Cards / Gold Cards / retriggers
Ancient Joker               <-> suit flexibility / Smeared Joker
Joker Stencil               <-> Ankh / Invisible Joker / Negative Jokers / empty slots
```

## 14. Not standalone

These components do not form independent strategies. They are assigned as conditional support, generic item value, or integrated economy support and must not compete for Primary/Secondary/Tertiary strategy rank by themselves.

| Component | Integrated destination |
|---|---|
| Abstract Joker | Generic wide-board additive Mult; ordinary Joker value only, never a standalone route |
| Raised Fist | High Card / Pair / held-card / Mime and Red-Seal support |
| Reserved Parking | Face-card held economy support |
| Business Card | Face Cards / Pareidolia / retriggers / Red Seal economy support |
| Faceless Joker | Faceless / discard economy support |
| Satellite | Planet / Constellation economy support |
| Cloud 9 | Cash-hoard / Nines economy support |
| Mail-In Rebate | Discard-utilization economy support |
| Banner / Delayed Gratification | No-discard / discard-preservation support |
| Blueprint / Brainstorm | Silver support for an owned, copyable defining engine; never independent strategy evidence |
| Astronomer | Planet Engine, Blue Seal hand-level scaling, Burnt Joker hand-level support, and prerequisite for Silver Constellation support |
| Chaos the Clown | Gold support for an owned Flash Card reroll engine |
| Drunkard / Merry Andy | Purple Seal, Castle, Mail-In Rebate, Yorick, and Burnt Joker discard engines |
| Juggler / Troubadour | Held Red-Seal, Blue Seal, Steel-Mime, Baron-Mime, and other material held-card engines |
| Splash | Played Red-Seal, Hiker, Flower Pot, Midas Mask, and Vampire/Canio card-processing engines |
| Showman | Baseball Card duplicate-Uncommon support and generic wide-board support |
| Invisible Joker | Joker Stencil duplication, Swashbuckler sell-value feed, and situational engine duplication |

Synergy-only combinations are folded into their defining strategy rows. Indexed parents are reserved for genuinely different play/build routes, not merely stronger combinations of the same route.
