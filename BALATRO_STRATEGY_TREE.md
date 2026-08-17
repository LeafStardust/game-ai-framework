# Balatro Strategy Tree

> **Topology only.** This file exists so the strategy forest can be reviewed without scrolling through scoring rules or tier explanations.
>
> Rules for evidence propagation, leaf-only ranking, Ante behavior, Negative Joker retention, and later Gold/Silver/Bronze/Banned assignment live in [`BALATRO_STRATEGY_TREE_RULES.md`](BALATRO_STRATEGY_TREE_RULES.md).
>
> Exact Gold/Silver/Bronze/Banned tables are intentionally **not** assigned until this topology is frozen.

Legend:

- `[I]` internal/root node — contributes foundation but is not directly ranked.
- `[L]` actionable leaf — appears in strategy rankings.
- A standalone `[L]` is both root and leaf.
- `Core ...` is a fallback leaf for a valid unspecialized version of a split root.

---

## 1. Poker-hand strategies

```text
High Card [I]
├── Core Repetition / Level High Card [L]
│   └── broad High Card foundation: repeated-hand and hand-level scaling
├── Stuntman / Small-Hand High Card [L]
│   └── tiny played hands; hand-size cost is acceptable because hand construction is trivial
└── Baron-Mime Steel-King High Card [L]
    └── preserve Kings/Steel/Red-Seal held cards; maximize held-card retriggers and hand size

Pair [L]

Two Pair [I]
├── Core Two Pair [L]
└── Spare Trousers + Square Joker Two Pair [L]
    └── repeated four-card Two Pair hands scale both Mult and Chips

Three of a Kind [L]

Straight [I]
├── Core Straight [L]
├── Shortcut / Four Fingers Straight [L]
│   └── structural consistency through relaxed Straight requirements
└── Runner Scaling Straight [L]
    └── repeatedly score Straights to scale Runner Chips

Flush [I]
├── Core Flush [L]
└── Smeared / Four Fingers Consistency Flush [L]
    └── reduce suit/hand-size requirements to make Flushes highly repeatable

Full House [L]
Four of a Kind [L]

Straight Flush [I]
├── Core Straight Flush [L]
└── Shortcut / Four Fingers / Smeared Straight Flush [L]
    └── rule-changing consistency shell for an otherwise difficult hand

Five of a Kind [I]
├── Core Five of a Kind [L]
└── DNA / Cryptid Rank-Copy Five of a Kind [L]
    └── concentrate one rank until five-copy hands become routine

Flush House [L]

Flush Five [I]
├── Core Flush Five [L]
├── DNA / Cryptid Exact-Card Flush Five [L]
│   └── copy identical rank+suit cards until the hand is deterministic
└── The Idol Monoculture Flush Five [L]
    └── exact-card concentration built to exploit The Idol's current target
```

There are intentionally no `High Card -> Pair -> Trips -> Quads -> Five of a Kind` edges. Those are different poker-hand roots, not natural progression levels.

---

## 2. Rank and face-card strategies

```text
Aces [I]
├── Scholar Ace Scoring [L]
│   └── score concentrated Aces for direct Chips/Mult payoff
└── DNA + Scholar Ace Concentration [L]
    └── repeatedly copy Aces, then score duplicate-Ace poker hands through Scholar

Twos [I]
├── Wee Joker Twos [L]
│   └── concentrate and repeatedly score 2s to scale Wee Joker
└── Wee Joker + Hack Retrigger Twos [L]
    └── retrigger scored 2s to accelerate Wee Joker scaling

Face Cards [I]
├── Core Face-Card Scoring [L]
├── Photograph + Hanging Chad (PhotoChad) [L]
│   └── place a face card first and retrigger Photograph's XMult activation
├── Triboulet + Sock and Buskin [L]
│   └── score Kings/Queens and retrigger every face-card XMult trigger
└── Pareidolia Universal Face Scoring [L]
    └── make all cards satisfy face-card payoff Jokers

Faceless / No-Face [I]
├── Ride the Bus No-Face Scaling [L]
│   └── avoid scoring face cards while scaling repeated hands
└── Faceless Joker Discard Economy [L]
    └── deliberately discard face cards for money while maintaining a non-face scoring shell

The Idol Exact-Card Concentration [L]
    └── collapse the deck around the current target rank+suit so every scoring card can trigger The Idol
```

`PhotoChad`, Triboulet, and Pareidolia stay under Face Cards rather than under one poker hand because they can support several poker-hand roots.

---

## 3. Suit strategies

```text
Hearts [I]
├── Core Hearts Scoring [L]
├── Bloodstone + Oops! All 6s Hearts [L]
│   └── turn Bloodstone's chance-based XMult into a reliable trigger
└── Bloodstone Retrigger Hearts [L]
    └── use Hanging Chad / Dusk / Seltzer / Red Seals or similar retriggers to multiply Heart triggers

Diamonds [I]
├── Core Diamonds Scoring [L]
└── Rough Gem Diamond Economy/Scoring [L]
    └── repeatedly score Diamonds while converting suit density into money and score support

Clubs [I]
├── Core Clubs Scoring [L]
└── Onyx Agate / Seeing Double Clubs [L]
    └── exploit Club density while satisfying Seeing Double where the current suit shell permits it

Spades [I]
├── Core Spades Scoring [L]
└── Arrowhead Spade Chips [L]
    └── concentrate Spades and convert each scored Spade into a large Chip source

Ancient Joker Suit-Rotation [L]
    └── preserve enough flexible suit structure to follow Ancient Joker's current suit efficiently

Flower Pot Multi-Suit [I]
├── Splash + Flower Pot [L]
├── Smeared Joker + Flower Pot [L]
└── Smeared + Splash + Flower Pot [L]
    └── reliably satisfy all four effective suits in one scoring hand
```

Suit leaves remain independent from Flush. A Hearts/Bloodstone run may play Flush, Five of a Kind, High Card, or another hand depending on the rest of the build.

---

## 4. Enhancement strategies

```text
Stone [I]
├── Marble Joker + Stone Joker Scaling [L]
│   └── generate Stone cards every Blind and convert total Stone count into permanent Chips
├── Marble Joker + Vampire Stone Feed [L]
│   └── generate a fresh enhancement every Blind and feed those Stone enhancements into Vampire
├── DNA + Stone Joker Duplication [L]
│   └── copy Stone cards to accelerate Stone Joker's deck-wide Chip scaling
└── Stone High Card [L]
    └── score large groups of Stone cards through High Card while using independent Mult scaling

Glass [I]
├── Glass Joker Breakage Scaling [L]
│   └── intentionally create/play Glass cards and profit from their destruction
└── Glass Retrigger Scoring [L]
    └── retrigger high-value Glass cards with Hanging Chad / Sock and Buskin / Dusk / Seltzer / Red Seal

Steel [I]
├── Core Steel Held-Card Scaling [L]
│   └── hold Steel cards while scoring with a separate small hand
├── Steel Joker Density Scaling [L]
│   └── increase Steel-card count so Steel Joker becomes a large independent XMult source
└── Mime Steel Retrigger [L]
    └── retrigger held Steel-card effects through Mime

Lucky [I]
├── Lucky Cat Scaling [L]
│   └── repeatedly trigger Lucky cards to grow Lucky Cat
├── Lucky Cat + Oops! All 6s [L]
│   └── increase Lucky trigger reliability and accelerate Lucky Cat growth
└── Lucky Retrigger [L]
    └── retrigger Lucky cards to multiply money/Mult procs and Lucky Cat growth

Gold Cards [I]
├── Held Gold + Mime Economy [L]
│   └── retain Gold cards through end of round and retrigger held-card payout with Mime
├── Golden Ticket Gold Scoring [L]
│   └── deliberately score Gold cards for repeated Golden Ticket money
└── Midas Mask Gold Generation [L]
    └── repeatedly convert scored face cards into Gold cards for later economy/use
```

Baron-Mime Steel Kings remains a High Card leaf because the scoring plan is specifically a High Card held-card realization; Steel and Red Seal independently provide compatible supporting evidence.

---

## 5. Seal strategies

```text
Red Seal [I]
├── Played Red-Seal Retrigger [L]
│   └── place Red Seal on the build's strongest scored-card trigger target
└── Held Red-Seal Retrigger [L]
    └── use Red Seal on held-effect cards such as Steel/Baron-compatible targets

Blue Seal Hand-Level Scaling [L]
    └── preserve Blue Seals to round end and repeatedly generate the intended Planet

Purple Seal Tarot Engine [L]
    └── preserve discard capacity and repeatedly discard Purple Seals for Tarot generation

Gold Seal Economy [I]
├── Core Gold-Seal Scoring Economy [L]
└── Gold-Seal Retrigger Economy [L]
    └── retrigger Gold-Seal cards to multiply payout
```

---

## 6. Destruction, sacrifice, and consumption engines

```text
Canio Destruction [I]
├── Trading Card Canio [L]
│   └── destroy a face card with the first discard each Blind to scale Canio
├── Pareidolia Canio [L]
│   └── make every playing card a valid Canio destruction target
├── Glass Canio [L]
│   └── destroy Glass face cards so Glass/Canio scaling can overlap
└── Consumable Canio [L]
    └── use The Hanged Man / Immolate / compatible Spectrals as repeatable face-card destruction sources

Vampire [I]
├── Core Enhancement-Feed Vampire [L]
│   └── continuously create enhanced cards and intentionally consume them for Vampire XMult
├── Midas Mask + Vampire [L]
│   └── convert scored face cards to Gold, then let Vampire consume the enhancement
└── Pareidolia + Midas Mask + Vampire [L]
    └── turn every scored card into a repeatable enhancement feed source

Ceremonial Dagger Sacrifice [I]
├── Core Dagger Sacrifice [L]
└── Riff-Raff / Disposable-Joker Dagger Feed [L]
    └── generate expendable Jokers specifically to convert sell value into Dagger Mult

Madness Destruction [I]
├── Solo Madness [L]
└── Eternal-Joker Madness [L]
    └── preserve Eternal support while allowing Madness to destroy ordinary Jokers and scale

Erosion Deck-Thinning [I]
├── Core Erosion Thinning [L]
└── Trading Card / Consumable Erosion [L]
    └── repeatedly destroy cards to accelerate Erosion while improving draw consistency
```

---

## 7. Deck-growth and card-addition engines

```text
Hologram Deck-Growth [I]
├── Core Hologram Growth [L]
├── DNA + Hologram [L]
│   └── every copied card advances both deck concentration and Hologram XMult
├── Certificate + Hologram [L]
│   └── add a card every round while scaling Hologram
└── Marble Joker + Hologram [L]
    └── add a Stone card every Blind for automatic Hologram scaling

Driver's License Enhancement-Density [L]
    └── rapidly create enough enhanced cards to activate and maintain Driver's License XMult

Blue Joker Large-Deck Chips [L]
    └── intentionally tolerate/grow deck size when remaining-deck Chips remain strategically valuable
```

DNA itself is not a standalone strategy. It is a card-copy engine used by concrete leaves such as DNA/Scholar Aces, Hologram growth, Stone duplication, Baron/Mime King concentration, and rank-copy poker hands.

---

## 8. Planet, Tarot, and consumable engines

```text
Constellation Planet-Scaling [L]
    └── buy/use Planets repeatedly to grow Constellation XMult while reinforcing the chosen hand

Perkeo Consumable Duplication [I]
├── Perkeo + Observatory Planet Stack [L]
│   └── duplicate the chosen Planet and exploit Observatory held-Planet XMult
├── Perkeo + Cryptid Copy Engine [L]
│   └── repeatedly duplicate Cryptid to clone the build's highest-value playing card
└── Perkeo Tarot/Spectral Engine [L]
    └── repeatedly duplicate a transformation consumable that directly advances the established build

Fortune Teller Tarot-Use Scaling [L]
    └── deliberately generate and use Tarots throughout the run to build persistent +Mult

Vagabond Low-Money Tarot Engine [L]
    └── keep cash low enough to repeatedly generate Tarots, accepting the economy tradeoff intentionally
```

---

## 9. Shop, pack, reroll, and blind-skip engines

```text
Campfire Sell-Scaling [L]
    └── buy/sell expendable cards deliberately to grow Campfire during the current Ante

Flash Card Reroll-Scaling [L]
    └── turn repeated shop rerolls into permanent Mult while balancing reroll cost/economy

Red Card Pack-Skip Scaling [L]
    └── open packs primarily to skip their contents and scale Red Card when the skipped value is worthwhile

Throwback Blind-Skip Scaling [L]
    └── intentionally skip selected Blinds because the tag EV and Throwback XMult jointly justify it
```

These leaves are important because they change resource behavior, not merely scoring math.

---

## 10. Joker-board and composition strategies

```text
Joker Stencil Empty-Slot [L]
    └── intentionally preserve empty Joker capacity when Stencil XMult outweighs filling the slots

Baseball Card Uncommon Stack [L]
    └── prefer a board dense with strategically useful Uncommon Jokers to multiply Baseball Card triggers

Abstract Joker Wide-Board [L]
    └── value filling Joker capacity because Abstract Joker scales directly with total Joker count

Swashbuckler Sell-Value Stack [I]
├── Core Swashbuckler [L]
└── Egg / Gift-Card Swashbuckler [L]
    └── deliberately grow Joker sell values and convert them into Swashbuckler Mult
```

Blueprint and Brainstorm are **amplifiers**, not standalone strategy leaves. They inherit value from whichever established leaf has the best copy target.

---

## 11. Discard and hand-rotation engines

```text
Yorick Discard-Scaling [L]
    └── allocate enough discards to trigger repeated Yorick upgrades without sacrificing blind survival

Obelisk Hand-Rotation [L]
    └── establish a most-played hand, then deliberately avoid it long enough to scale Obelisk without resetting

Green Joker No-Discard Scaling [L]
    └── prioritize playing rather than discarding so Green Joker scales continuously

Burnt Joker Hand-Level Engine [L]
    └── deliberately make the first discard represent the hand type being permanently leveled
```

`Burnt Joker Hand-Level Engine` can coexist with poker-hand leaves. For example, it may strongly reinforce Core High Card, Pair, Straight, or another selected poker-hand strategy without forcing a separate poker-hand transition.

---

## 12. Explicitly cross-cutting combinations

The following are **not extra parent edges**. They are important compatibility relationships that the later Gold/Silver/Bronze/Banned audit must represent across nodes:

```text
Baron-Mime High Card        <-> Steel / Red Seal / DNA / hand-size support
PhotoChad                   <-> Face Cards / Lucky / Glass / Red Seal
Triboulet + Sock and Buskin <-> Face Cards / Red Seal / Glass
Bloodstone Hearts           <-> Oops! All 6s / retriggers / Lucky
Marble Joker                <-> Stone / Hologram / Vampire / Driver's License
DNA                         <-> Aces / Stone / Hologram / Baron / Five of a Kind / Flush Five / Vampire
Pareidolia                  <-> Face scoring / Canio / Midas Mask / Vampire
Perkeo                      <-> chosen Planet / Cryptid / transformation consumables
Blueprint / Brainstorm      <-> strongest copyable engine in the current dominant leaf
```

These relationships are why a component may contribute evidence to several leaves even though the tree itself avoids fake multiple-parent topology.

---

## 13. Tree-freeze boundary

Before the Gold/Silver/Bronze/Banned catalogue begins, this file should be reviewed for:

```text
1. missing major/popular effective strategies
2. false leaves that are only minor two-Joker synergies
3. branches that should be split further because they make materially different decisions
4. branches that should be merged because they behave the same
5. incorrect parent-child relationships
6. missing Core/fallback leaves where a split parent can still be valid on its own
```

After topology freeze, tier assignment proceeds **node by node**, beginning with the High Card tree.
