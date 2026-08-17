# Balatro Strategy Tree Rules

Development rules for [`BALATRO_STRATEGY_TREE.md`](BALATRO_STRATEGY_TREE.md). Relationship data lives in [`BALATRO_STRATEGY_RELATIONSHIPS.md`](BALATRO_STRATEGY_RELATIONSHIPS.md).

## 1. Tree semantics

- `[I]` is a real generic strategy that has more specific descendants.
- `[L]` is a specialization with no descendants.
- A standalone `[L]` is a strategy with no specializations.
- Do not create `Core ...`, `... Scoring`, or other fallback leaves that merely duplicate their indexed parent.
- No natural poker-hand progression edges.
- Cross-cutting synergy does not create fake parent edges.

An indexed strategy remains a valid actionable strategy. When a specialization is materially established, the specialization may replace the generic indexed strategy for that branch in the actionable ranking.

## 2. Relationship table semantics

The `[I]` row in `BALATRO_STRATEGY_RELATIONSHIPS.md` is an aggregate development index. Its Joker columns contain the union of the generic strategy and descendant specialization relationships.

The aggregate row and a descendant row are **not additive**. The same Joker/component must never be counted twice merely because it appears in both the indexed row and a specialization row.

Specialization rows contain only the relationships that distinguish that specialization.

## 3. Evidence types

Joker relationship tiers:

- Gold: `+5.00`
- Silver: `+3.00`
- Bronze: `+1.00`
- Banned: `-8.00`

Non-Joker evidence is independent from Gold/Silver/Bronze:

- matching Planet / permanent hand level gained: `+0.50` per level;
- strategy-directed Tarot use: `+0.30` per use;
- strategy-directed Spectral use: `+0.50` per use;
- matching enhancement in current deck: `+0.35` per card.

There is **no universal Seal evidence weight**. Seal presence is too cross-cutting to prove most strategies. A seal matters only when an exact strategy mechanic explicitly depends on it; that logic is handled by that strategy rather than by a generic `+score per seal` rule.

## 4. Evidence ownership and duplication

A component may support multiple strategies when the mechanics are genuinely different.

If two nodes use the same component for the same reason, one semantic owner is preferred. If an indexed strategy lists a component because a descendant uses it, that index entry is reference/coverage data and must not create a second copy of the same evidence.

Repeated components such as DNA, Glass, Vampire, Pareidolia, Midas Mask, Marble Joker, and Trading Card require distinct payoff requirements when used by multiple specializations.

## 5. Generic play counts

Generic `hand_play_counts` are not positive strategy evidence.

Play counts remain legal only for mechanics that explicitly depend on them, such as Obelisk or Supernova.

Persistent hand levels remain valid evidence because they represent permanent investment.

## 6. Tree propagation

Specific evidence may support its broader indexed strategy, but scoring must preserve provenance so the same component is not counted once on a specialization and again through its indexed parent.

Broad indexed evidence does not blindly activate every specialization. A specialization requires its own distinguishing evidence.

There is no fallback-child suppression rule because there are no duplicate fallback children.

## 7. Ante behavior

### Antes 1-2

- inherent/meta/survival/economy value leads;
- several strategies may acquire evidence;
- a strong specific package may establish immediately.

### Antes 3-5

- strategy pressure increases;
- replacement and acquisition should increasingly reinforce established strategies;
- pivots remain allowed when current-state evidence changes.

### Ante 6+

- strongest viable strategy/specialization leads;
- up to two compatible materially supported peers may remain relevant;
- survival overrides strategic purity.

## 8. Negative Joker retention

Negative Jokers are protected from ordinary replacement pressure because they normally offset their slot cost.

Removal requires a real mechanical conflict, unavoidable ongoing harm, or an intentional sacrifice/destruction payoff that exceeds retention value.

## 9. Banned relationships

Banned means genuine mechanical conflict, not merely support for a competing strategy.

Competing positive strategies should normally compete through their own evidence rather than by banning each other.

## 10. Strategy-node admission

Create a new node only when it materially changes downstream decisions such as acquisition/retention, ordering, hand/discard behavior, deck shaping, consumable use, economy, blind skipping, or sacrifice/destruction behavior.

Do not create a node for every synergy. If the generic indexed strategy already represents the policy, do not add a duplicate generic child.
