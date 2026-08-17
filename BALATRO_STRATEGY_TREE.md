# Balatro Strategy Tree

> **v1.0F design draft — authoritative for the strategy-tree redesign, but not yet the runtime implementation.**
>
> This document replaces the previous flat strategy-playbook documents. Do not begin the Gold/Silver/Bronze/Banned catalogue rewrite until this tree is reviewed and frozen.

## 1. Core model

Balatro strategy is represented as a **forest of strategy trees**: multiple independent roots, each of which may specialize into more specific descendants.

A parent -> child edge means only:

> the child is a more specific realization of the parent strategy and therefore requires or benefits from the parent's strategic foundation.

It does **not** mean:

- the child is globally stronger than the parent;
- the child is a later poker hand in a natural progression;
- the agent should automatically move downward;
- Pair naturally becomes Three of a Kind, Four of a Kind, etc.;
- every strategy must have children.

Poker-hand adjacency is never strategy evidence. A pivot between different poker-hand roots happens only because the current build creates stronger evidence for another root/leaf.

Cross-cutting synergies do not create fake multi-parent trees. For example, Steel and Red Seal may strongly support Baron-Mime High Card, but they remain independent strategies/components rather than additional parents of Baron-Mime.

---

## 2. Node terminology and ranking

- **Root** — broadest strategy in one tree.
- **Internal node** — a strategy with one or more children.
- **Leaf** — the deepest defined strategy on a branch. A root with no children is also a leaf.
- **Core/fallback leaf** — an explicit leaf used when a split root remains strategically valid without satisfying any more-specific child.

### Only leaves are ranked

Internal nodes never consume positions in the actionable strategy ranking.

Example:

```text
High Card                         [internal]
├── Core High Card               [leaf]
├── Stuntman High Card           [leaf]
└── Baron-Mime High Card         [leaf]
```

If Baron-Mime is the strongest High Card realization, the ranking contains `Baron-Mime High Card`; it does not separately contain `High Card` as another ranked strategy.

The internal High Card score still matters because it is the strategic foundation inherited by eligible High Card leaves.

A core/fallback leaf is suppressed once a sufficiently established more-specific sibling leaf exists. This prevents `Core High Card` from occupying a second ranking slot beside an already established `Stuntman High Card` or `Baron-Mime High Card`.

---

## 3. Evidence and score model

Every node will eventually own its own exact Gold/Silver/Bronze/Banned relationships, structural evidence, conditions, and support rules.

The redesign separates three concepts.

### 3.1 Direct evidence

`direct_evidence(node)` is evidence that belongs to that exact node.

Examples:

- a broad High Card component may contribute directly to the High Card root;
- Stuntman-specific evidence belongs to the Stuntman High Card leaf;
- Baron/Mime-specific evidence belongs to the Baron-Mime High Card leaf.

A more-specific component should normally provide stronger evidence to its exact leaf than broad parent components provide through inherited foundation.

### 3.2 Branch/foundation score

Internal nodes maintain a non-ranked foundation/branch score for diagnostics and descendant readiness.

Specific descendant evidence propagates **upward with decay** so that an early lucky leaf package also establishes its ancestors.

Conceptually:

```text
Baron-Mime direct evidence        100%
        -> High Card foundation   discounted
```

If additional internal levels later exist, each upward edge applies further decay.

Exact propagation coefficients are intentionally not frozen yet.

### 3.3 Effective leaf score

Only leaves receive an actionable `effective_score`.

Conceptually:

```text
leaf effective score
=
leaf direct evidence
+ eligible inherited ancestor DIRECT foundation
+ leaf structural/current-state evidence
+ environment/deck/stake modifier
- conflicts / unmet requirements
```

Important anti-double-counting rule:

> A leaf must never re-inherit its own evidence after that evidence has propagated upward into an ancestor's branch score.

Therefore descendant propagation may contribute to an ancestor's diagnostic/foundation score, but a leaf inherits only the ancestor's **native/direct** foundation, not the ancestor total containing that same leaf's propagated evidence.

---

## 4. Direction of evidence flow

### Descendant -> ancestor: yes

Strong specific evidence also proves the broader strategy is credible.

```text
Baron + Mime
-> strong Baron-Mime evidence
-> discounted High Card foundation
```

This allows the run to become committed to a deep leaf early when RNG supplies the specific package before the broad foundation is otherwise complete.

### Ancestor -> descendant: not automatically

Broad evidence must not blindly activate every child.

```text
Burnt Joker supports High Card
!= automatically activate Stuntman High Card
!= automatically activate Baron-Mime High Card
```

A non-fallback child must first obtain qualifying child-specific evidence. Once activated, its effective score may inherit appropriate **ancestor direct foundation**.

This makes parent readiness a strong preference rather than a hard gate.

---

## 5. Strategy progression by Ante

### Antes 1-2 — exploration and foundation

- Normal strategy evidence starts at zero unless the deck/environment explicitly supplies evidence.
- Joker candidates retain their independent inherent/meta/survival/economy values.
- Strategy purchase pressure is weak.
- Empty Joker slots should normally be populated with useful Jokers rather than reserved for an imagined perfect build.
- Several roots/leaves may obtain evidence simultaneously.
- A lucky deep package may establish a leaf immediately; the agent does not have to finish the parent first.

### Antes 3-5 — convergence

- Strategy pressure increases.
- Filled Joker slots make replacement decisions strategically meaningful.
- More-specific leaf evidence separates otherwise similar roots.
- The agent increasingly concentrates resources on the strongest root/branch instead of continuing broad exploration.
- A genuinely stronger alternative may still pivot the run if RNG supplies enough current-state evidence.

### Ante 6+ — specialization

- The highest-ranked viable leaf becomes the dominant strategy.
- Up to two compatible, materially supported leaves may remain relevant.
- Purchases, replacement, rerolls, deck shaping, packs, consumables, and hand behavior primarily reinforce this established strategy state.
- Survival and guaranteed blind clears remain above strategic purity.

---

## 6. Poker-hand play count is not strategy evidence

`hand_play_counts` must not contribute to universal strategy inference.

A High Card played several times in early Antes may simply reflect poor draws. By mid/late Antes, persistent build structure already provides better evidence.

Play count remains legal wherever an actual Balatro mechanic explicitly uses it, for example a Joker whose effect depends on played-hand history. The rule is only:

```text
mechanic-specific hand history: allowed
strategy inference from hand count: forbidden
```

Persistent poker-hand investment such as used Planets / actual hand levels may still provide small strategy evidence because that investment remains part of the current run state.

---

## 7. Negative Joker retention rule

Negative Jokers are protected by default because the Negative edition supplies +1 Joker slot and therefore normally removes the slot-opportunity cost of keeping that Joker.

### Default

Do **not** sell or replace a Negative Joker merely because:

- it is Neutral to the dominant strategy;
- another ordinary Joker has better strategic alignment;
- its inherent value has fallen;
- the run is converging and wants cleaner strategy slots.

### Exceptions

A Negative Joker may be removed when its active mechanic materially harms the current run, including when:

1. it directly damages the dominant/relevant strategy;
2. it causes a hard functional contradiction that cannot be safely neutralized by ordering/targeting/play;
3. its expected ongoing harm exceeds the value of keeping the effectively free slot;
4. the active strategy intentionally consumes/sacrifices it and the strategy evaluator proves that trade is worthwhile.

Examples of Jokers requiring contextual treatment include Ceremonial Dagger and Vampire. Their destructive behavior is not automatically considered harmful when the run is intentionally following the corresponding strategy.

A Negative Joker should not be used as sacrificial fodder merely because it is slot-free; intentional destruction needs explicit strategy justification.

---

# 8. Strategy forest — structural draft

Legend:

- `[I]` internal node; never directly ranked.
- `[L]` ranked leaf.
- `[L/new]` new leaf not represented by the old flat catalogue.
- `[L/provisional]` retained structurally for now but requires an explicit keep/remove decision before tree freeze.

## 8.1 Poker-hand trees

```text
High Card [I]
├── Core High Card [L]
│   fallback for an established High Card foundation with no stronger specialization
├── Stuntman / Small-Hand High Card [L]
│   small-hand, Joker-driven and repeated-hand scoring realization
└── Baron-Mime Held-Card High Card [L]
    held Kings / held-card triggers / hand-size preservation realization

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

There are deliberately **no** edges such as:

```text
High Card -> Pair -> Three of a Kind -> Four of a Kind -> Five of a Kind
```

Those are different poker-hand strategies, not specializations of one another.

`Straight Flush`, `Flush House`, and `Flush Five` also remain separate roots rather than being forced under one of their component poker hands. They require multiple structures simultaneously and do not have a single truthful parent.

## 8.2 Face/rank structure

```text
Face Cards [I]
├── Played Face Cards [L]
│   face-card scoring / retrigger realization
└── Held Face Cards [L]
    face-card held-in-hand payoff realization

Faceless / No-Face [L]
Aces [L]
```

The Face Cards split exists because scoring face cards and deliberately retaining face cards in hand can produce materially different card-preservation, hand-selection, and Joker choices.

Baron-Mime High Card remains under High Card because it is a specific High Card realization; `Held Face Cards` is an independent compatible leaf that may reinforce it without becoming a second parent.

## 8.3 Suit strategies

```text
Hearts [L]
Diamonds [L]
Clubs [L]
Spades [L]
```

No artificial `Suit Strategy` parent is added merely for taxonomy. The four suit plans do not need a shared parent unless a later audit discovers genuine shared foundation evidence that changes decisions.

## 8.4 Enhancement strategies

```text
Glass [L]
Steel [L]
Lucky [L]
Stone [L]

Gold Cards [I]
├── Held Gold Economy [L]
└── Golden Ticket Gold Scoring [L]
```

Gold Cards is split because holding Gold cards for end-of-round value and deliberately scoring Gold cards for Golden Ticket create different target-selection behavior.

The other enhancement strategies currently have one coherent trigger pattern and remain root/leaves unless their later audit proves a real incompatible specialization.

## 8.5 Seal strategies

```text
Blue Seal [L]
Purple Seal [L]

Red Seal [I]
├── Played Red Seal [L]
└── Held Red Seal [L]

Gold Seal [L]
```

Red Seal is split because a played-card retrigger target and a held-card retrigger target require materially different preservation and targeting decisions.

Blue, Purple, and Gold Seal currently have sufficiently coherent trigger patterns to remain root/leaves.

## 8.6 Existing synergy / named-engine strategies

```text
Smeared / Splash + Flower Pot [L]
Canio Destruction [L]
Vampire [L]
Ceremonial Dagger Sacrifice [L/new]
```

Ceremonial Dagger becomes an explicit strategy because intentionally feeding Jokers to it changes acquisition, Joker ordering, retention, sacrifice, and replacement behavior. This also gives the Negative-Joker exception a real strategy context instead of a one-off hardcoded exemption.

## 8.7 Additional engine strategies accepted for tree audit

These engines materially change several downstream decisions and therefore deserve explicit leaves rather than being treated only as generic Joker strength:

```text
Campfire Sell-Scaling [L/new]
Hologram Deck-Growth [L/new]
Erosion Deck-Thinning [L/new]
Madness Solo/Sacrifice [L/new]
Obelisk Hand-Rotation [L/new]
Constellation Planet-Scaling [L/new]
Red Card Pack-Skip Scaling [L/new]
Throwback Blind-Skip Scaling [L/new]
Joker Stencil Empty-Slot [L/new]
Flash Card Reroll-Scaling [L/new]
```

Their exact relationships and viability conditions are **not** assigned here. Each must pass the same later Gold/Silver/Bronze/Banned audit as every other leaf.

## 8.8 Removed as a standalone strategy

### Generic `Edition`

The old flat `Edition` strategy is removed from the structural tree.

Foil/Holographic/Polychrome are normally component value modifiers, not by themselves a coherent run strategy. Negative receives the global retention rule above. A future edition-specific leaf may be added only if it changes enough downstream decisions to satisfy the strategy criterion.

---

# 9. Strategy-node admission rule

Do not create a child or new root merely because two Jokers have synergy.

A node belongs in the forest only when following it materially changes multiple decisions such as:

- Joker acquisition;
- Joker retention/replacement;
- Joker ordering;
- poker-hand preference;
- discard/play behavior;
- deck growth/thinning;
- rank/suit targeting;
- enhancement/seal targeting;
- Tarot/Spectral/Planet use;
- pack purchase/open/skip behavior;
- reroll behavior;
- blind skip behavior;
- economy/resource allocation.

If two proposed nodes would make essentially the same decisions, keep them as one strategy.

If one node is simply compatible with another but is not a specialization of it, keep them as independent roots/leaves rather than creating a false parent edge.

---

# 10. Component relationship rule for the later catalogue

Every node — root, internal node, and leaf — may own exact named:

- Gold relationships;
- Silver relationships;
- Bronze relationships;
- Banned/conflict relationships;
- conditional relationships;
- structural evidence;
- consumable / Planet / voucher support.

A component is mapped to the **most truthful node(s)** rather than being copied into every descendant.

Examples conceptually:

```text
Burnt Joker
-> broad High Card relationship at the High Card root

Stuntman
-> specific Stuntman High Card leaf relationship

Baron / Mime
-> specific Baron-Mime High Card leaf relationships when conditions are met
```

The exact tier values are intentionally deferred until the tree is frozen.

Banned means a genuine strategic conflict, not merely that a Joker supports a competing strategy. Competition should usually emerge because the competing leaf gains positive evidence, not because every other leaf applies duplicate negative evidence.

---

# 11. Runtime migration boundary

The current Python strategy runtime still implements the previous flat catalogue. That implementation remains legacy behavior until this design is frozen and the migration slice begins.

The migration must not be attempted piecemeal while the tree is still changing.

Required implementation sequence after tree freeze:

1. encode node IDs, parent IDs, leaf/internal role, and fallback-leaf behavior;
2. separate `direct_evidence`, internal `foundation/branch_score`, and leaf `effective_score`;
3. implement upward descendant evidence propagation without recursive double counting;
4. implement controlled ancestor-direct inheritance only for eligible/activated leaves;
5. rank leaves only;
6. remove poker-hand play-count strategy evidence;
7. implement Negative Joker retention protection and destructive-strategy exceptions;
8. rebuild Gold/Silver/Bronze/Banned mappings one strategy node at a time;
9. regenerate component -> strategy relationship indices;
10. update acquisition, replacement, consumable, pack, blind-skip, reroll, and D1 integrations to consume leaf rankings;
11. add deterministic tree/evidence/ranking tests before live validation.

---

# 12. Tree-freeze checklist

Before Gold/Silver/Bronze/Banned work starts, confirm:

- every current flat strategy has been retained, split, replaced, or explicitly removed;
- every split represents a real behavioral difference;
- no parent edge encodes a fake natural poker-hand transition;
- no useful unspecialized root becomes unrankable merely because it has children;
- core/fallback leaves exist where needed;
- cross-cutting mechanics do not create false multiple-parent relationships;
- obvious named engines have been accepted or rejected;
- only leaves appear in the strategy ranking;
- descendant evidence propagates upward only;
- ancestor direct foundation is inherited only by eligible leaves;
- no evidence can feed back through an ancestor and count twice;
- poker-hand play count is excluded from universal strategy evidence;
- Negative Joker retention protection is explicit;
- destructive Jokers are evaluated according to whether their destructive behavior is intentional for the active leaf.
