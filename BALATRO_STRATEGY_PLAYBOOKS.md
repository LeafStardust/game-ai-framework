# Balatro Strategy Playbooks

> Architecture and decision contract for the universal hardcoded Balatro strategy system.
>
> **This file explains how strategy playbooks work. It does not contain the strategy catalogue.**

## Strategy catalogue files

The concrete strategy definitions are maintained separately:

- [`BALATRO_STRATEGIES_POKER_HANDS.md`](BALATRO_STRATEGIES_POKER_HANDS.md) — High Card, Pair, Two Pair, Three of a Kind, Straight, Flush, Full House, Four of a Kind, Straight Flush, Five of a Kind, Flush House, Flush Five.
- [`BALATRO_STRATEGIES_MECHANICS.md`](BALATRO_STRATEGIES_MECHANICS.md) — Face Cards, Faceless/No-Face, Glass, Steel, Lucky, Stone, Gold Cards, Blue/Purple/Red/Gold Seal, Edition.
- [`BALATRO_STRATEGIES_NICHE.md`](BALATRO_STRATEGIES_NICHE.md) — Aces, Smeared/Splash + Flower Pot, Canio Destruction, Vampire, with additional niche packages added explicitly later.

The file grouping is documentation-only. **Every strategy is a peer in one flat universal runtime strategy pool.** There are no primary, advanced, overlay, mechanic, or niche runtime strategy classes.

---

## 1. Core model

The agent must not treat every Joker, Tarot, Planet, Spectral card, voucher, booster pack, and deck modification as an isolated purchase.

Instead, explicitly mapped build components contribute evidence toward one or more universal strategy playbooks.

A run may pursue several compatible strategies while evidence is weak, then gradually converge as its actual inventory and deck shape develop.

By late game the intended state is:

- **1 dominant strategy** — the main direction for future purchases and deck shaping;
- **0–2 relevant strategies** — compatible and sufficiently supported alternatives that still influence decisions;
- all other strategies strongly suppressed unless a genuinely transformative pivot appears.

The dominant strategy describes what the run is building toward. It does **not** dictate every hand that must be played. Survival and guaranteed blind clears remain superior to strategic purity.

---

## 2. What a strategy definition contains

Each universal strategy should eventually be encoded as data containing at least:

- stable strategy ID;
- human-readable name;
- strategic identity / intended scoring engine;
- **explicit named Gold components**;
- **explicit named Silver components**;
- **explicit named Bronze components**;
- **explicit named banned/conflict components**;
- relevant poker hands, when applicable;
- preferred Planets, when applicable;
- preferred Tarot/Spectral transformations;
- preferred vouchers or booster families when materially relevant;
- deck-shape evidence;
- entry evidence;
- maturity/completion evidence;
- natural pivot relationships;
- abandonment conditions.

A component may belong to several strategies at different tiers.

Gold/Silver/Bronze are therefore **strategy-relative relationships**, not global item rankings.

### 2.1 Exact component mapping is mandatory

The catalogue is intended to become executable data later. Therefore tier/conflict lists must use exact component identities.

Correct:

```text
Flush
  Gold: The Tribe; Smeared Joker; Four Fingers
  Silver: Droll Joker; Crafty Joker; Castle; Ancient Joker
  Banned/conflict: The Order; Runner; Crazy Joker; Devious Joker
```

Incorrect:

```text
Flush
  Silver: good suit Jokers
  Bronze: generic Mult/Chips
  Conflicts: rank stuff
```

**Unlisted component = Neutral for that strategy.** Neutral is not Bronze and is not banned.

Generic immediate scoring, economy, survival, edition, sell value, and other standalone item value may still be evaluated by the ordinary policy layer. A Joker does not need to be stuffed into Bronze merely to remain buyable.

Bronze therefore means **explicit weak/conditional strategic synergy**, not "generically useful."

---

## 3. Canonical data ownership

The canonical source of truth is **strategy-centric**.

```python
StrategyDefinition(
    id="steel",
    gold_components={...},
    silver_components={...},
    bronze_components={...},
    banned_components={...},
    conflicts={...},
    ...
)
```

Do **not** add strategy-tier metadata separately to all 150 Joker classes.

The runtime should generate an inverse lookup from the strategy definitions:

```python
component -> [(strategy, tier), ...]
```

This allows shop evaluation to answer:

> Which strategies does this Joker, consumable, voucher, or other component advance, and by how much?

without duplicating strategy data across the item implementations.

The same rule applies to consumables and other components: strategy files own the relationship; item classes do not become the strategy database.

---

## 4. Gold / Silver / Bronze / banned semantics

### Gold — defining / premium synergy

A Gold component is one of the strongest reasons to pursue or continue a strategy.

Typical Gold evidence includes a component that:

- directly defines the strategy;
- creates a major multiplicative or scaling engine;
- dramatically increases consistency;
- provides a core transformation the strategy needs; or
- turns the route into a realistic run-winning build.

Gold is **not an unconditional auto-buy**. Survival, affordability, slot pressure, boss constraints, economy, and stronger existing strategies can still override it.

### Silver — strong reinforcement

A Silver component works extremely well in the strategy but does not define it alone.

Several Silver components can collectively provide enough evidence to elevate a strategy without a Gold component.

### Bronze — explicit weak/conditional synergy

A Bronze component has a real named relationship to the strategy, but is weaker, more conditional, more replaceable, or less central than Silver.

Bronze evidence alone must not hard-lock a strategy.

### Banned / conflict

A named banned/conflict component is one the strategy should normally suppress once dominant because it:

- fails to trigger under the intended play pattern;
- directly destroys required deck structure;
- consumes enhancements/cards/resources the strategy needs to preserve; or
- strongly pulls the run into an incompatible route.

A banned/conflict mapping is still overridable by immediate survival or an intentional pivot. It is not a universal game ban.

---

## 5. Strategy evidence and ranking

The agent maintains a score for every universal strategy from **public run state only**.

Evidence may include:

- owned Jokers and their explicit Gold/Silver/Bronze relationships;
- held Tarot/Spectral/other consumables with explicit strategy mappings;
- permanent deck modifications;
- rank/suit/enhancement/seal/edition structure;
- poker-hand level investment;
- actual repeated hand usage;
- current Joker and consumable slot investment;
- synergistic component combinations;
- explicit conflicts already present;
- deck/stake effectiveness modifiers;
- sunk economic/build investment.

Conceptually:

```text
Ante 2
Face Cards       4.2
Pair             3.5
Steel            1.7
Lucky            0.8
Straight         0.2

Ante 4
Face Cards       8.9
Pair             6.1
Steel            4.4
Lucky            1.0
Straight         0.0

Ante 6
DOMINANT: Face Cards   13.6
RELEVANT: Pair          8.4
RELEVANT: Steel         7.2
All others: suppressed
```

Exact numerical weights belong in implementation and deterministic tests, not this document.

---

## 6. Ante progression: explore -> converge -> specialize

### Antes 1–2 — mandatory exploration / foundation

The run normally begins with no meaningful strategy evidence.

The agent must therefore **not refuse useful purchases because no strategy exists yet**.

It should intentionally acquire useful scoring, economy, Joker, Tarot, and Spectral opportunities that:

- improve immediate survival through the ordinary evaluator;
- provide an explicitly mapped Bronze/Silver/Gold relationship to one or more strategies;
- create useful deck structure or seed a strategy;
- do not catastrophically damage economy.

The objective is to let RNG provide strategic evidence rather than demanding that RNG already match a nonexistent build.

A mostly empty Joker board caused by "nothing matches my strategy" is a policy failure during this phase.

### Antes 3–5 — convergence

By Ante 3, actual inventory and deck shape should begin separating promising strategies from noise.

The agent increasingly prefers:

- Gold/Silver components of leading strategies;
- transformations that make those strategies more reliable;
- Planets matching poker-hand strategies with real evidence;
- packs with meaningful expected strategic utility.

Pivots remain allowed. A new Gold component may overtake the current leader while sunk investment is still shallow.

### Ante 6+ — dominant + relevant shortlist

By Ante 6 the run should normally expose:

- exactly **one dominant strategy**, when meaningful evidence exists;
- up to **two relevant strategies** that remain compatible and sufficiently supported.

Future purchases are strongly biased toward this shortlist.

Shortlist membership is **not a prohibition system**. If a Joker slot is empty and no on-strategy option appears, the agent may still buy a strong Neutral/off-strategy bridge when the ordinary evaluator says it materially improves survival or scoring.

The important late-game behavior is:

> Stop spending scarce resources fishing for unrelated new strategies that have little relationship to the established run.

A transformative pivot remains possible, but its required advantage increases with Ante and sunk investment.

---

## 7. Dominant strategy versus D1 hand selection

A strategy describes what the run is building toward, not an absolute command for D1.

If the dominant strategy is Flush but another available hand guarantees the blind clear, the agent may take the guaranteed clear.

When survival is not at risk, D1 should increasingly prefer:

- playing the dominant strategy's intended hand or trigger pattern;
- discarding toward that structure;
- preserving cards important to the dominant/relevant strategies;
- triggering strategic scaling engines when the lost immediate value is acceptable.

Priority is approximately:

1. guarantee or preserve blind survival;
2. take an already guaranteed efficient clear when available;
3. pursue the dominant strategy's intended scoring pattern;
4. reinforce relevant strategies when compatible;
5. avoid unrelated speculative behavior.

---

## 8. Consumables, Planets, and packs

The strategy system must prevent pointless consumable and booster spending without eliminating early build discovery.

### 8.1 Tarot cards — exploratory and strategy-seeding

Tarot cards may be valuable before a dominant strategy exists because they can create permanent deck structure.

Early Tarot acquisition/use may legitimately create enhancements, convert suits, copy cards, destroy cards, or increase rank concentration when those effects have explicit playbook relationships or strong immediate utility.

Therefore Tarot value in Antes 1–2 may come from both immediate utility and **strategy-seeding potential**.

As the run converges, Tarot value should increasingly come from dominant/relevant strategy contribution rather than generic transformation value.

### 8.2 Spectral cards — exploratory and potentially transformative

Spectral cards may be even more strategically transformative than Tarot cards and must not be gated behind an already mature strategy.

An early Spectral may legitimately create the foundation for a strategy through major rank, suit, edition, Joker, hand-size, or deck-structure changes.

The agent may therefore open/buy/use Spectral opportunities early when their expected structural upside justifies the risk.

Later, incompatible or destructive Spectral effects should face stronger strategy and survival penalties.

### 8.3 Planets — reinforcement, not blind exploration

Planets are different.

A Planet primarily improves one poker hand. It should **normally require actual poker-hand evidence before the agent spends money acquiring or upgrading it**.

Meaningful Planet value should come from one or more of:

- the corresponding poker-hand strategy is dominant;
- the corresponding poker-hand strategy is relevant;
- the deck and actual hand usage provide strong convergence-phase evidence for that hand;
- existing Joker/build structure makes that hand a realistic near-term direction.

A Planet should not create a strategy merely because `+1 hand level` is generically positive.

This is especially important for speculative hands such as Straight Flush, Five of a Kind, Flush House, and Flush Five.

### 8.4 Booster packs

Pack value should derive from expected contents relative to the current phase:

- **Arcana/Spectral:** can have genuine exploration and strategy-seeding value early;
- **Celestial:** should be much more tightly gated by actual poker-hand evidence;
- **Joker/other packs:** should account for immediate survival value and the chance of revealing explicitly mapped components for leading strategies.

Late-game packs should lose value when most plausible outcomes do not advance the dominant/relevant strategies.

---

## 9. Multiple strategies and compatibility

The agent may intentionally chase several compatible strategies while the run develops.

Example:

```text
Face Cards + Pair + Steel
```

All three remain independent peer strategies. The runtime does not need a nested `Face Pair Steel` playbook.

Compatibility emerges from:

- shared explicitly mapped components;
- deck shape;
- lack of conflicts;
- actual run evidence.

By Ante 6, one should normally become dominant while at most two remain relevant.

---

## 10. Shop behavior implied by the system

A future shop evaluation should be able to explain a candidate in strategy terms.

```text
Candidate: Photograph

Dominant: Face Cards
  tier: Gold

Relevant: Pair
  tier: Neutral

Relevant: Steel
  tier: Neutral

Result: strongly preferred if affordable and survival-safe.
```

A speculative Planet might produce:

```text
Candidate: Neptune

Dominant: Face Cards
  contribution: none

Relevant: Pair
  contribution: none

Relevant: Steel
  contribution: none

Straight Flush evidence: negligible

Result: reject.
```

The same explicit strategy relationships should inform Joker acquisition, consumables, vouchers, packs, rerolls, sell/replace decisions, and resource valuation.

---

## 11. Deck/stake cartridges

Universal strategies remain unchanged across decks and stakes.

A deck/stake cartridge may provide environment-specific modifiers such as:

```python
StrategyModifier(
    strategy_id="flush",
    enabled=True,
    effectiveness=1.10,
    score_bonus=0.0,
)
```

A cartridge may:

- amplify a strategy;
- suppress a strategy;
- disable a genuinely infeasible/unsupported strategy;
- adjust commitment or pivot pressure for the environment.

A cartridge must **not** redefine the universal Gold/Silver/Bronze/banned component relationships.

---

## 12. Implementation order

Do **not** continue strategy-aware production wiring until the catalogue is sufficiently complete.

1. Finalize the universal strategy list across the catalogue files.
2. Audit and fill exact named Gold/Silver/Bronze/banned mappings for every strategy.
3. Encode universal `StrategyDefinition` data.
4. Generate inverse component -> strategy/tier indices automatically.
5. Add deck/stake effectiveness modifiers.
6. Implement per-run evidence scoring and Ante-based exploration/convergence/specialization pressure.
7. Integrate strategy state into D1–D14.
8. Add deterministic tests for ranking, pivots, consumables, Planet suppression, packs, and hand preference.
9. Run specialized live validation.
10. Resume the v1.0 autonomous acceptance gate only after the strategy system is proven.

---

## 13. Non-negotiable behavioral rules

- The agent starts with **no assumed strategy**.
- Strategy catalogues use exact named components; vague categories are not implementation data.
- Unlisted component means Neutral, not Bronze.
- Antes 1–2 must permit and normally require useful purchases so RNG can create strategy evidence.
- Tarot/Spectral cards may seed strategies early; they are not subject to the same evidence gate as Planets.
- Planets should normally reinforce an evidenced poker-hand direction rather than create one from nothing.
- Antes 3–5 progressively favor coherent existing directions.
- By Ante 6, when evidence exists, the run should normally have **one dominant strategy and at most two relevant strategies**.
- The dominant strategy guides future build decisions but does not override guaranteed blind survival.
- Relevant strategies prevent over-locking and allow compatible offers to fill remaining slots.
- Neutral/off-strategy generic survival purchases remain legal when needed; speculative late strategy fishing does not.
- Gold/Silver/Bronze are strategy-relative relationships, never global item tiers.
- Strategy files own component-tier metadata; individual Joker classes do not.
- Deck/stake cartridges modify strategy effectiveness; they do not own or redefine universal strategies.
- Strategy decisions must be explainable in authoritative logs.
