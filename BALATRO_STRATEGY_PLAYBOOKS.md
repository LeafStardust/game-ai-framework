# Balatro Strategy Playbooks

> Design contract for the universal hardcoded strategy catalogue that will drive future Balatro production behavior.
>
> **This file defines strategies before implementation.** Deck/stake cartridges do not own strategies. They may disable, amplify, suppress, or otherwise modify the effectiveness of universal strategies for a particular deck/stake environment.

## 1. Core model

The Balatro agent must stop treating every Joker, Tarot, Planet, Spectral card, voucher, booster pack, and deck modification as an isolated purchase.

Instead, every meaningful build component contributes evidence toward one or more **universal strategy playbooks**.

Examples of universal playbooks include:

- poker-hand strategies: High Card, Pair, Two Pair, Three of a Kind, Straight, Flush, Full House, Four of a Kind, Straight Flush, Five of a Kind, Flush House, Flush Five;
- mechanic strategies: Face Cards, Faceless, Glass, Steel, Lucky;
- niche/synergy strategies: Aces, Smeared/Splash + Flower Pot, Canio Destruction, Vampire.

These labels are useful for humans organizing the catalogue, but **the runtime must treat every playbook as a peer in one flat strategy pool**. There are no primary, advanced, or overlay strategy classes.

A run may pursue several compatible playbooks while evidence is weak. It must gradually converge as the run develops.

By late game the intended state is:

- **1 dominant strategy** — the main direction of future purchases and deck shaping;
- **0–2 relevant strategies** — still sufficiently compatible and supported to influence decisions;
- all other strategies heavily suppressed unless a genuinely transformative pivot appears.

The dominant strategy does not dictate every hand the agent must play. Survival and guaranteed blind clears remain superior to strategic purity.

---

## 2. What a playbook contains

Each universal playbook will eventually be encoded as data with at least:

- stable strategy ID;
- human-readable name;
- strategic identity / intended scoring engine;
- Gold components;
- Silver components;
- Bronze components;
- hard conflicts;
- soft conflicts;
- relevant poker hands, when applicable;
- preferred Planets, when applicable;
- preferred Tarot/Spectral transformations;
- preferred vouchers / booster families when materially relevant;
- deck-shape evidence;
- entry evidence;
- maturity/completion evidence;
- natural pivot relationships;
- abandonment conditions.

A component may belong to several playbooks at different tiers.

Example conceptually:

```text
Mime
  High Card: Gold
  Steel: Gold
  Face Cards: Silver
  Flush: Bronze
```

The tier is therefore **not a global item ranking**. It describes how valuable that component is *inside a particular strategy*.

---

## 3. Canonical data ownership

The canonical source of truth should remain **strategy-centric**:

```python
StrategyDefinition(
    id="steel",
    gold_components={...},
    silver_components={...},
    bronze_components={...},
    conflicts={...},
    ...
)
```

The runtime should automatically generate the inverse lookup:

```python
component -> [(strategy, tier), ...]
```

This gives shop evaluation the convenient question:

> "Which strategies does this Joker/consumable advance, and by how much?"

without duplicating tier metadata inside every Joker/consumable implementation.

This also prevents the 150 Joker classes from becoming the authoritative strategy database.

---

## 4. Gold / Silver / Bronze semantics

### Gold — defining / premium synergy

Gold means the component is one of the strongest reasons to pursue or continue that playbook.

Typical Gold evidence:

- directly defines the strategy;
- creates a major multiplicative/scaling engine for it;
- dramatically increases its consistency;
- provides a core transformation the strategy needs;
- turns an otherwise weak strategy into a realistic run-winning route.

Gold is **not an unconditional auto-buy**. Survival, affordability, slot pressure, boss constraints, and stronger existing strategies can still override it.

### Silver — strong reinforcement

Silver means the component works extremely well in the playbook but does not define it alone.

Several Silver components can collectively create enough evidence to elevate a strategy even without a Gold component.

### Bronze — compatible / bridge support

Bronze means the component contributes usefully but is replaceable, generic, or only moderately synergistic.

Bronze pieces are important early because the agent cannot wait for perfect Gold/Silver rolls before buying anything.

Bronze evidence alone must not hard-lock a strategy.

### Conflict

A strategy may also mark components or deck shapes as:

- **hard conflict** — directly undermines the strategy;
- **soft conflict** — pulls resources/build structure away from it but may coexist temporarily.

---

## 5. Strategy evidence and ranking

The agent maintains a score for every universal playbook from **public run state only**.

Evidence may include:

- owned Jokers and their Gold/Silver/Bronze relationships;
- held consumables;
- permanent deck modifications;
- card ranks/suits/enhancements/seals/editions;
- poker-hand level investment;
- actual repeated hand usage;
- current Joker/consumable slot investment;
- existing synergistic combinations;
- conflicts already present;
- deck/stake effectiveness modifiers;
- economic cost already sunk into the strategy.

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

The exact numerical weights belong in implementation and testing, not this document.

---

## 6. Ante progression: explore -> converge -> commit

### Antes 1–2 — mandatory exploration / foundation

The run normally begins with no meaningful playbook evidence.

Therefore the agent **must not refuse useful purchases simply because no active strategy exists yet**.

In Antes 1–2 it should intentionally acquire useful scoring/economy/build pieces that:

- improve immediate survival;
- have broadly useful Bronze value;
- create Silver/Gold evidence for one or more strategies;
- include worthwhile Tarot/Spectral cards or packs capable of creating useful deck structure or seeding a strategy;
- do not catastrophically damage economy.

The objective is to create strategic evidence from RNG rather than demand that RNG already match a nonexistent strategy.

A completely empty Joker board caused by "nothing matches my strategy" is a policy failure during this phase.

Planet spending is different: a Planet primarily reinforces one poker hand, so the agent should normally require actual evidence for that poker-hand direction before buying or consuming it.

### Antes 3–5 — convergence

By Ante 3 the current inventory and deck shape should begin separating promising strategies from noise.

The agent increasingly prefers:

- Gold/Silver components of leading strategies;
- transformations that make those strategies more reliable;
- Planets matching poker-hand strategies that have real evidence;
- packs whose expected contents have meaningful strategic utility.

Pivots remain allowed. A new Gold component can overtake the current leader when the existing investment is still shallow.

The agent should gradually stop paying for unrelated speculative directions.

### Ante 6+ — dominant + relevant shortlist

By Ante 6 the run should normally expose:

- exactly **one dominant strategy**, when meaningful evidence exists;
- up to **two relevant strategies** that remain compatible and sufficiently supported.

Future purchases are strongly biased toward those strategies.

However, shortlist membership is **not a prohibition system**. If the agent has an empty Joker slot and the shop provides no on-strategy component, it may buy a strong generic/off-strategy bridge when doing so materially improves survival or scoring.

The important behavior is:

> stop spending scarce resources chasing random new strategies that have little relationship to the established run.

A late transformative pivot remains possible, but its required advantage must increase with sunk investment and Ante.

---

## 7. Dominant strategy versus hand selection

A playbook describes **what the run is building toward**, not an absolute command for D1.

Example:

- dominant strategy: Flush;
- current hand contains a viable Flush line;
- another available hand already guarantees the blind clear.

The agent may take the guaranteed clear instead of forcing the Flush.

When survival is not at risk, D1 should prefer:

- playing the strategic hand;
- discarding toward the strategic hand;
- preserving cards important to the dominant/relevant strategies;
- triggering strategic scaling engines when the lost immediate value is acceptable.

Priority remains approximately:

1. guarantee / preserve blind survival;
2. minimize unnecessary hand expenditure when strategically safe;
3. pursue the dominant strategy's intended scoring pattern;
4. reinforce relevant strategies when compatible;
5. avoid unrelated speculative behavior.

---

## 8. Consumables, Planets, and packs

This strategy model is specifically intended to eliminate pointless consumable and booster spending, but **Tarot/Spectral exploration and Planet investment must not use the same gate**.

### Tarot / Spectral cards — allowed to seed strategies

Tarot and especially Spectral cards can materially reshape the deck, create enhanced cards, duplicate ranks, destroy cards, change suits, or otherwise create the structural evidence that a strategy needs.

Therefore in Antes 1–2 they may be acquired and used **before a dominant or relevant strategy exists** when their effect has credible standalone structural value or can seed one or more viable playbooks.

Examples:

- suit conversion can seed Flush or Smeared/Splash + Flower Pot;
- card destruction can begin rank concentration, Canio Destruction, Faceless shaping, or general deck thinning;
- enhancement creation can seed Steel, Glass, Lucky, Vampire, etc.;
- rank conversion/duplication can seed Aces, Three/Four/Five of a Kind, Full House, or other rank-concentration plans.

Early Tarot/Spectral openness is deliberate exploration, not random use. The agent should still reject transformations that are immediately harmful, have negligible structural value, or destroy stronger existing evidence.

As the run converges during Antes 3–5, Tarot/Spectral value should increasingly depend on whether the effect advances the leading strategies. By Ante 6+, unrelated transformations should lose most speculative value unless they enable a genuinely transformative pivot or are required for survival.

### Planets — require poker-hand evidence

Planets are fundamentally different because they mostly spend resources to permanently upgrade **one specific poker hand** rather than opening a broad family of future build directions.

A Planet must not become attractive merely because its effect is generically positive, and a Planet should not be used as the thing that invents a poker-hand strategy from nothing.

Before buying or consuming a Planet, the run should normally have meaningful evidence for that poker-hand direction through one or more of:

- the poker hand is already dominant or relevant;
- owned Jokers materially reward that poker hand;
- deck shape makes the poker hand reliably constructible;
- actual repeated hand usage demonstrates that it is a real scoring line;
- existing hand-level investment and supporting components show an intentional transition toward it.

Late-game off-strategy Planets should normally be ignored. Unsupported speculative upgrades such as Neptune with no Straight-Flush structure are explicit policy failures.

### Booster packs

Pack families inherit the same asymmetry.

- **Arcana/Spectral packs:** may have real exploratory value in Antes 1–2 because their contents can create strategy evidence and deck structure.
- **Celestial packs:** should normally require credible poker-hand evidence because their primary value is hand-specific Planet investment.
- As convergence increases, all pack purchases should increasingly derive value from the dominant/relevant strategies plus immediate survival utility.

The agent should never reduce pack evaluation to "packs are good." It should ask whether the plausible contents can create or reinforce useful strategic structure at the current Ante.

---

# 9. Universal playbook catalogue

The following sections define the initial catalogue to encode. The grouping is documentation-only; runtime strategies remain peers.

## 9.1 Poker-hand playbooks

### High Card

**Identity:** low construction burden; repeated safe scoring with Joker scaling and/or held-card value.

**Gold examples:** Stuntman; strong High-Card repetition/scaling engines; Baron + Mime when the deck actually supports held Kings.

**Silver examples:** Supernova/Card Sharp when High Card is already repeated; held-card scoring that naturally preserves cards in hand; reliable card-independent scaling.

**Bronze examples:** generic flat Chips/Mult/economy compatible with one-card play.

**Strategic support:** Pluto; deck thinning; Steel/held-card manipulation when compatible.

**Conflicts:** five-card-only engines; heavy rank/suit restructuring for unrelated hands.

---

### Pair

**Identity:** low-cost hand construction around reliable duplicated ranks.

**Gold examples:** The Duo; strong Pair-specific scaling/payoff.

**Silver examples:** Jolly Joker; Sly Joker; Half Joker; repeated-hand scaling once Pair is established.

**Bronze examples:** generic scoring/economy and compatible rank payoffs.

**Strategic support:** Mercury; light rank duplication; selective thinning.

**Natural transitions:** Two Pair, Three of a Kind, Full House.

---

### Two Pair

**Identity:** repeated four-card scoring around several duplicated ranks.

**Gold examples:** Spare Trousers; dedicated Two-Pair scaling.

**Silver examples:** Mad Joker; Clever Joker; Pair-compatible payoff; Square Joker when exactly-four-card play is reliable.

**Bronze examples:** generic scoring/economy and temporary Pair support.

**Strategic support:** Uranus; multiple duplicated-rank clusters.

---

### Three of a Kind

**Identity:** deliberate single-rank concentration without requiring full endgame rank collapse.

**Gold examples:** The Trio; dedicated Three-of-a-Kind multipliers/scalers; powerful rank-copying when a target rank is already established.

**Silver examples:** Zany Joker; Wily Joker; compatible rank-specific payoff.

**Bronze examples:** generic scoring/economy that does not require rank diversity.

**Strategic support:** Venus; Death/Strength/Cryptid-style concentration where feasible.

**Natural transitions:** Full House, Four of a Kind, Five of a Kind.

---

### Straight

**Identity:** preserve rank connectivity and invest in consistency enablers.

**Gold examples:** Shortcut; Four Fingers; Runner; The Order.

**Silver examples:** Crazy Joker; Devious Joker; Superposition where Ace Straights are genuinely common.

**Bronze examples:** generic scoring/economy that does not destroy rank coverage.

**Strategic support:** Saturn; connector preservation; removal of isolated/excess duplicate ranks.

**Conflicts:** mature single-rank concentration.

---

### Flush

**Identity:** concentrate effective suit density and exploit Flush/suit payoff.

**Gold examples:** The Tribe; Smeared Joker when it materially increases effective suit density; Four Fingers; strong suit payoff matching the actual deck.

**Silver examples:** Droll Joker; Crafty Joker; Castle; suit-specific scoring matching existing conversion.

**Bronze examples:** generic scoring/economy and temporary suit support.

**Strategic support:** Jupiter; suit conversion; selective off-suit destruction.

**Natural transitions:** Straight Flush when Straight structure also becomes real; Flush House/Flush Five after strong rank concentration.

---

### Full House

**Identity:** maintain at least two meaningful rank clusters and repeatedly assemble 3+2.

**Gold examples:** The Family; strong rank-manipulation packages that preserve two clusters rather than collapsing to one.

**Silver examples:** dedicated Full-House Chips/Mult; Pair/Three-of-a-Kind components that remain useful inside Full House.

**Bronze examples:** generic scoring and rank-compatible economy.

**Strategic support:** Earth; controlled duplication/destruction.

**Conflicts:** indiscriminate single-rank collapse unless intentionally pivoting upward.

---

### Four of a Kind

**Identity:** heavy concentration around one target rank.

**Gold examples:** The Family; powerful rank-copy/destruction engines once target-rank density exists.

**Silver examples:** Four-of-a-Kind direct Chips/Mult; rank-specific payoff matching the target rank.

**Bronze examples:** generic scoring compatible with concentrated ranks.

**Strategic support:** Mars; repeated target-rank creation; off-rank destruction.

**Natural transitions:** Five of a Kind; Flush Five when suit concentration also exists.

---

### Straight Flush

**Identity:** simultaneously reliable Straight structure and effective suit concentration.

**Gold examples:** Shortcut/Four Fingers combined with real suit control; The Order/The Tribe when both conditions are realistically repeatable.

**Silver examples:** compatible Straight or Flush engines already supported by deck shape.

**Bronze examples:** generic scoring that does not damage either requirement.

**Strategic support:** Neptune.

**Entry requirement:** must have substantial existing structural evidence. Neptune alone is never enough.

---

### Five of a Kind

**Identity:** extreme single-rank concentration.

**Gold examples:** Cryptid/Ouija/rank-copy engines after a target rank has already become dominant; rank payoff matching that rank.

**Silver examples:** Four/Three-of-a-Kind engines that remain active while transitioning.

**Bronze examples:** generic scaling compatible with rank collapse.

**Strategic support:** Planet X.

**Entry requirement:** sufficient target-rank density; never an early speculative default.

---

### Flush House

**Identity:** Full-House rank clustering plus suit concentration.

**Gold examples:** rank-copy + suit-conversion packages capable of repeatedly creating 3+2 in one suit/effective suit.

**Silver examples:** Full-House and Flush components already supported simultaneously.

**Strategic support:** Ceres.

**Entry requirement:** mature Full-House/Flush structural evidence.

---

### Flush Five

**Identity:** same-rank same-suit concentration.

**Gold examples:** rank-copy and suit-copy/conversion effects when the deck already contains a meaningful nucleus of identical rank+suit cards.

**Silver examples:** Five-of-a-Kind and Flush components that remain compatible.

**Strategic support:** Eris.

**Entry requirement:** strong existing identical-card concentration; never speculative from a normal deck.

---

## 9.2 Mechanic-specific playbooks

### Face Cards

**Identity:** preserve/create Jacks, Queens, and Kings and exploit face-card triggers.

**Gold examples:** major face-card multipliers/scalers such as Triboulet-style payoff; Pareidolia when it unlocks multiple face-card effects; strong face-card retrigger packages.

**Silver examples:** Smiley Face; Scary Face; Business Card; Photograph; Sock and Buskin when sufficient face density exists.

**Bronze examples:** generic scoring/economy that does not require destroying face cards.

**Preferred transformations:** Strength/rank manipulation that increases useful face density; selective destruction of irrelevant low ranks.

**Conflicts:** Faceless/No-Face strategies; Ride the Bus-style no-face requirements.

---

### Faceless / No-Face

**Identity:** remove or avoid face cards and exploit effects that benefit from their absence/destruction.

**Gold examples:** Ride the Bus when the deck can reliably avoid scoring face cards; Faceless Joker when discard structure supports it.

**Silver examples:** low-rank payoff engines; destruction tools that remove face cards while improving deck consistency.

**Bronze examples:** generic scoring/economy compatible with low-rank play.

**Conflicts:** Face Cards; Baron/King-heavy held-card packages.

---

### Glass

**Identity:** create and repeatedly exploit Glass cards while managing breakage/replacement risk.

**Gold examples:** Glass Joker; reliable Glass creation/duplication engines when enough Glass density exists.

**Silver examples:** retriggers/multipliers that magnify Glass scoring; deck-copy effects that replenish strong Glass targets.

**Bronze examples:** generic scoring/economy compatible with fragile scoring cards.

**Preferred transformations:** Justice and copy effects applied to strategically valuable ranks/suits.

**Risk:** do not destroy the only reliable clear line merely to maximize Glass value.

---

### Steel

**Identity:** keep Steel cards in hand and multiply held-card value.

**Gold examples:** Steel Joker; Mime; Baron when Steel Kings/King density make the package coherent.

**Silver examples:** held-card scoring/retrigger effects; hand-size support; card generation that increases useful held cards.

**Bronze examples:** generic scoring requiring few played cards.

**Preferred transformations:** Chariot; Death/copy effects targeting valuable Steel cards.

**Natural compatibility:** High Card, Pair, Face Cards depending on deck shape.

---

### Lucky

**Identity:** create Lucky-card density and exploit repeated Lucky triggers/scaling.

**Gold examples:** Lucky Cat once Lucky-card usage is real; retrigger engines that substantially increase Lucky proc opportunities.

**Silver examples:** Magician; card-copy effects targeting strong Lucky cards; compatible per-card scoring.

**Bronze examples:** generic scoring/economy that keeps Lucky cards playable.

**Requirement:** Lucky evidence must come from actual enhanced cards/components, not theoretical future Magician access.

---

## 9.3 Niche synergy playbooks

### Aces

**Identity:** concentrate and exploit Ace-specific scoring while retaining compatible poker-hand routes.

**Gold examples:** Scholar; strong Ace duplication/concentration engines when Ace density is already meaningful.

**Silver examples:** Fibonacci where its rank set remains compatible; Superposition in Straight/Ace shells; compatible rank retriggers.

**Bronze examples:** generic scoring/economy that does not require destroying Aces.

**Preferred transformations:** Strength/rank manipulation and copy effects that increase useful Ace density.

**Potential hand shells:** Pair/Three/Four/Five of a Kind, High Card, Straight depending on the rest of the build.

---

### Smeared / Splash + Flower Pot

**Identity:** satisfy Flower Pot's multi-suit requirement reliably by manipulating what counts as scored/effective suits and by ensuring required cards score.

**Gold examples:** Flower Pot plus Smeared Joker and/or Splash when that combination materially raises trigger consistency.

**Silver examples:** suit-generation/conversion tools that fill missing color/suit requirements; retrigger/scoring pieces compatible with playing the required mixed-suit hand.

**Bronze examples:** generic scaling that works with multi-card mixed-suit plays.

**Requirement:** individual pieces should not overvalue this strategy until enough of the package exists to make Flower Pot triggering realistic.

---

### Canio Destruction

**Identity:** scale Canio by deliberately destroying face cards while preserving a reliable scoring shell.

**Gold examples:** Canio; repeatable face-card destruction tools once Canio is owned.

**Silver examples:** Hanged Man/other destruction effects targeting face cards; deck-shaping tools that create expendable face cards if economically sensible.

**Bronze examples:** scoring/economy that keeps the run safe during destruction scaling.

**Conflict:** Face Cards is normally incompatible once Canio destruction becomes the dominant plan.

**Requirement:** destruction should be intentional and valuation-aware, not random thinning.

---

### Vampire

**Identity:** feed enhanced cards into Vampire to scale its multiplier while maintaining enough enhancement generation to sustain growth.

**Gold examples:** Vampire; repeatable enhancement-generation engines that can create cards for Vampire to consume.

**Silver examples:** Tarot generation; enhancement creation that is cheap/repeatable; deck-control tools that route expendable enhanced cards into scoring hands.

**Bronze examples:** generic scoring/economy that supports the scaling period.

**Conflict:** Steel/Glass/Lucky strategies may conflict when Vampire consumes enhancements those strategies need to preserve.

**Requirement:** the agent must value the *conversion pipeline* (create enhancement -> safely score it -> Vampire consumes it -> permanent scaling), not merely the presence of Vampire.

---

## 10. Multiple strategies and compatibility

The agent should intentionally chase several strategies when their components overlap.

Example:

```text
Face Cards + Pair + Steel
```

can coexist because:

- Pair may provide the poker-hand shell;
- Face Cards may define which ranks matter;
- Steel may define held-card/value manipulation.

All three remain peer playbooks. The agent does not need a special nested "Face Pair Steel" strategy object.

Compatibility emerges from:

- shared components;
- deck shape;
- lack of conflicts;
- actual run evidence.

Eventually one becomes dominant because it accumulates the strongest evidence and sunk investment.

---

## 11. Shop behavior implied by the catalogue

When evaluating a shop item, the future policy should be able to produce reasoning such as:

```text
Candidate: Joker X

Dominant strategy: Face Cards
  tier: Gold
  contribution: very high

Relevant strategy: Pair
  tier: Silver
  contribution: high

Relevant strategy: Steel
  tier: none

Result: strongly preferred if affordable and survival-safe.
```

A different item might be:

```text
Candidate: Neptune

Dominant strategy: Face Cards
  tier: none

Relevant strategy: Pair
  tier: none

Relevant strategy: Steel
  tier: none

Straight Flush evidence: negligible

Result: reject except for exceptional independent survival/value reasons.
```

This same model should govern Jokers, consumables, Planets, vouchers, packs, rerolls, and sell/replace decisions.

---

## 12. Deck/stake cartridges

Universal playbooks remain unchanged across decks/stakes.

A cartridge may provide only environment-specific modifiers such as:

```python
StrategyModifier(
    strategy_id="flush",
    enabled=True,
    effectiveness=1.10,
    score_bonus=0.0,
)
```

Examples:

- a deck with unusual suit structure may amplify or suppress Flush-related strategies;
- reduced discard availability may reduce the effectiveness of Straight/Flush strategies that depend heavily on digging;
- stake mechanics may change economy/scaling risk and therefore alter strategy effectiveness;
- a strategy can be disabled for an environment only when it is genuinely infeasible or outside that cartridge's supported competence.

The cartridge must never redefine what Gold/Silver/Bronze means for a universal strategy.

---

## 13. Implementation order

Do **not** continue strategy-aware production wiring until this catalogue is sufficiently complete.

Implementation order:

1. Review and finalize the universal playbook list.
2. Fill concrete Gold/Silver/Bronze component mappings for each playbook.
3. Encode the universal strategy definitions.
4. Generate inverse component -> strategy/tier indices automatically.
5. Add deck/stake strategy-effectiveness modifiers.
6. Implement per-run evidence scoring and Ante-based exploration/convergence/commitment pressure.
7. Integrate strategy state into D1–D14.
8. Add deterministic unit/regression tests for strategy ranking, pivots, consumable/Planet suppression, packs, and hand preference.
9. Run specialized live validation.
10. Only then resume the v1.0 autonomous acceptance gate.

---

## 14. Non-negotiable behavioral rules

- The agent starts with **no assumed strategy**.
- Antes 1–2 must permit and normally require useful purchases so RNG can create strategy evidence.
- Tarot/Spectral cards may seed strategies during early exploration when their structural effect is useful; they do not require a pre-existing dominant strategy.
- Planets normally require actual poker-hand strategy evidence before purchase/use and must not create a poker-hand strategy merely because upgrading a hand is generically positive.
- Antes 3–5 progressively favor coherent existing directions.
- By Ante 6, when evidence exists, the run should normally have **one dominant strategy and at most two relevant strategies**.
- The dominant strategy guides future build decisions but does not override guaranteed blind survival.
- Relevant strategies prevent over-locking and allow compatible components/offers to fill remaining slots.
- Off-strategy generic survival purchases remain legal when needed; speculative new-strategy fishing does not.
- Gold/Silver/Bronze are strategy-relative relationships, never global item tiers.
- Deck/stake cartridges modify strategy effectiveness; they do not own or redefine universal strategies.
- Strategy decisions must be explainable in authoritative logs.