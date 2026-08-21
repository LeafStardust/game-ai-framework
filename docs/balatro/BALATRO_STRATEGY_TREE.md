# Balatro Strategy Track Topology

Canonical topology reference for the Red/White strategy system. Contribution data lives in `BALATRO_STRATEGY_RELATIONSHIPS.md`; semantics/migration rules live in `BALATRO_STRATEGY_TREE_RULES.md`; realized viability lives in `BUILD_HEALTH_AND_REALIZED_STRENGTH.md`.

## Architectural status

The historical name **Strategy Tree** remains in filenames/code, but the target model is a **strategy-track / Bond-like system**:

- every Joker may contribute to multiple tracks;
- tracks develop independently;
- compatible developed tracks compose one emergent build;
- one track may become the principal power engine;
- other tracks reinforce hand shape, rank/suit, enhancements, economy, deck shaping, retriggers, etc.;
- conflicts exclude mechanically contradictory combinations;
- rank-aware prescriptions control actual decisions.

The runtime still contains legacy Primary/Secondary/Relevant machinery. It is migration infrastructure, not the final model. Do not interpret this topology as a tournament where exactly one node must win.

Legend: `[I]` = generic/indexed track with specializations; `[L]` = leaf/specialization. Parent-child edges mean evidence inheritance/factoring. Cross-cutting compatibility belongs in the composition graph, not fake parent edges.

## 1. Poker-hand tracks

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

Poker-hand tracks usually combine with a power engine rather than replacing it. Example: Burnt + Pair or Burnt + High Card.

## 2. Rank / face tracks

```text
Aces [L]
Low-Rank Scoring [L]
Twos / Wee-Hack [L]
Ten-Four / Walkie Talkie [L]
Sixes / Sixth Sense [L]
Jacks / Hit the Road [L]
Queens / Shoot the Moon [L]

Face Cards [I]
├── Photograph + Hanging Chad [L]
├── Triboulet + Sock and Buskin [L]
├── Pareidolia Universal Face Scoring [L]
├── Held Face-Card Economy [L]
└── Business Card Face Economy [L]

Faceless / No-Face [I]
└── Ride the Bus No-Face Scaling [L]

The Idol Exact-Card Concentration [L]
```

Important composition rules:
- Scholar is the defining Aces component; DNA/Fibonacci/Odd Todd reinforce Aces when prerequisites are real.
- Ten-Four is a paired package, not `Walkie alone = complete build`: Walkie is weak alone and materially stronger with Even Steven/compatible Four support.
- Ride the Bus creates an execution prescription: avoid playing face cards when a safe comparable non-face line exists; playing a face card resets its scaling.
- Face and no-face tracks can conflict when their prescriptions are materially developed.

## 3. Suit / held-card tracks

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

Raised Fist is held-card support rather than an independent track.

## 4. Enhancement tracks

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

## 5. Seal tracks

```text
Red Seal [I]
├── Played Red-Seal Retrigger [L]
└── Held Red-Seal Retrigger [L]
Blue Seal Hand-Level Scaling [L]
Purple Seal Tarot Engine [L]
Gold-Seal Retrigger Economy [L]
```

## 6. Destruction / thinning tracks

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

## 7. Deck-growth / training tracks

```text
Blue Joker / Hologram Deck-Growth [L]
Hiker Retrigger / Copy Training [L]
Driver's License Enhancement-Density [L]
```

Blue/Hologram growth is a good example of structural contribution versus realized power: Hologram x1.0 may belong strongly to the track while still being an inactive engine.

## 8. Planet / Tarot / consumable tracks

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

Constellation remains dependency-gated; Planet infrastructure must actually exist.

## 9. Economy / shop / skip tracks

```text
Bull / Bootstraps Cash Scoring [L]
Campfire Sell-Scaling [L]
Flash Card Reroll-Scaling [L]
Red Card Pack-Skip Scaling [L]
Throwback Blind-Skip Scaling [L]
```

Economy support can feed a scoring track without becoming the power engine. Bull/Bootstraps is different because cash itself becomes scoring power.

## 10. Joker-board composition tracks

```text
Joker Stencil / Ankh / Invisible Duplication [L]
Baseball Card Uncommon Stack [L]
Egg / Gift-Card Swashbuckler [L]
```

Abstract Joker remains generic board value, not an independent track.

## 11. Discard / no-discard / rotation tracks

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

Authoritative compatibility:

```text
Burnt <X> Green
Burnt <X> Burglar
Green <-> Burglar : strong synergy
```

Burnt is a discard-using permanent hand-level engine. When sufficiently developed and survival is safe, its first-discard activation must be deliberately used even if the first available scoring hand would already clear the blind. Burglar must never be treated as Burnt support because it removes Burnt's activation resource.

## 12. Hand-scheduling tracks

```text
Last-Hand Burst [I]
├── Acrobat Last-Hand XMult [L]
└── Dusk Last-Hand Retrigger [L]
Loyalty Card Six-Hand Cycle [L]
```

## 13. Cross-track composition examples

These are compatibility/synergy links, not parent edges and not exhaustive complete builds.

```text
Burnt                      <-> High Card / Pair / other cheap repeatable hand tracks
Burnt                      <-> Aces / Scholar / DNA when the card plan is compatible
Green                      <-> Burglar / no-discard / extra hands
Baron-Mime High Card       <-> Steel / Red Seal / DNA / hand-size / Shoot the Moon
PhotoChad                  <-> Face Cards / Pareidolia / Lucky / Glass / Red Seal / Hiker
Triboulet + Sock and Buskin<-> Face Cards / Pareidolia / Red Seal / Glass
Bloodstone Hearts          <-> Oops! All 6s / retriggers / Lucky
Marble Joker               <-> Stone / Blue-Hologram growth / Vampire / Driver's License
DNA                        <-> Aces / Stone / growth / Baron / Trips / Quads / Five Kind / Flush Five / Vampire
Pareidolia                 <-> face scoring / Canio / Midas Mask / Vampire
Perkeo                     <-> Planet / Cryptid / Tarot / Spectral
Blueprint / Brainstorm     <-> strongest compatible copyable engine
Bull / Bootstraps          <-> cash generators
Discard Utilization        <-> Castle / Mail-In Rebate / Purple Seal / Hit the Road / Faceless / Yorick
Hack / Fibonacci           <-> Twos / low ranks / retriggers
Walkie Talkie              <-> Tens / Fours / Even Steven / Hack-on-Fours / retriggers
Hiker                      <-> compact deck / retriggers / DNA / trained cards
Blackboard                 <-> Spades / Clubs / High Card / Pair / held-card preservation
Planet Engine              <-> Constellation / Satellite / Blue Seal / Astronomer / hand levels
Tarot Engine               <-> Fortune Teller / Cartomancer / Hallucination / 8 Ball / Purple Seal / Vagabond / Perkeo
Ancient Joker              <-> suit flexibility / Smeared Joker
Joker Stencil              <-> Ankh / Invisible / Negative / empty slots
```

## 14. Components that are not standalone tracks

These can contribute to one or several tracks but should not compete as independent builds merely because they are useful:

- Abstract Joker — generic wide-board additive Mult.
- Raised Fist — held-card/hand support.
- Rocket / To the Moon / Cloud 9 / Golden Joker and similar cash pieces — feed cash-scoring/economy tracks when usable.
- Reserved Parking / Business Card / Faceless Joker — contextual economy/support.
- Banner / Delayed Gratification — no-discard/discard-preservation support.
- Blueprint / Brainstorm — copy support for a compatible owned engine.
- Astronomer — Planet/Blue Seal/Burnt hand-level support and Constellation prerequisite.
- Drunkard / Merry Andy — discard-resource support where discards are actually desired.
- Juggler / Troubadour — held-card support.
- Splash — played-card processing support.
- Showman / Invisible Joker — board/duplication support.

## 15. Target runtime output

The topology should eventually produce a state like:

```text
Combined build : Burnt + Aces + Pair + DNA support
Power engine   : Burnt
Developed tracks: Burnt, Aces, Pair
Emerging tracks : deck copy
Conflicts       : Green, Burglar
```

It should **not** reduce the same state to `Primary=Burnt, Secondary=Aces, Third=Pair` and then treat those as competing alternative builds.
