# Balatro Strategy Catalogue — Poker Hands

> Concrete universal poker-hand strategy definitions.
>
> These are documentation groupings only. At runtime every strategy is a peer in the same universal strategy pool. See [`BALATRO_STRATEGY_PLAYBOOKS.md`](BALATRO_STRATEGY_PLAYBOOKS.md) for architecture, tier semantics, Ante progression, and implementation rules.

## Shared rule for poker-hand strategies

A Planet is **support for an evidenced poker-hand strategy**, not sufficient strategy evidence by itself.

Early Joker, Tarot, Spectral, deck-shape, and actual hand-use evidence may establish or strengthen a poker-hand strategy. Planet purchases should normally follow that evidence rather than create the direction from nothing.

---

## High Card

**Identity:** low construction burden; repeated safe scoring through Joker scaling, held-card value, and minimal played-card commitment.

**Planet:** Pluto.

### Gold
- Stuntman.
- Strong High-Card repetition/scaling engines when High Card is already being repeated.
- Baron + Mime package when the deck actually supports held Kings.
- Burnt Joker when the run can deliberately use its first discard to scale High Card without damaging survival.

### Silver
- Supernova when High Card is the repeated hand.
- Card Sharp once repeated High Card is reliable.
- Half Joker.
- Space Joker when High Card is the intended level target.
- Green Joker / compatible repeated-hand scaling.
- Blackboard when held-card conditions are realistically maintainable.
- Held-card scoring pieces that naturally fit low-card play.

### Bronze
- Generic flat Chips/Mult.
- Generic economy.
- Card-independent bridge scoring.

### Preferred support
- Deck thinning.
- Steel cards and held-card manipulation where compatible.
- Preserve valuable held cards.

### Conflicts
- Five-card-only scoring engines when the build depends on minimal-card play.
- Heavy rank/suit restructuring for unrelated hands.

### Natural pivots
- Pair when rank duplication appears.
- Steel / Face Cards when held-card structure develops.

---

## Pair

**Identity:** low-cost hand construction around reliable duplicated ranks.

**Planet:** Mercury.

### Gold
- The Duo.
- Strong Pair-specific scaling/payoff.
- Half Joker when Pair is consistently played as two cards.

### Silver
- Jolly Joker.
- Sly Joker.
- Supernova when Pair is established as the repeated hand.
- Card Sharp.
- Burnt Joker / Space Joker when Pair is the chosen level target.
- Rank-specific payoff matching naturally duplicated ranks.

### Bronze
- Generic scoring/economy.
- Temporary rank payoff that does not require destructive restructuring.

### Preferred support
- Light rank duplication via Death/Strength/copy effects.
- Selective thinning that raises pair frequency.

### Conflicts
- Heavy Straight structure.
- Five-card-only packages with no compatible payoff.

### Natural pivots
- Two Pair.
- Three of a Kind.
- Full House.

---

## Two Pair

**Identity:** repeated four-card scoring around several duplicated ranks.

**Planet:** Uranus.

### Gold
- Spare Trousers.
- Dedicated long-run Two-Pair scaling.

### Silver
- Mad Joker.
- Clever Joker.
- Pair-compatible payoff that still triggers on Two Pair.
- Square Joker when exactly-four-card play is reliable.
- Supernova / Card Sharp after Two Pair is established.

### Bronze
- Generic scoring/economy.
- Temporary Pair support.

### Preferred support
- Several duplicated rank clusters rather than one fully dominant rank.
- Death/Strength that improve pair density without collapsing diversity too early.

### Conflicts
- Heavy Straight rank-spacing requirements.
- Excessive single-rank concentration unless intentionally pivoting.

### Natural pivots
- Full House.
- Three/Four of a Kind.
- Pair if construction becomes too expensive.

---

## Three of a Kind

**Identity:** deliberate single-rank concentration without requiring full endgame rank collapse.

**Planet:** Venus.

### Gold
- The Trio.
- Strong Three-of-a-Kind multiplier/scaling engines.
- Powerful rank-copying once a target rank is established.

### Silver
- Zany Joker.
- Wily Joker.
- Pair-condition effects that remain active.
- Rank-specific payoff matching the target rank.
- Half Joker when exactly-three-card play remains advantageous.

### Bronze
- Generic scoring/economy compatible with rank concentration.

### Preferred support
- Death, Strength, Cryptid-style copying/concentration once a target rank exists.
- Destroy off-plan ranks when safe.

### Conflicts
- Mature Straight structure.
- Broad rank-diversity requirements.

### Natural pivots
- Full House.
- Four of a Kind.
- Five of a Kind.
- Flush Five when suit concentration also develops.

---

## Straight

**Identity:** preserve rank connectivity and use consistency enablers to make a fragile five-card hand repeatable.

**Planet:** Saturn.

### Gold
- Shortcut.
- Four Fingers.
- Runner.
- The Order.

### Silver
- Crazy Joker.
- Devious Joker.
- Superposition when Ace Straights are realistically common.
- Card Sharp / Supernova once Straight consistency exists.
- Compatible rank-specific payoff that does not destroy connectivity.

### Bronze
- Generic scoring/economy that preserves rank coverage.

### Preferred support
- Preserve central connectors and useful rank bands.
- Remove isolated/excess duplicate ranks before central connectors.
- Use Death/Strength to repair gaps rather than blindly collapse ranks.

### Conflicts
- Mature single-rank concentration.
- Heavy held-card shells that cannot spare enough cards to assemble Straights.

### Natural pivots
- Straight Flush only when suit density also becomes real.
- High Card/Pair if Straight consistency collapses.

---

## Flush

**Identity:** concentrate effective suit density and exploit Flush/suit-specific payoff.

**Planet:** Jupiter.

### Gold
- The Tribe.
- Smeared Joker when it materially increases effective suit density.
- Four Fingers.
- Bloodstone in a Hearts-focused shell.
- Arrowhead in a Spades-focused shell.
- Onyx Agate in a Clubs-focused shell.
- Rough Gem in a Diamonds-focused shell when its economy contribution is strategically relevant.

### Silver
- Droll Joker.
- Crafty Joker.
- Castle when discard routing can scale it safely.
- Ancient Joker when suit flexibility can exploit it often enough.
- Suit-specific scoring matching actual deck conversion.

### Bronze
- Generic scoring/economy.
- Temporary suit support.

### Preferred support
- Suit conversion.
- Selective off-suit destruction.
- Smeared-aware effective suit counting.

### Conflicts
- Mature single-rank concentration unless transitioning to Flush Five/Flush House.
- Random suit conversion that lowers effective dominant-suit density.

### Natural pivots
- Straight Flush when Straight structure is already real.
- Flush House / Flush Five after substantial rank concentration.

---

## Full House

**Identity:** maintain at least two meaningful rank clusters and repeatedly assemble 3+2.

**Planet:** Earth.

### Gold
- The Family.
- Strong rank-manipulation packages that preserve two useful clusters.

### Silver
- Dedicated Full-House Chips/Mult.
- Pair and Three-of-a-Kind components that remain useful inside Full House.
- Repetition scaling once Full House is realistically repeatable.

### Bronze
- Generic scoring/economy compatible with clustered ranks.

### Preferred support
- Controlled duplication/destruction.
- Maintain a primary triple-capable rank and a secondary pair-capable rank.

### Conflicts
- Indiscriminate single-rank collapse unless deliberately pivoting upward.
- Mature Straight structure.

### Natural pivots
- Four/Five of a Kind if one rank dominates.
- Flush House if suit concentration also becomes strong.

---

## Four of a Kind

**Identity:** heavy concentration around one target rank.

**Planet:** Mars.

### Gold
- The Family.
- Powerful rank-copy/destruction engines once target-rank density exists.

### Silver
- Four-of-a-Kind direct Chips/Mult.
- Rank-specific payoff matching the target rank.
- Three-of-a-Kind engines that remain useful during transition.

### Bronze
- Generic scaling compatible with concentrated ranks.

### Preferred support
- Repeated target-rank creation.
- Off-rank destruction.

### Entry evidence
- Existing target-rank density or strong repeatable rank-copying capacity.

### Natural pivots
- Five of a Kind.
- Flush Five if suit concentration also exists.

---

## Straight Flush

**Identity:** simultaneously reliable Straight structure and effective suit concentration.

**Planet:** Neptune.

### Gold
- Shortcut/Four Fingers combined with real suit control.
- The Order/The Tribe when both conditions are realistically repeatable.
- Strong combined Straight + suit consistency packages.

### Silver
- Compatible Straight or Flush engines already supported by deck shape.

### Bronze
- Generic scoring that does not damage either structural requirement.

### Entry evidence
- Substantial existing Straight and Flush structural evidence.
- Neptune alone is never enough.

### Conflict
- Treat as speculative from an ordinary unmodified deck.

---

## Five of a Kind

**Identity:** extreme single-rank concentration.

**Planet:** Planet X.

### Gold
- Cryptid/Ouija/rank-copy engines after a target rank is already dominant.
- Strong payoff tied to the dominant rank.

### Silver
- Four/Three-of-a-Kind engines that remain useful during transition.

### Bronze
- Generic scaling compatible with rank collapse.

### Entry evidence
- Sufficient target-rank density. Never an early speculative default.

### Natural pivots
- Flush Five if suit identity also becomes concentrated.

---

## Flush House

**Identity:** Full-House rank clustering plus suit concentration.

**Planet:** Ceres.

### Gold
- Rank-copy + suit-conversion packages capable of repeatedly creating 3+2 in one suit/effective suit.

### Silver
- Full-House and Flush components already supported simultaneously.

### Entry evidence
- Mature Full-House/Flush structural evidence.
- Ceres alone is never sufficient evidence.

---

## Flush Five

**Identity:** same-rank same-suit concentration.

**Planet:** Eris.

### Gold
- Rank-copy and suit-copy/conversion effects when a meaningful nucleus of identical rank+suit cards already exists.

### Silver
- Five-of-a-Kind and Flush components that remain compatible.

### Entry evidence
- Strong existing identical-card concentration.
- Never speculative from a normal deck.
