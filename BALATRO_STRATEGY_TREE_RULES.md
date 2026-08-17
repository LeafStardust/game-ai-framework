# Balatro Strategy Tree Rules

> Design rules for the v1.0F strategy-tree migration. The actual topology lives in [`BALATRO_STRATEGY_TREE.md`](BALATRO_STRATEGY_TREE.md).

## 1. What a tree edge means

A parent -> child edge means only that the child is a **more specific realization** of the parent strategy.

It does not mean:

- the child is globally stronger;
- the child must be reached later;
- the agent automatically progresses downward;
- adjacent poker hands naturally transition into each other.

Different poker hands remain separate roots unless one strategy is genuinely a specialization of another. High Card -> Pair -> Three of a Kind -> Four of a Kind is explicitly forbidden as a topology rule.

Cross-cutting synergies do not create fake multiple parents. A component may support several strategy nodes, but each strategy node has one truthful parent path.

## 2. Node roles

- **Root** — broadest strategy in a tree.
- **Internal node** — a strategy with children.
- **Leaf** — deepest defined strategy on a branch.
- A root with no children is also a leaf.
- A split root may have a `Core ...` fallback leaf so an unspecialized but valid version of that strategy remains rankable.

Only **leaves** appear in the actionable strategy ranking. Internal nodes exist to hold foundation evidence and contribute to descendant scores.

## 3. Evidence values

The implementation should separate:

- `direct_evidence(node)` — evidence belonging to this exact node;
- `foundation_score(node)` — non-ranked evidence describing how established an internal/root strategy is;
- `effective_score(leaf)` — actionable score used to rank leaves.

Every node, including internal nodes and leaves, may later own exact Gold/Silver/Bronze/Banned relationships, conditional relationships, structural evidence, consumable support, Planet support, voucher support, and environment modifiers.

## 4. Evidence propagation

### Descendant -> ancestor

Specific descendant evidence propagates **upward with decay** because a concrete leaf package also proves its broader foundation.

Example:

```text
Baron-Mime evidence
    -> strong Baron-Mime direct evidence
    -> discounted High Card foundation evidence
```

This allows a lucky early package to establish a deep strategy without first completing every broad parent component.

### Ancestor -> descendant

Ancestor evidence does **not** automatically activate every child.

A child must have qualifying child-specific evidence before it can inherit appropriate ancestor direct foundation.

Example:

```text
Burnt Joker -> High Card foundation
```

does not by itself activate both Stuntman High Card and Baron-Mime High Card.

### No recursive double counting

A leaf must never propagate its own evidence upward and then re-inherit that same propagated evidence through the parent. Descendants may inherit ancestor **native/direct foundation**, not an ancestor total that already contains the descendant's own propagated contribution.

## 5. Ranking behavior by Ante

### Antes 1-2 — exploration

- Normal strategy values start at zero unless the starting environment supplies explicit evidence.
- Joker inherent/meta/survival/economy value dominates purchases.
- Empty Joker slots should normally be populated with useful components.
- Several roots/leaves may gain evidence at once.
- A sufficiently complete deep leaf may become highly ranked immediately if RNG supplies it early.

### Antes 3-5 — convergence

- Strategy pressure increases.
- Filled Joker slots make sell/replace choices increasingly dependent on leaf ranking.
- The agent should begin concentrating on the strongest established branches while retaining genuinely competitive alternatives.
- A new branch can still overtake the current direction if current-state evidence becomes stronger.

### Ante 6+ — specialization

- The strongest viable leaf becomes dominant.
- Up to two compatible, materially supported leaves may remain relevant.
- Purchases, selling, rerolls, packs, deck shaping, consumables and hand behavior primarily reinforce the established leaf/compatible leaves.
- Guaranteed survival remains higher priority than strategic purity.

## 6. Poker-hand play counts

Generic `hand_play_counts` are **not strategy evidence**.

Early hand usage can reflect draw quality rather than intent, and later persistent build state is a better signal. Hand history remains legal for Jokers/mechanics that explicitly use it, such as Supernova or Obelisk.

Persistent poker-hand investment, especially actual hand levels from used Planets or other permanent upgrades, may still contribute small evidence.

## 7. Negative Joker retention

Negative Jokers are protected from ordinary sell/replacement pressure because the Negative edition normally offsets their slot cost with +1 Joker slot.

Do not sell a Negative Joker merely because it is Neutral or weakly aligned.

A Negative Joker may be removed when:

1. its active mechanic materially harms the dominant/relevant strategy;
2. it creates a hard contradiction that cannot be safely neutralized;
3. its expected ongoing harm exceeds the value of retaining the effectively free slot;
4. an active sacrifice/destruction strategy intentionally consumes it and the strategy evaluator proves the trade worthwhile.

Examples requiring contextual treatment include Ceremonial Dagger, Vampire and Madness. A destructive Joker is not inherently harmful when the run is deliberately built around that destruction mechanic.

## 8. Gold / Silver / Bronze / Banned

Exact tiers are intentionally deferred until the topology is frozen.

Later, every node may own:

- **Gold** — defining/premium evidence for that exact strategy;
- **Silver** — strong reinforcement;
- **Bronze** — explicit weaker/conditional reinforcement;
- **Banned** — genuine strategic conflict.

A Joker supporting a competing strategy is not automatically Banned. Competition should normally emerge because the competing leaf gains positive evidence. Banned is reserved for actual conflict.

A component may legitimately appear in several strategy nodes at different tiers when its effect truthfully supports several builds.

## 9. Strategy-node admission rule

Create a new node only when following it materially changes multiple downstream decisions such as:

- Joker acquisition or retention;
- Joker ordering;
- hand/discard behavior;
- rank/suit/deck shaping;
- enhancement or seal targeting;
- Tarot/Spectral/Planet use;
- pack or reroll behavior;
- blind skipping;
- economy/resource allocation;
- sacrifice/destruction behavior.

Do not create a node for every two-Joker interaction. If two proposed strategies make essentially the same decisions, keep one node and express the synergy through relationships instead.
