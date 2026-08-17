# Balatro Strategy Tree Rules

Design rules for the v1.0F strategy-tree migration. Topology: [`BALATRO_STRATEGY_TREE.md`](BALATRO_STRATEGY_TREE.md). Relationship table: [`BALATRO_STRATEGY_RELATIONSHIPS.md`](BALATRO_STRATEGY_RELATIONSHIPS.md).

## 1. Tree edges

A parent -> child edge means the child is a more specific realization of the parent.

It does not mean:

- the child is globally stronger;
- the child must be reached later;
- the agent automatically progresses downward;
- adjacent poker hands naturally transition into each other.

High Card -> Pair -> Three of a Kind -> Four of a Kind progression is forbidden.

Cross-cutting synergy does not create fake multiple parents.

## 2. Node roles

- **Root** — broadest strategy in a tree.
- **Internal node** — strategy with children; not actionable.
- **Leaf** — actionable strategy.
- A root with no children is also a leaf.
- A split root may have a fallback leaf, but the fallback must have a concrete strategy name. Do not use empty `Core ...` placeholder names in the development topology.

Only leaves appear in actionable ranking.

## 3. Evidence model

Keep these separate:

- `direct_evidence(node)`
- `foundation_score(node)`
- `effective_score(leaf)`

### Joker evidence

| Relationship | Score |
|---|---:|
| Gold | +5.00 |
| Silver | +3.00 |
| Bronze | +1.00 |
| Neutral | 0.00 |
| Banned | -8.00 |

Gold/Silver/Bronze are **Joker relationship tiers only**.

### Non-Joker evidence

| Evidence | Score |
|---|---:|
| Matching Planet / permanent hand level gained | +0.50 per level |
| Strategy-directed Tarot use | +0.30 per use |
| Strategy-directed Spectral use | +0.50 per use |
| Matching enhancement in current deck | +0.35 per card |
| Matching seal in current deck | +0.40 per card |

Tarot, Planet, Spectral, enhancement, and seal evidence does not use Gold/Silver/Bronze.

`Banned` may still apply to any component when it is a genuine mechanical conflict.

Held/unopened consumables are not current positive strategy evidence. Positive Tarot/Spectral evidence comes from an actual strategy-directed use or its surviving current-state result.

Do not double count the same persistent transformation as both historical-use evidence and structural deck evidence unless the two values represent different mechanics.

## 4. Evidence propagation

### Descendant -> ancestor

Positive descendant evidence propagates upward with decay.

```text
Baron-Mime evidence
    -> Baron-Mime direct evidence
    -> discounted High Card foundation
```

### Ancestor -> descendant

Parent evidence does not blindly activate specific children.

A specialized child needs qualifying child-specific evidence before inheriting ancestor direct foundation.

### No recursive double counting

A leaf must never propagate its own evidence upward and then re-inherit that propagated evidence through the parent. Descendants inherit ancestor native/direct foundation only.

## 5. Ranking by Ante

### Antes 1-2

- strategy values normally start at zero;
- inherent/meta/survival/economy value dominates;
- several strategies may gain evidence;
- a complete early package may establish immediately.

### Antes 3-5

- strategy pressure increases;
- replacement and reroll choices increasingly use leaf ranking;
- the agent converges while allowing stronger pivots.

### Ante 6+

- strongest viable leaf dominates;
- up to two compatible materially supported leaves may remain relevant;
- survival overrides strategic purity.

## 6. Poker-hand play counts

Generic `hand_play_counts` are not positive strategy evidence.

Play history remains legal only for mechanics that explicitly use it, including Supernova and Obelisk.

Permanent poker-hand levels are valid evidence at `+0.50` per gained level.

## 7. Negative Joker retention

Negative Jokers are protected from ordinary sell/replacement pressure because the Negative edition normally offsets slot cost with +1 Joker slot.

A Negative Joker may be removed when:

1. its active mechanic materially harms a dominant/relevant strategy;
2. it creates a hard contradiction that cannot be neutralized;
3. ongoing harm exceeds the free-slot benefit;
4. a deliberate sacrifice/destruction strategy proves the trade worthwhile.

## 8. Relationship ownership

Gold/Silver/Bronze describe strategy evidence, not generic Joker strength.

- **Gold** — defining Joker evidence.
- **Silver** — strong Joker reinforcement.
- **Bronze** — weaker/secondary Joker reinforcement.
- **Banned** — genuine mechanical conflict.

A competing strategy is not automatically Banned.

A component may appear in multiple strategy nodes only when the mechanical requirements are distinct. If the same component means the same thing in both places, one node owns it.

Examples:

- Glass Canio and Glass Joker scaling may both reference Glass only when Canio payoff and Glass-Joker payoff are independently present.
- Midas + Vampire and Gold-card economy may both reference Midas only when enhancement consumption and Gold retention are independently represented.
- Trading Card Canio and Trading Card thinning may both reference Trading Card only when both destruction payoffs are independently present.

## 9. Strategy-node admission

Create a node only when it materially changes multiple downstream decisions such as:

- Joker acquisition/retention/order;
- hand/discard behavior;
- rank/suit/deck shaping;
- enhancement/seal targeting;
- Tarot/Spectral/Planet use;
- packs/rerolls/blind skips;
- economy/resource allocation;
- sacrifice/destruction behavior.

Do not create a node for every two-Joker interaction. If two proposed strategies make essentially the same decisions, keep one node and express the synergy through relationships.
