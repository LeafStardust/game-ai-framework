# Balatro Strategy Catalogue

Canonical list of accepted Balatro Bonds. Architecture and Currency Wars analogy: `BALATRO_STRATEGY_SYSTEM.md`. Exact component/state weights: `BALATRO_STRATEGY_CONTRIBUTIONS.md`.

## Catalogue rules

A Bond is a persistent, developable strategic axis. It is not every Joker, every synergy pair, or every named build.

```text
LOCKED = defining prerequisite absent
R0     = naturally available Bond below R1
R1-R5  = increasingly developed rank
```

Ranks measure structural development. Realization (`DORMANT/PARTIAL/ACTIVE/MATURE`) measures whether the engine is actually functioning. Build Health answers whether it is strong enough to survive/scale.

Contributors are alternative/additive paths into one Bond meter; R2-R5 are never sequential item recipes.

---

# Accepted Bonds

## 1. Burnt

**Identity:** deliberate permanent specialization of a selected poker hand through the Burnt first-discard leveling engine.

**Unlock:** Burnt Joker required. **Thresholds:** `8 / 12 / 17 / 23 / 30`.

**Target:** strongest compatible poker-hand Bond; High Card fallback when no meaningful specialization exists. Existing permanent hand investment creates switching resistance.

**Rank behavior:**
- R1 recognize first-discard permanent value;
- R2 reinforce selected target and targeted leveling infrastructure;
- R3 actively shape/protect Burnt specialization;
- R4 may be principal power engine and should take safe first-discard scaling before trivial clears;
- R5 capstone commitment with very high pivot resistance.

**Conflict:** No-Discard.

Implementation: `games/balatro/bonds/burnt.py`.

## 2. Held Cards

**Identity:** strategic value created by cards intentionally retained in hand for direct held-card payoff.

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`.

Direct contributors currently include Baron, Shoot the Moon, Raised Fist, Steel held infrastructure, and extra hand size.

**Important boundary:** Mime contributes **zero** Held Cards quota; it belongs to Held Retrigger. Gold Cards and Blue Seals are excluded from Held Cards. Their held state is a trigger condition, not this Bond's strategic identity.

Rank progression increasingly preserves held payoff cards, shapes hand/deck state around them, and at R4+ may make held-card value a power engine.

Implementation: `games/balatro/bonds/held_cards.py`.

## 3. Held Retrigger

**Identity:** repeated triggering of abilities on cards held in hand.

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`.

Mime is the strongest current direct contributor. Red Seal density is an independent route. Blueprint/Brainstorm contribute conditionally when Mime exists because copying Mime increases held retrigger capacity.

Rank progression increasingly values retriggerable held effects and at high rank actively seeks Held Cards/Steel compositions.

**Synergy:** Held Cards, Steel.

## 4. Steel

**Identity:** deck development around Steel cards as repeatable held XMult infrastructure.

**Unlock:** none. **Thresholds:** `4 / 8 / 14 / 21 / 29`.

Steel density is the core persistent state; Steel Joker and Red-Seal Steel overlap add structural development. Steel cards may contribute to both Steel and Held Cards without double-counting mechanical score.

Rank progression increasingly avoids needlessly playing Steel payoff cards, shapes deck density, and at R4+ can become a power engine.

**Synergy:** Held Cards, Held Retrigger.

## 5. Pair

**Identity:** deliberate scoring specialization around Pair as the repeated poker-hand plan.

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`.

The Duo, Jolly Joker, Sly Joker, Half Joker and permanent Pair levels currently contribute. Play-count history alone does not create Pair development.

At higher ranks Pair increasingly governs Planet/deck/scoring choices and may become the principal poker-hand engine.

## 6. High Card

**Identity:** deliberate scoring specialization around reliable High Card execution.

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`.

Stuntman, Half Joker and permanent High Card levels currently contribute. Burnt targeting High Card does not make Burnt itself High Card quota.

At higher ranks High Card increasingly governs scoring/deck choices and may become the principal poker-hand engine.

## 7. Aces

**Identity:** deck/rank specialization around Ace density and Ace-specific payoff.

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`.

Scholar is the strongest current direct contributor; Fibonacci is weaker shared rank support; Ace density is persistent state. DNA contributes only once meaningful Ace density exists, because DNA alone does not create an Ace strategy.

At higher ranks the agent should intentionally preserve/create Ace density and value compatible poker-hand/scoring Bonds around it.

## 8. No-Discard

**Identity:** power/economy gained by deliberately avoiding discards.

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`.

Current contributors: Green Joker, Burglar, Delayed Gratification, Ramen, Banner.

At higher ranks the agent increasingly refuses low-value discards, protects zero-discard scaling, and may make no-discard execution a power engine.

**Conflict:** Burnt. Green/Burglar may coexist here; Burglar must never again be described as Burnt support.

## 9. Cash

**Identity:** persistent bankroll/economy infrastructure whose retained money materially improves future power and/or direct scoring.

**Unlock:** none. **Thresholds:** `4 / 9 / 15 / 22 / 30`.

Current contributors include Bull, Bootstraps, Rocket, Golden Joker, To the Moon, Satellite, Reserved Parking and bankroll bands.

A high Cash rank is **not a command to hoard money blindly**. Build Health and projected improvement still decide whether spending is correct. Bull/Bootstraps-style scoring makes bankroll preservation much more authoritative than ordinary economy.

## 10. Lucky

**Identity:** deck development around Lucky-card triggers and Lucky-specific scaling/probability support.

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`.

Current contributors: Lucky Cat, Oops! All 6s, Lucky-card density.

Higher ranks increasingly value Lucky creation, trigger support, and deck density while actual trigger output remains a realization/scoring concern.

## 11. Glass

**Identity:** deck development around Glass XMult and Glass-specific persistent scaling.

**Unlock:** none. **Thresholds:** `4 / 8 / 13 / 19 / 26`.

Current contributors: Glass Joker, Glass-card density, and accumulated Glass destruction while Glass Joker remains owned.

Higher ranks increasingly shape deck/play around Glass payoff and may make Glass a power engine. Break risk remains part of score/survival evaluation, not rank itself.

## 12. Face Cards

**Identity:** deck/scoring specialization around cards treated as face cards and face-card-specific payoff.

**Unlock:** none. **Thresholds:** `4 / 9 / 15 / 22 / 30`.

Current contributors: Pareidolia, Sock and Buskin, Photograph, Scary Face, Smiley Face, Business Card, and natural face-card density.

Higher ranks increasingly shape the deck and scoring line around face cards. Bosses such as The Plant suppress realization/score projection rather than deleting structural Face Cards rank.

---

## Sparse relationship graph currently frozen

```text
Burnt x No-Discard             = CONFLICT
Held Cards <-> Held Retrigger  = SYNERGY
Held Cards <-> Steel           = SYNERGY
Held Retrigger <-> Steel       = SYNERGY
```

All unlisted pairs default to neutral. Do not construct an exhaustive pair matrix.

## Composition motifs

Named builds remain above the Bond layer. Canonical example:

```text
Held Cards + Held Retrigger + Steel + King structure
        -> Baron-Mime-Steel motif
```

Baron-Mime-Steel is therefore not another Bond.

## Implementation status

Burnt and Held Cards have dedicated evaluators. Bonds 3-12 are currently implemented in `games/balatro/bonds/catalogue_batch_one.py` during the catalogue build-out. This may be split into per-Bond modules during the final audit if that improves maintainability.

Production Primary/Secondary/Third runtime selection is still legacy migration infrastructure. Do not wire half the catalogue into live authority until the full Bond set/composer is ready.
