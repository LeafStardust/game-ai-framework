# Balatro Strategy Relationships

> Canonical relationship/audit companion to [`BALATRO_STRATEGY_TREE.md`](BALATRO_STRATEGY_TREE.md). The tree file owns topology. [`BALATRO_STRATEGY_TREE_RULES.md`](BALATRO_STRATEGY_TREE_RULES.md) owns scoring/propagation semantics. This file owns **where Gold/Silver/Bronze/Banned/conditional evidence belongs** as the node-by-node audit proceeds.
>
> A tier is **strategy evidence**, not generic Joker/item power. Generic strength remains in the ordinary value evaluators.

## Status legend

- **Complete** — relationship ownership for this node is audited and authoritative for the current production migration.
- **In progress** — some relationships are authoritative, but the node/branch still has an explicitly named pending slice.
- **Pending** — topology is frozen, but exact tier ownership is not yet audited. `TBD` means deliberately unresolved; legacy flat tiers are not authoritative for the tree node.
- `—` means the audited node intentionally owns no relationship in that tier.

## Multi-node ownership and cross-link rule

A Joker, consumable, structural feature, or other component may be relevant to more than one strategy node. Relevance alone does **not** justify duplicate evidence.

1. Prefer one semantic owner when the same component means the same thing in both places.
2. A component may appear on multiple nodes only when each occurrence has a **different payoff and a distinct qualifying requirement/state** documented here.
3. A shared component must not activate two leaves merely because both leaf names mention it. Each leaf must independently satisfy its own qualifying evidence.
4. A defining Gold relationship should normally be tied to the node's actual payoff engine. Shared generic support is more often Silver/Bronze or a cross-link.
5. If two leaves would be activated by the exact same component set and state for the exact same reason, that is a relationship-ownership defect. Assign one owner or, if the topology truly cannot distinguish the policies, raise a topology defect rather than double-counting.
6. Cross-links describe compatibility; they are not parent edges and do not automatically add score.

### Important overlap examples

- **Glass Joker Breakage Scaling ↔ Glass Canio** — `Glass Joker Breakage` owns Glass destruction when breaking Glass is itself the scaling payoff. `Glass Canio` owns the route only when **Canio** is the payoff and Glass **face cards** provide the destruction mechanism. Glass cards alone must not activate both leaves.
- **Core Enhancement-Feed Vampire ↔ Midas Mask + Vampire** — Core Vampire requires a reliable generic enhancement-feed loop. The Midas leaf specifically requires **Midas Mask + Vampire** and treats generated Gold enhancements as temporary feed. Persistent Gold-card economy belongs to the Gold Cards branch instead.
- **Midas Mask Gold Generation ↔ Midas Mask + Vampire** — Gold Cards/Midas is about creating/retaining Gold-card value. Midas+Vampire is about deliberately consuming those enhancements for Vampire scaling. The same Midas ownership does not prove both policies without the corresponding payoff state.
- **Marble Joker + Vampire Stone Feed ↔ Core Vampire** — the Stone leaf requires **Marble-driven Stone replenishment + Vampire** and a usable Stone-feed loop. Generic Vampire does not receive duplicate Stone evidence merely because Marble exists; if Stone feed is the dominant mechanism, the Stone leaf is the specific realization.
- **Pareidolia Canio ↔ Pareidolia + Midas Mask + Vampire** — Pareidolia is shared support, but the defining payoff differs: destroyed face cards for Canio versus Midas-generated enhancements consumed by Vampire. The partner engine is part of the leaf requirement.
- **Trading Card Canio ↔ Trading Card Thinning/Economy** — Trading Card can support both only when the run actually has both distinct payoffs: Canio face-card destruction and deck-thinning/economy value. Trading Card ownership alone is not defining Canio evidence.

---

## 1. Poker-hand strategies

| Node | Status | Gold | Silver | Bronze | Banned | Conditional / structural |
|---|---|---|---|---|---|---|
| High Card `[I]` | Complete | Burnt Joker; Pluto (Planet) | Card Sharp; Supernova; Space Joker; Half Joker; Green Joker; Burglar | — | Obelisk **conditional** | Obelisk only when non-history High Card commitment exists and High Card is currently tied/most-played. Play count is never positive strategy evidence. |
| Core Repetition / Level High Card `[L]` | Complete | — | — | — | — | True fallback. Owns no direct evidence; inherits High Card foundation and is suppressed by an established specific sibling. |
| Stuntman / Small-Hand High Card `[L]` | Complete | Stuntman | — | — | — | Stuntman is separately Banned for Baron-Mime only when that held engine is materially established. |
| Baron-Mime Steel-King High Card `[L]` | Complete | — | Baron*; Mime*; Blackboard; Shoot the Moon; Troubadour; Juggler; The Chariot (consumable) | Raised Fist; Reserved Parking | Stuntman* | `*` Baron/Mime require real held-King support/partner state. Preferred structure: Steel, Red Seal, Kings, face cards. Stuntman conflict requires a material held-card engine, not one isolated Steel King. |
| Pair `[L]` | Complete | The Duo; Mercury (Planet) | Jolly Joker; Sly Joker | — | Obelisk **conditional** | Half Joker, Supernova, Card Sharp, Space Joker, Burnt Joker become Silver only after independent Pair evidence (Pair level or Duo/Jolly/Sly). Pair play count is not evidence. |
| Two Pair `[I]` | In progress | Uranus (Planet) | Mad Joker; Clever Joker | — | Obelisk **conditional** | The Duo, Jolly, Sly, Supernova, Card Sharp, Space Joker, Burnt Joker become Silver only after independent Two Pair evidence. Play count is used only for Obelisk's mechanic. |
| Core Two Pair `[L]` | Complete | — | — | — | — | True fallback; owns no direct evidence and inherits Two Pair parent foundation. |
| Spare Trousers + Square Joker Two Pair `[L]` | In progress | Spare Trousers | TBD: Square Joker audit next | TBD | TBD | Spare Trousers is already defining because it explicitly scales from Two Pair. Square Joker relationship/requirements remain the next slice. |
| Three of a Kind `[I]` | Pending | TBD | TBD | TBD | TBD | Parent owns broad Trips evidence after audit. |
| Core Three of a Kind `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback leaf. |
| DNA / Cryptid Rank-Copy Three of a Kind `[L]` | Pending | TBD | TBD | TBD | TBD | Must require rank-copy structure that materially supports Trips; DNA/Cryptid ownership alone must not imply natural hand progression. |
| Straight `[I]` | Pending | TBD | TBD | TBD | TBD | Parent broad Straight evidence. |
| Core Straight `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback leaf. |
| Shortcut / Four Fingers Straight `[L]` | Pending | TBD | TBD | TBD | TBD | Distinct consistency/rule-modification route. |
| Runner Scaling Straight `[L]` | Pending | TBD | TBD | TBD | TBD | Runner payoff requires repeated Straight scoring. |
| Superposition Ace-Straight Tarot `[L]` | Pending | TBD | TBD | TBD | TBD | Requires Ace-ending Straight feasibility plus Superposition Tarot payoff. |
| Flush `[I]` | Pending | TBD | TBD | TBD | TBD | Suit concentration alone is cross-cutting and must not blindly activate Flush. |
| Core Flush `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback leaf. |
| Smeared / Four Fingers Consistency Flush `[L]` | Pending | TBD | TBD | TBD | TBD | Rule/consistency realization. |
| Full House `[L]` | Pending | TBD | TBD | TBD | TBD | Standalone leaf. |
| Four of a Kind `[I]` | Pending | TBD | TBD | TBD | TBD | Parent broad Quads evidence. |
| Core Four of a Kind `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback leaf. |
| DNA / Cryptid Rank-Copy Four of a Kind `[L]` | Pending | TBD | TBD | TBD | TBD | Requires concrete rank concentration/copy feasibility. |
| Straight Flush `[I]` | Pending | TBD | TBD | TBD | TBD | No natural transition credit from Straight or Flush. |
| Core Straight Flush `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback leaf. |
| Shortcut / Four Fingers / Smeared Straight Flush `[L]` | Pending | TBD | TBD | TBD | TBD | Consistency/rule-modification route. |
| Seance Straight-Flush Spectral Engine `[L]` | Pending | TBD | TBD | TBD | TBD | Requires actual Straight-Flush feasibility/use, not Seance ownership alone. |
| Five of a Kind `[I]` | Pending | TBD | TBD | TBD | TBD | Parent broad Five-Kind evidence. |
| Core Five of a Kind `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback leaf. |
| DNA / Cryptid Rank-Copy Five of a Kind `[L]` | Pending | TBD | TBD | TBD | TBD | Requires rank density/copy support. |
| Flush House `[L]` | Pending | TBD | TBD | TBD | TBD | Standalone leaf. |
| Flush Five `[I]` | Pending | TBD | TBD | TBD | TBD | Exact-card concentration branch. |
| Core Flush Five `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback leaf. |
| DNA / Cryptid Exact-Card Flush Five `[L]` | Pending | TBD | TBD | TBD | TBD | Requires exact rank+suit copy concentration. |
| The Idol Monoculture Flush Five `[L]` | Pending | TBD | TBD | TBD | TBD | Idol target must match meaningful exact-card concentration; arbitrary rolled target is not evidence. |
| Four-Card Hand Spam `[I]` | Pending | TBD | TBD | TBD | TBD | Broad four-card policy foundation. |
| Square Joker Four-Card Chips `[L]` | Pending | TBD | TBD | TBD | TBD | Square scales from exactly four played cards, independent of Two Pair. |
| Square + Green Joker Four-Card Spam `[L]` | Pending | TBD | TBD | TBD | TBD | Requires both four-card Square scaling and no-discard Green scaling. |

## 2. Rank and face-card strategies

| Node | Status | Gold | Silver | Bronze | Banned | Conditional / structural |
|---|---|---|---|---|---|---|
| Aces `[I]` | Pending | TBD | TBD | TBD | TBD | Broad Ace structure. |
| Scholar Ace Scoring `[L]` | Pending | TBD | TBD | TBD | TBD | Scholar payoff. |
| DNA + Scholar Ace Concentration `[L]` | Pending | TBD | TBD | TBD | TBD | Requires actual Ace concentration/copy support. |
| Low-Rank Scoring `[I]` | Pending | TBD | TBD | TBD | TBD | Broad low-rank foundation. |
| Fibonacci Low-Rank Scoring `[L]` | Pending | TBD | TBD | TBD | TBD | Fibonacci rank set is defining structure. |
| Hack + Fibonacci Retrigger `[L]` | Pending | TBD | TBD | TBD | TBD | Requires retriggerable low-rank Fibonacci targets. |
| Twos `[I]` | Pending | TBD | TBD | TBD | TBD | Broad Two-density foundation. |
| Wee Joker Twos `[L]` | Pending | TBD | TBD | TBD | TBD | Wee payoff. |
| Wee Joker + Hack Retrigger Twos `[L]` | Pending | TBD | TBD | TBD | TBD | Requires Wee + retriggerable Twos. |
| Sixes / Sixth Sense `[L]` | Pending | TBD | TBD | TBD | TBD | Sixth Sense consumption policy. |
| Jacks / Hit the Road `[L]` | Pending | TBD | TBD | TBD | TBD | Jack discard/scaling policy. |
| Queens / Shoot the Moon `[L]` | Pending | TBD | TBD | TBD | TBD | Held-Queen payoff. |
| Face Cards `[I]` | Pending | TBD | TBD | TBD | TBD | Broad face-card foundation. |
| Core Face-Card Scoring `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback leaf. |
| Photograph + Hanging Chad (PhotoChad) `[L]` | Pending | TBD | TBD | TBD | TBD | First-scored face-card retrigger payoff. |
| Triboulet + Sock and Buskin `[L]` | Pending | TBD | TBD | TBD | TBD | K/Q face retrigger payoff. |
| Pareidolia Universal Face Scoring `[L]` | Pending | TBD | TBD | TBD | TBD | Pareidolia changes face eligibility; partner payoff still required. |
| Held Face-Card Economy `[L]` | Pending | TBD | TBD | TBD | TBD | Held-face economy mechanics. |
| Business Card Face Economy `[L]` | Pending | TBD | TBD | TBD | TBD | Scored face-card economy; distinct from held-face economy. |
| Faceless / No-Face `[I]` | Pending | TBD | TBD | TBD | TBD | Broad deliberate no-face policy. |
| Ride the Bus No-Face Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Requires avoiding scored face cards. |
| Faceless Joker Discard Economy `[L]` | Pending | TBD | TBD | TBD | TBD | Requires discardable face-card supply, not no-face deck absence. |
| The Idol Exact-Card Concentration `[L]` | Pending | TBD | TBD | TBD | TBD | Exact current Idol target concentration. |

## 3. Suit and held-card strategies

| Node | Status | Gold | Silver | Bronze | Banned | Conditional / structural |
|---|---|---|---|---|---|---|
| Hearts `[I]` | Pending | TBD | TBD | TBD | TBD | Broad Hearts structure; independent from Flush. |
| Core Hearts Scoring `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback leaf. |
| Bloodstone + Oops! All 6s Hearts `[L]` | Pending | TBD | TBD | TBD | TBD | Probability amplification route. |
| Bloodstone Retrigger Hearts `[L]` | Pending | TBD | TBD | TBD | TBD | Retrigger-heavy Hearts payoff. |
| Diamonds `[I]` | Pending | TBD | TBD | TBD | TBD | Broad Diamonds structure. |
| Core Diamonds Scoring `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback leaf. |
| Rough Gem Diamond Economy / Scoring `[L]` | Pending | TBD | TBD | TBD | TBD | Diamond scoring/economy payoff. |
| Clubs `[I]` | Pending | TBD | TBD | TBD | TBD | Broad Clubs structure. |
| Core Clubs Scoring `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback leaf. |
| Onyx Agate / Seeing Double Clubs `[L]` | Pending | TBD | TBD | TBD | TBD | Seeing Double requires compatible mixed/effective-suit trigger structure. |
| Spades `[I]` | Pending | TBD | TBD | TBD | TBD | Broad Spades structure. |
| Core Spades Scoring `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback leaf. |
| Arrowhead Spade Chips `[L]` | Pending | TBD | TBD | TBD | TBD | Spade-chip payoff. |
| Blackboard Held-Black Cards `[L]` | Pending | TBD | TBD | TBD | TBD | Held Spade/Club preservation. |
| Ancient Joker Suit-Rotation `[I]` | Pending | TBD | TBD | TBD | TBD | Current suit rotation is state-dependent. |
| Core Ancient Joker Suit-Rotation `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback rotation route. |
| Ancient + Smeared Suit-Rotation `[L]` | Pending | TBD | TBD | TBD | TBD | Smeared broadens effective suit compatibility. |
| Flower Pot Multi-Suit `[I]` | Pending | TBD | TBD | TBD | TBD | Multi-suit scoring foundation. |
| Splash + Flower Pot `[L]` | Pending | TBD | TBD | TBD | TBD | Splash makes all played cards score for Flower Pot coverage. |
| Smeared Joker + Flower Pot `[L]` | Pending | TBD | TBD | TBD | TBD | Effective-suit simplification route. |
| Smeared + Splash + Flower Pot `[L]` | Pending | TBD | TBD | TBD | TBD | Combined coverage route. |

## 4. Enhancement strategies

| Node | Status | Gold | Silver | Bronze | Banned | Conditional / structural |
|---|---|---|---|---|---|---|
| Stone `[I]` | Pending | TBD | TBD | TBD | TBD | Broad Stone-card foundation. |
| Marble Joker + Stone Joker Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Stone creation + Stone-density payoff. |
| Marble Joker + Vampire Stone Feed `[L]` | Pending | TBD | TBD | TBD | TBD | Requires Marble replenishment plus Vampire consuming Stone enhancements; cross-link to Vampire, no duplicate generic Vampire evidence. |
| DNA + Stone Joker Duplication `[L]` | Pending | TBD | TBD | TBD | TBD | Requires copyable Stone structure. |
| Stone High Card `[L]` | Pending | TBD | TBD | TBD | TBD | Stone scoring used as High Card realization; cross-link does not create natural hand progression. |
| Glass `[I]` | Pending | TBD | TBD | TBD | TBD | Broad Glass-card foundation. |
| Glass Joker Breakage Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Glass destruction is the payoff; cross-link to Glass Canio only when Canio payoff also exists. |
| Glass Retrigger Scoring `[L]` | Pending | TBD | TBD | TBD | TBD | Retain/retrigger Glass rather than primarily destroy for Glass Joker scaling. |
| Steel `[I]` | Pending | TBD | TBD | TBD | TBD | Broad held-Steel foundation. |
| Core Steel Held-Card Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback Steel route. |
| Steel Joker Density Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Steel-card density payoff. |
| Mime Steel Retrigger `[L]` | Pending | TBD | TBD | TBD | TBD | Held Steel retrigger payoff; cross-link to Baron-Mime only with its King-specific requirements. |
| Lucky `[I]` | Pending | TBD | TBD | TBD | TBD | Broad Lucky structure. |
| Lucky Cat Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Lucky trigger accumulation. |
| Lucky Cat + Oops! All 6s `[L]` | Pending | TBD | TBD | TBD | TBD | Probability-amplified Lucky route. |
| Lucky Retrigger `[L]` | Pending | TBD | TBD | TBD | TBD | Retrigger-heavy Lucky route. |
| Gold Cards `[I]` | Pending | TBD | TBD | TBD | TBD | Broad Gold enhancement foundation. |
| Held Gold + Mime Economy `[L]` | Pending | TBD | TBD | TBD | TBD | Held-card money retriggers. |
| Golden Ticket Gold Scoring `[L]` | Pending | TBD | TBD | TBD | TBD | Scored Gold-card economy. |
| Midas Mask Gold Generation `[L]` | Pending | TBD | TBD | TBD | TBD | Persistent Gold generation payoff. |
| Midas Mask + Golden Ticket Economy `[L]` | Pending | TBD | TBD | TBD | TBD | Midas generation feeding scored Gold economy. |

## 5. Seal strategies

| Node | Status | Gold | Silver | Bronze | Banned | Conditional / structural |
|---|---|---|---|---|---|---|
| Red Seal `[I]` | Pending | TBD | TBD | TBD | TBD | Broad Red-Seal foundation. |
| Played Red-Seal Retrigger `[L]` | Pending | TBD | TBD | TBD | TBD | Played-card retrigger targets. |
| Held Red-Seal Retrigger `[L]` | Pending | TBD | TBD | TBD | TBD | Held-card retrigger targets. |
| Blue Seal Hand-Level Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | End-of-round hand-level investment. |
| Purple Seal Tarot Engine `[L]` | Pending | TBD | TBD | TBD | TBD | Discard-trigger Tarot generation. |
| Gold Seal Economy `[I]` | Pending | TBD | TBD | TBD | TBD | Broad scored Gold-Seal economy. |
| Core Gold-Seal Scoring Economy `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback Gold-Seal route. |
| Gold-Seal Retrigger Economy `[L]` | Pending | TBD | TBD | TBD | TBD | Retriggered Gold-Seal payout route. |

## 6. Destruction, sacrifice, consumption, and thinning

| Node | Status | Gold | Silver | Bronze | Banned | Conditional / structural |
|---|---|---|---|---|---|---|
| Canio Destruction `[I]` | Pending | TBD | TBD | TBD | TBD | Broad destroyed-face-card Canio foundation. |
| Trading Card Canio `[L]` | Pending | TBD | TBD | TBD | TBD | Requires Canio + Trading Card and a face-card destruction path. Trading Card alone belongs primarily to thinning/economy. |
| Pareidolia Canio `[L]` | Pending | TBD | TBD | TBD | TBD | Requires Canio + Pareidolia so destroyed eligible cards feed Canio. |
| Glass Canio `[L]` | Pending | TBD | TBD | TBD | TBD | Requires Canio + destructible Glass **face cards**; Glass alone belongs to Glass strategy. |
| Consumable Canio `[L]` | Pending | TBD | TBD | TBD | TBD | Requires Canio plus a repeatable public consumable destruction route for face cards. |
| Vampire `[I]` | Pending | TBD | TBD | TBD | TBD | Broad enhancement-consumption foundation. |
| Core Enhancement-Feed Vampire `[L]` | Pending | TBD | TBD | TBD | TBD | Generic reliable enhancement feed; should not duplicate a more specific Midas/Stone feed realization. |
| Midas Mask + Vampire `[L]` | Pending | TBD | TBD | TBD | TBD | Requires Midas + Vampire; generated Gold is temporary feed, not persistent Gold-card economy evidence. |
| Pareidolia + Midas Mask + Vampire `[L]` | Pending | TBD | TBD | TBD | TBD | Requires all three pieces; Pareidolia broadens Midas generation before Vampire consumes enhancements. |
| Ceremonial Dagger Sacrifice `[I]` | Pending | TBD | TBD | TBD | TBD | Broad intentional Joker-sacrifice foundation. |
| Core Dagger Sacrifice `[L]` | Pending | TBD | TBD | TBD | TBD | Requires expendable Joker value below sacrifice payoff. |
| Riff-Raff / Disposable-Joker Dagger Feed `[L]` | Pending | TBD | TBD | TBD | TBD | Requires a replenishable disposable-Joker source. |
| Madness Destruction `[I]` | Pending | TBD | TBD | TBD | TBD | Broad Madness policy. |
| Solo Madness `[L]` | Pending | TBD | TBD | TBD | TBD | Low/empty companion-board route. |
| Eternal-Joker Madness `[L]` | Pending | TBD | TBD | TBD | TBD | Eternal companions survive Madness destruction. |
| Deck Thinning `[I]` | Pending | TBD | TBD | TBD | TBD | Broad deliberate deck-reduction foundation. |
| Trading Card Thinning / Economy `[L]` | Pending | TBD | TBD | TBD | TBD | Trading Card destruction primarily valued for thinning/economy. |
| Erosion Thinning `[L]` | Pending | TBD | TBD | TBD | TBD | Reduced deck size is the Erosion payoff. |
| Trading Card + Erosion `[L]` | Pending | TBD | TBD | TBD | TBD | Trading Card directly advances Erosion's reduced-deck payoff. |

## 7. Deck-growth, card-addition, and card-training engines

| Node | Status | Gold | Silver | Bronze | Banned | Conditional / structural |
|---|---|---|---|---|---|---|
| Hologram Deck-Growth `[I]` | Pending | TBD | TBD | TBD | TBD | Broad added-card Hologram foundation. |
| Core Hologram Growth `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback growth route. |
| DNA + Hologram `[L]` | Pending | TBD | TBD | TBD | TBD | DNA card-addition route. |
| Certificate + Hologram `[L]` | Pending | TBD | TBD | TBD | TBD | Certificate card-addition route. |
| Marble Joker + Hologram `[L]` | Pending | TBD | TBD | TBD | TBD | Marble Stone generation as deck-growth feed, distinct from Stone payoff. |
| Hiker Card Training `[I]` | Pending | TBD | TBD | TBD | TBD | Broad permanent-card training foundation. |
| Core Hiker Card Training `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback Hiker route. |
| Hiker Retrigger / Copy Training `[L]` | Pending | TBD | TBD | TBD | TBD | Repeated triggers/copies concentrate permanent card upgrades. |
| Driver's License Enhancement-Density `[L]` | Pending | TBD | TBD | TBD | TBD | Requires enough enhanced cards for License payoff. |
| Blue Joker Large-Deck Chips `[L]` | Pending | TBD | TBD | TBD | TBD | Large remaining-deck chip payoff. |

## 8. Planet, Tarot, and consumable engines

| Node | Status | Gold | Silver | Bronze | Banned | Conditional / structural |
|---|---|---|---|---|---|---|
| Planet Engine `[I]` | Pending | TBD | TBD | TBD | TBD | Broad Planet-use/investment foundation. |
| Constellation Planet-Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Planet use grows Constellation. |
| Satellite Planet-Economy `[L]` | Pending | TBD | TBD | TBD | TBD | Unique Planet discovery/use economy. |
| Constellation + Satellite Planet Engine `[L]` | Pending | TBD | TBD | TBD | TBD | Both Planet scaling and economy payoffs. |
| Perkeo Consumable Duplication `[I]` | Pending | TBD | TBD | TBD | TBD | Broad duplicated-consumable foundation. |
| Perkeo + Observatory Planet Stack `[L]` | Pending | TBD | TBD | TBD | TBD | Requires Observatory/Planet held-stack payoff. |
| Perkeo + Cryptid Copy Engine `[L]` | Pending | TBD | TBD | TBD | TBD | Requires Cryptid duplication payoff. |
| Perkeo Tarot / Spectral Engine `[L]` | Pending | TBD | TBD | TBD | TBD | Requires useful repeated Tarot/Spectral transformation target. |
| Fortune Teller Tarot-Use Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Tarot-use accumulation payoff. |
| Vagabond Low-Money Tarot Engine `[L]` | Pending | TBD | TBD | TBD | TBD | Requires deliberate low-money operating state. |

## 9. Economy, shop, pack, reroll, and blind-skip engines

| Node | Status | Gold | Silver | Bronze | Banned | Conditional / structural |
|---|---|---|---|---|---|---|
| Cash Hoard / Interest `[I]` | Pending | TBD | TBD | TBD | TBD | Broad cash-reserve foundation. |
| Core Cash-Reserve Economy `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback reserve route. |
| Rocket / To the Moon Cash Growth `[L]` | Pending | TBD | TBD | TBD | TBD | Cash growth/interest payoff. |
| Bull Cash-to-Chips `[L]` | Pending | TBD | TBD | TBD | TBD | Cash retained as chip scaling. |
| Bootstraps Cash-to-Mult `[L]` | Pending | TBD | TBD | TBD | TBD | Cash retained as Mult scaling. |
| Bull + Bootstraps Cash Scoring `[L]` | Pending | TBD | TBD | TBD | TBD | Combined cash scoring payoff. |
| Cloud 9 Nines Economy `[L]` | Pending | TBD | TBD | TBD | TBD | Nine-density economy payoff. |
| Campfire Sell-Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Intentional sell loop. |
| Flash Card Reroll-Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Reroll spending is the scaling action. |
| Red Card Pack-Skip Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Pack-content skipping is the scaling action. |
| Throwback Blind-Skip Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Blind skipping is the scaling action; D13 opportunity cost remains authoritative. |

## 10. Joker-board and composition strategies

| Node | Status | Gold | Silver | Bronze | Banned | Conditional / structural |
|---|---|---|---|---|---|---|
| Joker Stencil `[I]` | Pending | TBD | TBD | TBD | TBD | Broad deliberate empty-slot foundation. |
| Core Joker Stencil Empty-Slot `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback Stencil route. |
| Joker Stencil + Ankh / Invisible Duplication `[L]` | Pending | TBD | TBD | TBD | TBD | Duplication used to multiply Stencil while preserving beneficial emptiness. |
| Baseball Card Uncommon Stack `[L]` | Pending | TBD | TBD | TBD | TBD | Uncommon-Joker board composition. |
| Abstract Joker Wide-Board `[L]` | Pending | TBD | TBD | TBD | TBD | Wide occupied Joker board payoff. |
| Swashbuckler Sell-Value Stack `[I]` | Pending | TBD | TBD | TBD | TBD | Broad sell-value accumulation. |
| Core Swashbuckler `[L]` | Pending | TBD | TBD | TBD | TBD | Fallback Swashbuckler route. |
| Egg / Gift-Card Swashbuckler `[L]` | Pending | TBD | TBD | TBD | TBD | Deliberately grows Joker sell value for Swashbuckler. |

## 11. Discard, no-discard, and hand-rotation engines

| Node | Status | Gold | Silver | Bronze | Banned | Conditional / structural |
|---|---|---|---|---|---|---|
| Discard Utilization `[I]` | Pending | TBD | TBD | TBD | TBD | Broad value-from-discard foundation. |
| Castle Suit-Discard Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Current Castle suit target matters. |
| Mail-In Rebate Rank-Discard Economy `[L]` | Pending | TBD | TBD | TBD | TBD | Current rank target matters. |
| Yorick Discard-Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Repeated discard volume payoff. |
| No-Discard / Discard-Preservation `[I]` | Pending | TBD | TBD | TBD | TBD | Broad avoid/preserve-discard foundation. |
| Green Joker No-Discard Scaling `[L]` | Pending | TBD | TBD | TBD | TBD | Avoid discarding to preserve/grow Mult. |
| Banner + Delayed Gratification Discard Reserve `[L]` | Pending | TBD | TBD | TBD | TBD | Unused discard count has direct payoff. |
| Ramen Preservation `[L]` | Pending | TBD | TBD | TBD | TBD | Avoid discard-caused XMult decay. |
| Burglar Zero-Discard / Extra-Hand `[L]` | Pending | TBD | TBD | TBD | TBD | Converts discard economy into extra hands. |
| Obelisk Hand-Rotation `[L]` | Pending | TBD | TBD | TBD | TBD | Play counts are allowed here because Obelisk explicitly depends on most-played-hand history. |
| Burnt Joker Hand-Level Engine `[L]` | Pending | TBD | TBD | TBD | TBD | First-discard hand-level growth; distinct from generic High Card/Pair support. |

## 12. Hand-scheduling engines

| Node | Status | Gold | Silver | Bronze | Banned | Conditional / structural |
|---|---|---|---|---|---|---|
| Last-Hand Burst `[I]` | Pending | TBD | TBD | TBD | TBD | Broad last-hand payoff foundation. |
| Acrobat Last-Hand XMult `[L]` | Pending | TBD | TBD | TBD | TBD | Last-hand XMult payoff; survival remains superior. |
| Dusk Last-Hand Retrigger `[L]` | Pending | TBD | TBD | TBD | TBD | Last-hand retrigger payoff; survival remains superior. |

---

## Cross-cutting links that are not duplicate evidence

These links are compatibility reminders only. They do not automatically add relationship score.

- Baron-Mime High Card ↔ Steel / Red Seal / DNA / hand-size support / Shoot the Moon
- PhotoChad ↔ Face Cards / Lucky / Glass / Red Seal / Hiker
- Triboulet + Sock and Buskin ↔ Face Cards / Red Seal / Glass
- Bloodstone Hearts ↔ Oops! All 6s / retriggers / Lucky
- Marble Joker ↔ Stone / Hologram / Vampire / Driver's License
- DNA ↔ Aces / Stone / Hologram / Baron / Trips / Quads / Five Kind / Flush Five / Vampire
- Pareidolia ↔ Face scoring / Canio / Midas Mask / Vampire
- Perkeo ↔ chosen Planet / Cryptid / transformation consumables
- Blueprint / Brainstorm ↔ strongest copyable engine in the active leaf
- Cash Hoard ↔ Bull / Bootstraps / Rocket / To the Moon / Cloud 9 / economy sources
- Discard Utilization ↔ Castle / Mail-In Rebate / Purple Seal / Hit the Road / Faceless / Yorick
- No-Discard ↔ Green Joker / Banner / Delayed Gratification / Ramen / Burglar
- Hack / Fibonacci ↔ Twos / low-rank shaping / retriggers
- Hiker ↔ compact-deck shaping / retriggers / DNA / high-value scoring cards
- Blackboard ↔ Spades / Clubs / High Card / Pair / held-card preservation
- Planet Engine ↔ Constellation / Satellite / Blue Seal / Astronomer / poker-hand investment
- Business Card ↔ Face Cards / Pareidolia / retriggers / Red Seal
- Midas + Golden Ticket ↔ Face Cards / Gold Cards / retriggers
- Ancient Joker ↔ suit flexibility / Smeared Joker
- Joker Stencil ↔ Ankh / Invisible Joker / Negative Jokers / deliberate empty slots

## Maintenance rule

Every node in the frozen topology must have an entry in this file. When a node audit becomes green:

1. replace its `TBD` fields with the exact audited tiers/conditions;
2. state any required structural evidence explicitly;
3. add cross-links for repeated components without duplicating evidence blindly;
4. mark the node/branch Complete only after its focused deterministic gate is green;
5. keep `BALATRO_STRATEGY_TREE.md` topology-only and update this file rather than burying tier ownership in runtime code alone.
