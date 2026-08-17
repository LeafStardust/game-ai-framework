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

The agent runs **through the playbook system**, but the playbook system does not replace ordinary Joker value.

Every shop candidate has two conceptually separate value sources:

```text
TOTAL CANDIDATE VALUE
=
base / meta / immediate value
+ survival / economy / context value
+ Ante-scaled strategy alignment
```

At the beginning of a run, every strategy score starts at zero because the run has no strategic evidence yet. Therefore strategy alignment contributes approximately zero to Joker purchase value. The agent buys useful early Jokers primarily from their ordinary/meta value.

Once a Joker is bought, every strategy explicitly linked to that Joker is immediately rescored from the new **current build state**. A Gold/Silver/Bronze relationship raises the corresponding strategy; a banned/conflict relationship lowers it. The higher a strategy becomes, the more future Gold/Silver/Bronze components of that strategy gain purchase value.

This creates the intended feedback loop:

```text
current build
    -> strategy scores
    -> strategy ranking
    -> strategy-aware candidate values
    -> buy / sell / use decision
    -> changed current build
    -> recompute strategy scores
    -> repeat
```

The system therefore discovers a build from the items RNG actually provides rather than selecting a build in advance.

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

The first implementation may begin with tunable evidence weights approximately like:

```text
Gold     +5
Silver   +3
Bronze   +1
Neutral   0
Banned   -8
```

These are initial implementation values, not permanent balance constants. The important invariant is the ordering and sign: Gold > Silver > Bronze > Neutral > Banned, with banned/conflict evidence strong enough to materially reduce strategy coherence.

### Gold — defining / premium synergy

A Gold component is one of the strongest reasons to pursue or continue a strategy.

Gold is **not an unconditional auto-buy**. A Gold shop candidate receives a large strategy bonus only when the corresponding strategy already has meaningful positive evidence and Ante pressure makes that evidence important. A Gold Joker for a zero-score strategy can still be bought early if its ordinary/meta value is good, but Gold status alone does not force the purchase.

### Silver — strong reinforcement

A Silver component works extremely well in the strategy but does not define it alone.

Several Silver components can collectively provide enough evidence to elevate a strategy without a Gold component.

### Bronze — explicit weak/conditional synergy

A Bronze component has a real named relationship to the strategy, but is weaker, more conditional, more replaceable, or less central than Silver.

Bronze evidence alone must not hard-lock a strategy.

### Banned / conflict

A named banned/conflict component contributes **negative evidence** to that strategy. This naturally reduces the strategy score and, when the strategy is dominant/relevant, creates sell/replace pressure on that component.

Banned does not mean "sell immediately under all circumstances." A conflicting Joker may temporarily remain if it is carrying current survival or there is no safe replacement.

A small set of direct functional contradictions may receive stronger immediate replacement priority. Example: **Pareidolia + Ride the Bus**, because Pareidolia makes every card a face card and directly breaks Ride the Bus's intended no-face scoring pattern.

---

## 5. Strategy score: current build state only

A strategy score represents **the run as it exists now**, not historical ownership.

If The Duo contributes +5 Pair evidence while owned, selling The Duo removes that +5 immediately. The fact that the run used to own it is irrelevant.

Permanent state created earlier remains relevant because it is still current state. Examples:

- Pair hand level remains elevated after Mercury was used;
- duplicated ranks remain in the deck after Death/Cryptid was used;
- Steel/Glass/Lucky/Stone cards remain enhanced;
- seals and editions remain where they currently exist.

Strategy scores should be recomputed whenever a meaningful current-state mutation occurs, including:

- Joker bought;
- Joker sold;
- consumable **used**;
- Planet **used**;
- card added, destroyed, copied, rank-changed, suit-changed, enhanced, sealed, or edition-changed;
- voucher/environment state changes when it affects strategy evidence;
- other persistent public build-state mutations.

### 5.1 Held/unopened consumables are not strategy evidence

Buying or holding an unopened Tarot/Spectral/Planet does **not** by itself increase the current strategy score. It represents potential future structure, not structure already achieved.

The candidate consumable can still receive purchase value because of what it could do for a strategy. Once used, its resulting permanent state is included in the next strategy recomputation.

This keeps strategy score grounded in the actual current build instead of promises about unused consumables.

### 5.2 Planets provide small persistent evidence after use

A used Planet increases the corresponding poker-hand strategy slightly because the run has permanently invested in that hand.

Planet evidence should be weaker than defining Joker evidence. Repeated Planet investment can nevertheless accumulate into meaningful support, especially when consistent with actual hand usage and deck shape.

Example conceptually:

```text
The Duo owned       -> strong Pair evidence
Mercury used once   -> small Pair evidence
Pair level 6        -> accumulated Pair investment evidence
```

### 5.3 Strategy scores may be negative

Banned/conflicting components and hostile deck structure may push a strategy below zero. Negative strategies should be considered incompatible rather than attractive.

For candidate purchase alignment, only meaningful positive strategy relevance should create positive synergy bonuses. The implementation must not allow a negative strategy score multiplied by a negative banned weight to accidentally become a positive purchase bonus.

---

## 6. Candidate strategy value

A candidate Joker's Gold/Silver/Bronze label does **not** directly add its evidence weight to the purchase score.

Instead, the candidate's strategic purchase value depends on how strongly the current run already supports the strategies that candidate belongs to.

Conceptually:

```python
strategy_alignment = sum(
    positive_relevance(strategy_score)
    * candidate_relationship_weight
    for each candidate strategy relationship
)

candidate_value = (
    base_meta_value
    + survival_economy_context
    + ante_strategy_pressure * normalized(strategy_alignment)
)
```

Consequences:

- Gold candidate + strategy score 0 -> little/no strategy bonus;
- Gold candidate + highly ranked strategy -> large strategy bonus;
- Silver/Bronze candidate + highly ranked strategy -> smaller reinforcement bonus;
- Banned candidate + highly ranked strategy -> negative strategy value;
- Neutral candidate -> no strategy adjustment, but ordinary/meta value still applies.

This is the mechanism that makes the agent gradually conform by itself.

---

## 7. Ante progression: explore -> converge -> specialize

Ante changes **how loudly strategy affects decisions**. It does not manufacture strategy evidence.

### Antes 1–2 — exploration / foundation

Strategy influence on purchases is deliberately weak.

At a zero-evidence start, shop Jokers are therefore chosen mostly by ordinary/meta value, immediate survival, economy, and affordability. Buying those Jokers creates the first strategy evidence.

The agent should be willing to try useful Jokers from several different strategies and fill available slots instead of waiting for an imaginary perfect build.

Tarot/Spectral opportunities may also create strategic structure early. Their unopened state does not raise strategy score, but their expected effect may justify acquisition/use.

### Antes 3–5 — convergence

Strategy influence becomes progressively stronger.

The agent increasingly prefers Gold/Silver/Bronze candidates belonging to its higher-ranked strategies, while still allowing meaningful pivots and strong Neutral purchases.

This is where the strategy rankings should begin separating coherent directions from incidental early purchases.

### Ante 6+ — dominant + relevant shortlist

By Ante 6 the run should normally expose:

- exactly **one dominant strategy**, when meaningful evidence exists;
- up to **two relevant strategies** that remain compatible and sufficiently supported.

Strategy influence is now strong. Future purchases, replacements, deck shaping, packs, consumables, and rerolls should primarily reinforce this shortlist.

Shortlist membership is **not a prohibition system**. If a Joker slot is empty and no on-strategy option appears, the agent may still buy a strong Neutral/off-strategy bridge when the ordinary evaluator says it materially improves survival or scoring.

The important late-game behavior is:

> Stop spending scarce resources fishing for unrelated new strategies that have little relationship to the established run.

A transformative pivot remains possible, but its required advantage increases with Ante and sunk current-state investment.

---

## 8. Selling and replacement

Owned components are evaluated against the same current strategy state.

A Joker that is banned/conflicting for the dominant strategy creates replacement pressure because it lowers that strategy's coherence. The agent should prefer replacing it with a strong aligned component when doing so is affordable and survival-safe.

Normal sequence:

```text
conflicting owned Joker
    -> negative dominant/relevant strategy contribution
    -> lower retention value
    -> aligned shop replacement appears
    -> sell conflict
    -> buy replacement
    -> recompute all strategy scores
```

Do not sell a conflicting Joker merely to create an empty slot if that would materially jeopardize the current blind/run and there is no better replacement.

Direct functional contradictions such as Pareidolia + Ride the Bus may justify much stronger replacement urgency.

---

## 9. Dominant strategy versus D1 hand selection

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

## 10. Consumables, Planets, and packs

The strategy system must prevent pointless consumable and booster spending without eliminating early build discovery.

### 10.1 Tarot cards — exploratory and strategy-seeding

Tarot cards may be valuable before a dominant strategy exists because they can create permanent deck structure.

Early Tarot acquisition/use may legitimately create enhancements, convert suits, copy cards, destroy cards, or increase rank concentration when those effects have explicit playbook relationships or strong immediate utility.

An unopened Tarot does not raise strategy score. Its acquisition value comes from expected immediate/structural benefit. After use, the resulting deck state is rescored.

### 10.2 Spectral cards — exploratory and potentially transformative

Spectral cards may be even more strategically transformative than Tarot cards and must not be gated behind an already mature strategy.

An unopened Spectral does not raise current strategy score. It may still be acquired/opened early when its expected transformation is valuable. After use, the actual resulting state becomes strategy evidence.

Later, incompatible or destructive Spectral effects should face stronger strategy and survival penalties.

### 10.3 Planets — reinforcement, not blind exploration

A Planet primarily improves one poker hand. It should **normally require actual poker-hand evidence before the agent spends money acquiring or upgrading it**.

Meaningful Planet purchase value should come from one or more of:

- the corresponding poker-hand strategy is dominant;
- the corresponding poker-hand strategy is relevant;
- the deck and actual hand usage provide strong convergence-phase evidence for that hand;
- existing Joker/build structure makes that hand a realistic near-term direction.

A Planet should not create strategy intent merely because `+1 hand level` is generically positive. Once used, however, the permanent hand-level investment contributes a small amount of ongoing strategy evidence.

This is especially important for speculative hands such as Straight Flush, Five of a Kind, Flush House, and Flush Five.

### 10.4 Booster packs

Pack value should derive from expected contents relative to the current phase:

- **Arcana/Spectral:** can have genuine exploration and strategy-seeding value early;
- **Celestial:** should be much more tightly gated by actual poker-hand evidence;
- **Joker/other packs:** should account for immediate survival/meta value and the chance of revealing explicitly mapped components for leading strategies.

Late-game packs should lose value when most plausible outcomes do not advance the dominant/relevant strategies.

---

## 11. Multiple strategies and compatibility

The agent may intentionally chase several compatible strategies while the run develops.

Example:

```text
Face Cards + Pair + Steel
```

All three remain independent peer strategies. The runtime does not need a nested `Face Pair Steel` playbook.

Compatibility emerges from:

- shared explicitly mapped components;
- current deck shape;
- positive/negative component evidence;
- actual run state.

By Ante 6, one should normally become dominant while at most two remain relevant.

Most apparent Joker clashes should emerge naturally from these positive and negative playbook relationships rather than requiring a large pairwise Joker-conflict database.

---

## 12. Shop behavior implied by the system

At the beginning of the run:

```text
Pair score      0
Flush score     0
Steel score     0
Face score      0
...
```

A Joker's strategy adjustment is therefore approximately zero. The agent buys from ordinary/meta/context value.

After acquiring a Joker with mapped relationships, those strategy scores change. Future candidates are then evaluated against the new rankings.

Example:

```text
Current run:
Pair   10
Steel   6
Straight 1

Candidate Joker X:
Pair: Gold
Steel: Bronze
Straight: Banned
```

Joker X receives strong positive alignment from Pair, smaller positive alignment from Steel, and a negative contribution from Straight. Ante determines how strongly that net alignment affects the final purchase value.

A speculative Planet might produce:

```text
Candidate: Neptune
Straight Flush evidence: negligible
Current dominant/relevant strategies: no Straight Flush support
Result: reject paid acquisition
```

The same strategy relationships should inform Joker acquisition, consumables, vouchers, packs, rerolls, sell/replace decisions, and resource valuation.

---

## 13. Deck/stake cartridges

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

## 14. Implementation order

Do **not** continue strategy-aware production wiring until the catalogue is sufficiently complete.

1. Finalize the universal strategy list across the catalogue files.
2. Audit and fill exact named Gold/Silver/Bronze/banned mappings for every strategy.
3. Encode universal `StrategyDefinition` data and tunable relationship weights.
4. Generate inverse component -> strategy/tier indices automatically.
5. Implement current-state strategy recomputation and event triggers for buy/sell/use/permanent deck changes.
6. Implement candidate strategy alignment as a function of current positive strategy scores, candidate tier, and Ante pressure.
7. Add deck/stake effectiveness modifiers.
8. Implement dominant/relevant ranking and Ante-based exploration/convergence/specialization pressure.
9. Integrate strategy state into D1–D14, including sell/replace behavior.
10. Add deterministic tests for scoring, removal on sell, Planet investment, conflicts, ranking, pivots, consumables, Planet suppression, packs, and hand preference.
11. Run specialized live validation.
12. Resume the v1.0 autonomous acceptance gate only after the strategy system is proven.

---

## 15. Non-negotiable behavioral rules

- The agent starts with **all strategy scores at zero** unless the starting deck/environment itself supplies explicit current-state evidence.
- Strategy catalogues use exact named components; vague categories are not implementation data.
- Unlisted component means Neutral, not Bronze.
- Strategy scores describe **current build state**, not historical ownership.
- Buying/selling Jokers and using components that alter persistent state trigger strategy recomputation.
- Unopened/held consumables do not increase strategy score merely because they are owned.
- Used Planets contribute small persistent evidence through permanent poker-hand investment.
- Candidate Gold/Silver/Bronze value depends on the current score of the strategies it supports; Gold does not mean mandatory purchase.
- Ante controls strategy influence: weak in Antes 1–2, progressively stronger in Antes 3–5, strong for the dominant + up to two relevant strategies from Ante 6 onward.
- Tarot/Spectral cards may seed strategies early; they are not subject to the same evidence gate as Planets.
- Planets should normally reinforce an evidenced poker-hand direction rather than create one from nothing.
- Banned/conflicting components contribute negative strategy evidence and replacement pressure, not unconditional immediate selling.
- Direct functional contradictions may receive exceptional replacement urgency.
- The dominant strategy guides future build decisions but does not override guaranteed blind survival.
- Neutral/off-strategy generic survival purchases remain legal when needed; speculative late strategy fishing does not.
- Strategy files own component-tier metadata; individual Joker classes do not.
- Deck/stake cartridges modify strategy effectiveness; they do not own or redefine universal strategies.
- Strategy decisions must be explainable in authoritative logs.
