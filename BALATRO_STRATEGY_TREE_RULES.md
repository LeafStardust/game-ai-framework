# Balatro Strategy Tree Rules

Development rules for [`BALATRO_STRATEGY_TREE.md`](BALATRO_STRATEGY_TREE.md). Relationship data lives in [`BALATRO_STRATEGY_RELATIONSHIPS.md`](BALATRO_STRATEGY_RELATIONSHIPS.md).

## 1. Tree semantics

- `[I]` is a real generic strategy that has more specific descendants.
- `[L]` is a specialization with no descendants.
- A standalone `[L]` is a strategy with no specializations.
- Do not create `Core ...`, `... Scoring`, or other fallback leaves that merely duplicate their indexed parent.
- No natural poker-hand progression edges.
- Cross-cutting synergy does not create fake parent edges.
- Similar or composite poker hands remain separate when their evidence does not inherit cleanly across every evidence column.

An indexed strategy remains a valid actionable strategy. When a specialization is materially established, the specialization may replace the generic indexed strategy for that branch in the actionable ranking.

## 2. Relationship table semantics

An `[I]` row contains only evidence that belongs to the generic indexed strategy and is shared by every specialization below it.

A specialization row contains only the additional evidence that distinguishes that specialization from its parent and siblings.

This factoring rule applies to every evidence column:

- Gold;
- Silver;
- Bronze;
- Banned;
- Tarot;
- Planet;
- Spectral;
- Enhancement.

A component must never be copied into an indexed row merely because one descendant uses it. If a component is specific to one descendant, it belongs only on that descendant.

Example:

```text
High Card [I]
  generic evidence shared by both High Card specializations

Stuntman / Small-Hand High Card [L]
  Stuntman-specific evidence only

Baron-Mime Steel-King High Card [L]
  Baron/Mime-specific evidence only
```

`Stuntman`, `Baron`, and `Mime` therefore do not also appear on the High Card row. `The Chariot` and `Steel` do appear on the High Card row because they benefit both current High Card specializations and are not unique evidence for Baron-Mime.

## 3. Evidence types

Joker relationship tiers:

- Gold: `+8.00`
- Silver: `+3.00`
- Bronze: `+1.00`
- Banned: `-8.00`

Gold is deliberately narrow. A Joker belongs in Gold only when **owning that Joker can make the strategy viable and unusually effective by itself**, rather than merely making the strategy easier to execute or adding modest value. Examples include Scholar for Aces, Glass Joker for Glass breakage, Steel Joker for Steel density, Runner / The Order for Straight, Hologram for deck-growth, Yorick for discard scaling, and Obelisk for hand rotation.

Silver is the normal support tier. Enablers, consistency tools, modest economy pieces, hand-shape helpers, and weak single-Joker routes belong here even when they are strongly associated with a strategy. Examples include Banner, Delayed Gratification, Acrobat, Abstract Joker, Shortcut, Four Fingers, Superposition, Reserved Parking, Business Card, Faceless Joker, Sixth Sense, Shoot the Moon, Hiker, Satellite, Mail-In Rebate, Loyalty Card, Fortune Teller, Cartomancer, Hallucination, and 8 Ball.

Bronze remains secondary or conditional support. A Gold relationship must outweigh two Silvers and remain the largest single evidence step, but Gold must not be used merely to manufacture an early commitment signal.

These tiers are strategy evidence, not a universal Joker-value catalogue. A strategy-agnostic Joker keeps its ordinary scoring, economy, scaling, and survival value without being copied into every row as Bronze. Conversely, a route-bound Joker mapped only to another strategy can be `OFF_PATH` even though that other row calls it Silver or Gold.

Candidate applicability is reported separately:

- `UNIVERSAL`: useful without the active route; no strategy bonus or off-path penalty;
- `ALIGNED`: supports the active route and receives its tier reinforcement;
- `PIVOT`: a sufficiently strong alternative route whose projected evidence clears the pivot margin while pivots remain allowed;
- `OFF_PATH`: requires another route and receives a dynamic opportunity cost;
- `CONFLICT`: explicitly Banned by the active route.

Foil, Holographic, Polychrome, and Negative values are universal rather than strategy tiers. Negative additionally avoids ordinary slot opportunity cost and should be acquired when affordable unless its active mechanic is an explicit conflict. Other editions strongly improve a candidate but still must justify the occupied slot and transaction cost; an edition does not make a useless off-path mechanic automatically replace a useful aligned Joker.

Non-Joker evidence is independent from Gold/Silver/Bronze:

- matching Planet / permanent hand level gained: `+0.50` per level;
- strategy-directed Tarot use: `+0.30` per use;
- strategy-directed Spectral use: `+0.50` per use;
- matching enhancement in current deck: `+0.35` per card.

There is **no universal Seal evidence weight**. Seal presence is too cross-cutting to prove most strategies. A seal matters only when an exact strategy mechanic explicitly depends on it; that logic is handled by that strategy rather than by a generic `+score per seal` rule.

## 4. Evidence ownership and duplication

A component may support multiple strategies when the mechanics are genuinely different.

If two nodes use the same component for the same reason, one semantic owner is preferred. Parent/child factoring must preserve one ownership location for each piece of evidence.

Repeated components such as DNA, Glass, Vampire, Pareidolia, Midas Mask, Marble Joker, and Trading Card require distinct payoff requirements when used by multiple specializations.

## 5. Generic play counts

Generic `hand_play_counts` are not positive strategy evidence.

Play counts remain legal only for mechanics that explicitly depend on them, such as Obelisk or Supernova.

Persistent hand levels remain valid evidence because they represent permanent investment.

## 6. Tree propagation

A specialization inherits generic parent evidence once the specialization itself is materially established.

Specific child evidence may support confidence in the broader parent strategy, but it must retain provenance and must not be re-counted as parent direct evidence.

Broad indexed evidence does not blindly activate every specialization. A specialization requires its own distinguishing evidence.

There is no fallback-child suppression rule because there are no duplicate fallback children.

## 7. Strategy pursuit and Ante behavior

A positive dominant strategy is always worth trying to strengthen, regardless of Ante. There is no minimum Ante and no arbitrary score floor before strategy-search pressure may activate. If the current dominant strategy has positive evidence, shop rerolls, Joker acquisition, consumable acquisition, deck shaping, and hand preference may all seek additional matching evidence immediately.

This is **not** permission to spend recklessly. Survival, blind-clear probability, affordability, cash reserve, reroll EV, and immediate board strength remain higher-priority constraints. Strategy pursuit means the agent should not passively wait for the exact next component to appear when active search is economically justified.

### Antes 1-2

- inherent/meta/survival/economy value still leads when no route has positive evidence;
- several strategies may acquire evidence and remain pivotable;
- once a dominant route has positive evidence, the agent should already look for aligned Jokers/consumables and other ways to increase its score;
- a strong specific package may establish immediately.

### Antes 3-5

- strategy pressure increases naturally through accumulated evidence;
- replacement and acquisition should reinforce the strongest viable strategy while pivots remain allowed when current-state evidence changes;
- the agent should actively search rather than waiting for aligned pieces to fall into the shop on their own when reroll EV supports it.

### Ante 6+

- the strongest viable strategy/specialization is the only prescriptive route;
- secondary strategies remain visible for diagnostics but contribute no purchase bonus, hand preference, or pivot authorization;
- a route-bound secondary-strategy Joker is eligible for replacement by a positively valued universal or dominant-strategy Joker;
- the dominant route remains under active search pressure;
- survival overrides strategic purity.

## 8. Tactical survival overrides strategy preferences

Strategy is always subordinate to winning the current blind.

- If a current legal hand can score at least `remaining blind score / hands remaining`, a pace-qualified play is authoritative over strategy shaping.
- If no current play reaches that pace, discards are the normal setup/recovery tool when available.
- If only one hand remains, no current play can clear/reach pace, and at least one legal discard remains, the agent **must discard** rather than spend the final hand on a known losing play.
- No-discard incentives such as Banner, Delayed Gratification, Green Joker, or Ramen cannot override that final-hand survival rule.

## 9. Joker ordering

Joker order is an executable build decision, not presentation state. In stable
phases the agent evaluates legal permutations against the complete active build.
The selected order must account for:

- additive Mult resolving before later multiplicative Mult when that scores higher;
- Blueprint copying the Joker immediately to its right;
- Brainstorm copying the leftmost Joker;
- Ceremonial Dagger destroying the Joker immediately to its right on blind select.

Ceremonial Dagger permutations are evaluated after projecting the sacrifice and
its gained Mult. Ordinary reorders require a strict projected whole-build score
improvement. Negative-retention safety is stronger than that ordinary threshold:
when Dagger is not the active strategy, the policy may accept a lower immediate
score to move a Negative Joker out of the sacrifice slot. An active Dagger route
may intentionally consume a Negative only when its projected build ordering still
justifies that sacrifice.

## 10. Negative Joker retention

Negative Jokers are protected from ordinary sell/replacement pressure because they normally offset their slot cost. Selling one cannot fund an ordinary replacement slot because the extra slot disappears with it.

Standalone sale requires measured whole-build harm to clear the configured
material-harm floor. Neutrality, off-path status, low sell value, full ordinary
slots, or a stronger shop candidate are not removal exceptions. Boss-required
emergency actions such as Verdant Leaf remain survival-scoped. Intentional
destruction requires an active matching route, such as Ceremonial Dagger, and is
logged as an explicit retention exception.

## 11. Banned relationships

Banned means genuine mechanical conflict, not merely support for a competing strategy.

Competing positive strategies should normally compete through their own evidence rather than by banning each other.

## 12. Strategy-node admission

Create a new node only when it materially changes downstream decisions such as acquisition/retention, ordering, hand/discard behavior, deck shaping, consumable use, economy, blind skipping, or sacrifice/destruction behavior.

Do not create a node for every synergy. If the generic indexed strategy already represents the policy, do not add a duplicate generic child.
