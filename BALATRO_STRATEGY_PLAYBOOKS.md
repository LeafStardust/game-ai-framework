# Balatro Strategy Playbooks

> Design contract for the hardcoded build strategies the Balatro agent will implement after this document is reviewed. This file defines **what a coherent build is** before any further strategy/runtime wiring is added.
>
> These are **build archetype playbooks**, not deck/stake cartridges. Deck and stake playbooks will later modify the value and feasibility of these archetypes without redefining them.

## 1. Purpose

The agent should not infer a build merely from isolated Joker affinities. It should compare the current public run state against a small catalogue of explicit strategic playbooks and ask:

1. Which archetypes are currently feasible?
2. Which archetypes are already supported by owned components and deck shape?
3. Which purchases or transformations materially advance one of those archetypes?
4. Which candidate conflicts with the active archetype?
5. When should the run remain flexible, pivot, commit, or declare the build mature?

The first implementation should remain deterministic and inspectable. Every build decision should be explainable in terms of one or more entries in this catalogue.

---

## 2. Tier semantics

The Gold/Silver/Bronze labels are **archetype-relative component tiers**, not global Joker power rankings.

### Gold — defining component

A Gold component either:

- directly multiplies the target hand/archetype;
- materially changes the feasibility of repeatedly making that hand;
- provides a primary scaling engine whose natural use pattern is the archetype; or
- creates the deck structure needed for the archetype to exist reliably.

A Gold component is strong evidence that the corresponding playbook should become a candidate, but it is **not an automatic purchase or commitment**. Cost, survival, anti-synergy, current deck shape and opportunity cost still matter.

### Silver — strong support

A Silver component:

- directly rewards the target hand without defining the entire run;
- improves consistency, card selection or hand construction;
- provides secondary scaling; or
- becomes excellent once Gold-level structure already exists.

Multiple Silver components plus matching deck structure may justify a build even without a Gold Joker.

### Bronze — bridge / generic support

A Bronze component:

- keeps the run alive while the build is forming;
- provides generic Chips/Mult/economy compatible with the archetype;
- has useful but non-exclusive synergy; or
- is a temporary bridge expected to be replaceable later.

Bronze pieces **must never be sufficient evidence by themselves to lock an archetype**.

### Conflict classes

Each playbook may also identify:

- **Hard conflict** — the component or deck requirement directly prevents the intended strategy from functioning reliably.
- **Soft conflict** — the component pulls resources or deck shaping in another direction but can coexist temporarily.
- **Conditional conflict** — compatible only under a named overlay or special deck state.

---

## 3. Playbook lifecycle

The future implementation should expose a per-archetype state similar to:

`INACTIVE -> CANDIDATE -> FOCUSED -> LOCKED -> MATURE`

### INACTIVE

No meaningful evidence beyond generic Bronze support.

### CANDIDATE

At least one defining signal exists: a Gold component, strong hand-level investment, meaningful deck structure, or a combination of direct Silver components.

### FOCUSED

The run should begin preferring purchases, Planets, Tarot/Spectral transformations and D1 lines that reinforce the archetype, while still allowing a pivot.

### LOCKED

The active build direction is committed. The existing public build-intent boundary remains the default: Antes 1-4 are pivotable and the build locks starting at Ante 5.

Locking must require **coherence**, not merely elapsed Ante. If the run has no meaningful archetype evidence, it may lock as neutral rather than inventing a strategy.

### MATURE

The archetype has enough structure that the agent should stop paying significant speculative cost for unrelated pivots. A mature build normally has:

- repeatable access to its strategic hand;
- at least one reliable base Chips/Mult source;
- at least one scaling or multiplicative endgame source;
- deck structure that supports the target hand rather than fighting it; and
- sufficient economy/survival to reach the next shop/boss.

The exact numeric thresholds for these states belong in implementation/configuration, not in this document.

---

## 4. Shared decision rules

These rules apply to every playbook.

### 4.1 Survival still dominates

A theoretically perfect build component must not be bought, held or pursued when doing so makes the current blind materially unsafe.

### 4.2 Gold does not mean auto-buy

A Gold component can be wrong when:

- its activation requirement is not currently feasible;
- its cost destroys necessary reserve/interest;
- the run already has a stronger conflicting locked build;
- it consumes the last critical Joker/consumable slot for insufficient gain; or
- the current blind/boss makes the transition unsafe.

### 4.3 Deck shape is first-class evidence

Owned-deck rank counts, suit counts, enhancements, seals, editions and hand-level investment must contribute to archetype evidence independently of Joker names.

### 4.4 Temporary Bronze pieces are replaceable

The shop arbiter should be willing to sell a Bronze bridge when a Silver/Gold component creates a materially stronger coherent build.

### 4.5 Advanced hands are transitions, not early fantasies

Straight Flush, Five of a Kind, Flush House and Flush Five should generally be entered from an already functional parent build. The agent must not spend early resources chasing them from an ordinary 52-card deck without structural evidence.

---

# 5. Primary playbooks

## 5.1 High Card

**Strategic hand:** High Card  
**Planet:** Pluto  
**Identity:** Minimal hand-construction burden. Convert consistency, Joker scaling and held-card value into repeated safe scores while playing as few cards as possible.

### Gold components

- **Stuntman** — large card-independent Chips and naturally compatible with a low-card strategy.
- **Supernova** — repeated use of one hand type rewards committing to High Card.
- **Card Sharp** — rewards repeating High Card within the same round once the first hand establishes it.
- **Burnt Joker** — can repeatedly level High Card when the first discard is intentionally shaped as High Card.
- **Baron + Mime package** — Gold only under the Held Kings overlay; High Card is the natural shell because it can leave Kings in hand.

### Silver components

- Half Joker.
- Space Joker.
- Green Joker.
- Ride the Bus under a No-Face overlay.
- Burglar / no-discard support.
- Blackboard when the held-card suit condition is realistically maintainable.
- Shoot the Moon / Raised Fist / other held-card scoring under the appropriate deck shape.

### Bronze components

- Generic flat Chips or Mult Jokers that do not require a larger poker hand.
- Generic economy Jokers.
- Blue Joker, Abstract Joker and similar bridge scoring when they do not create a conflicting build requirement.

### Preferred deck manipulation

- Thin cards that do not contribute to held-card or enhancement plans.
- Prefer valuable single scoring cards over broad rank/suit restructuring.
- Steel cards and held-card value become premium under Baron/Mime or other held-card overlays.
- Do not spend heavily manufacturing pairs/straights/flushes unless pivot evidence already exists.

### D1 play/discard profile

- Prefer the minimum number of played cards that preserves clear probability.
- Preserve valuable held cards.
- Avoid unnecessary discards when Green Joker, Banner, Delayed Gratification or similar no-discard value is active.
- Intentionally use the first discard for Burnt Joker only when the level gain is worth the lost immediate line quality.

### Conflicts

- **Hard/near-hard:** effects requiring four or five played cards when the build depends on one-card plays.
- **Soft:** heavy Straight/Flush/rank-concentration investment.
- **Conditional:** Obelisk is not a High Card engine; it is a pivot engine and should eventually punish continued use of the most-played hand.

### Natural pivots

- Pair if rank duplication and Pair-specific pieces appear.
- Held Kings High Card if Baron/Mime/King density appears.
- No-Face High Card if Ride the Bus and low-rank support become dominant.

### Mature signal

High Card is repeatably clear-capable without hand-shape hunting, has meaningful High Card level/repetition scaling, and has at least one strong late-score source beyond generic Bronze flat stats.

---

## 5.2 Pair

**Strategic hand:** Pair  
**Planet:** Mercury  
**Identity:** Low construction cost with more base scoring than High Card. Build around reliable duplicated ranks while retaining room for held-card and utility effects.

### Gold components

- **The Duo** — direct multiplicative Pair payoff.
- **Half Joker** — Pair naturally fits its small-hand requirement.
- **Supernova** when Pair is already the repeated hand.
- **Burnt Joker / Space Joker** when they are clearly being used to scale Pair levels.

### Silver components

- Jolly Joker.
- Sly Joker.
- Card Sharp.
- Green Joker / generic repeat-hand scaling.
- Rank-specific Jokers when the duplicated rank naturally supports them.

### Bronze components

- Generic Chips/Mult/economy.
- Temporary rank payoffs that do not require destructive deck reshaping.

### Preferred deck manipulation

- Light rank duplication using Death, Strength or card generation.
- Thin isolated low-value cards when doing so raises pair frequency.
- Avoid excessive single-rank concentration until a Three/Four/Five-of-a-Kind pivot is justified.

### D1 play/discard profile

- Prefer two-card Pair plays unless extra scoring cards are necessary.
- Discard toward duplicated ranks while preserving enhanced/held-value cards.
- Do not sacrifice a safe Pair merely to hunt a speculative higher hand.

### Conflicts

- Heavy Straight structure.
- Suit conversion that consumes rank consistency without creating a stronger Flush route.
- Five-card-only scoring packages.

### Natural pivots

- Two Pair when a second duplicated rank and Two Pair pieces appear.
- Three of a Kind when one rank becomes dominant.
- Full House when two rank clusters become reliable.

### Mature signal

Pair is available with little or no discard expenditure, Mercury investment or repeated-hand scaling is meaningful, and the build has a multiplier/scaler capable of carrying late blinds.

---

## 5.3 Two Pair

**Strategic hand:** Two Pair  
**Planet:** Uranus  
**Identity:** Four-card hand with moderate construction requirements and excellent access to pair-based and dedicated Two Pair scaling.

### Gold components

- **Spare Trousers** — defining long-run Two Pair scaling engine.
- **Mad Joker** — direct Two Pair Mult.
- **Clever Joker** — direct Two Pair Chips.
- **The Duo** when the hand-condition model confirms the played Two Pair satisfies Pair-based payoff.
- **Square Joker** when the build consistently plays exactly four cards.

### Silver components

- Jolly Joker / Sly Joker.
- Supernova.
- Card Sharp.
- Burnt Joker / Space Joker when Two Pair is the chosen level target.

### Bronze components

- Generic scoring and economy.
- Temporary Pair support that remains useful inside Two Pair.

### Preferred deck manipulation

- Build several duplicated ranks rather than one dominant rank.
- Death/Strength should improve pair density without collapsing the deck into an unintended single-rank build too early.
- Thinning isolated ranks is useful when it increases the chance of drawing two separate pairs.

### D1 play/discard profile

- Prefer four scoring cards; avoid a fifth kicker unless it materially improves score or triggers another owned effect.
- Preserve multiple pair candidates during discard search.
- When Spare Trousers is active, value safely triggering its scaling even if another hand would score slightly more immediately.

### Conflicts

- Heavy Straight rank-spacing requirements.
- Five-card-only hand packages unless Full House transition is active.
- Over-concentrating one rank can reduce Two Pair reliability and should be treated as a pivot signal instead.

### Natural pivots

- Full House when one pair becomes a triple.
- Three/Four of a Kind when one rank starts dominating.
- Pair if hand size/economy makes Two Pair too expensive to assemble.

### Mature signal

Two Pair is produced consistently, Spare Trousers or another dedicated engine has meaningful scaling, and the deck still contains enough distinct duplicated ranks to sustain the hand.

---

## 5.4 Three of a Kind

**Strategic hand:** Three of a Kind  
**Planet:** Venus  
**Identity:** Rank-concentration build that begins the transition from common hands into high-value repeated-rank strategies.

### Gold components

- **The Trio** — direct multiplicative Three-of-a-Kind payoff.
- **Zany Joker** — direct Mult.
- **Wily Joker** — direct Chips.
- **Cryptid / Death / Ouija-style rank concentration** once a target rank is established.
- **Half Joker** when the hand is consistently played as exactly three cards.

### Silver components

- Pair-condition Jokers that remain active on the chosen hand.
- Supernova / Card Sharp.
- Rank-specific Jokers matching the target rank.
- Hack/Fibonacci/Wee Joker when the chosen rank makes them naturally relevant.

### Bronze components

- Generic scoring/economy that does not require preserving broad rank diversity.

### Preferred deck manipulation

- Select one or two target ranks and copy/upgrade toward them.
- Destroy off-plan ranks.
- Avoid random rank changes once concentration is valuable.

### D1 play/discard profile

- Preserve all copies of the target rank unless survival requires otherwise.
- Discard aggressively away from isolated ranks when a clear Three-of-a-Kind line is feasible.
- Do not spend excessive discards chasing a third copy when Pair or High Card already provides a safe clear.

### Conflicts

- Straight builds requiring broad rank coverage.
- Full-spectrum suit/rank diversity packages.

### Natural pivots

- Full House if a second rank cluster develops.
- Four of a Kind / Five of a Kind as target-rank density increases.
- Flush Five if the dominant rank also becomes suit-concentrated.

### Mature signal

The target rank is sufficiently duplicated that Three of a Kind is routine, Venus/repetition scaling is meaningful, and the build owns a late multiplicative or scaling payoff.

---

## 5.5 Straight

**Strategic hand:** Straight  
**Planet:** Saturn  
**Identity:** Preserve rank connectivity and use consistency enablers to turn a fragile five-card hand into a repeatable high-scaling line.

### Gold components

- **Shortcut** — fundamentally changes Straight feasibility.
- **Four Fingers** — reduces the number of cards required for Straight construction.
- **Runner** — dedicated Straight scaling.
- **The Order** — direct multiplicative Straight payoff.

### Silver components

- Crazy Joker.
- Devious Joker.
- Superposition when Ace-containing Straights are realistic.
- Fibonacci when the deck naturally favors compatible low/mid ranks.
- Card Sharp / Supernova after Straight consistency is already established.

### Bronze components

- Generic scoring/economy.
- Temporary rank-specific value that does not require destroying Straight coverage.

### Preferred deck manipulation

- Preserve connected rank bands and valuable internal ranks.
- Remove excess duplicate or isolated edge ranks before removing central connectors.
- Strength/Death may repair gaps, but should not blindly collapse rank diversity.
- Avoid Ouija-style full rank conversion unless intentionally pivoting out of Straight.

### D1 play/discard profile

- Track rank outs, duplicate redundancy and open-ended/gapped Straight possibilities.
- Preserve central connectors over isolated high-card value when clear probability supports the search.
- Four Fingers/Shortcut must change discard evaluation, not merely final-hand scoring.

### Conflicts

- **Hard:** mature single-rank concentration.
- **Soft:** mono-suit conversion unless Straight Flush is a real transition.
- Heavy held-card shells that cannot spare the cards needed to assemble Straights.

### Natural pivots

- Straight Flush only when suit density and suit/straight enablers are already present.
- High Card/Pair if hand-size penalties or deck damage make Straight consistency collapse.

### Mature signal

A Straight can be assembled reliably within the available hand/discard budget, Saturn or Runner has meaningful scaling, and at least one direct Straight payoff/enabler makes the strategy safer than generic alternatives.

---

## 5.6 Flush

**Strategic hand:** Flush  
**Planet:** Jupiter  
**Identity:** Concentrate suit density and exploit suit-specific or Flush-specific payoffs while maintaining enough consistency to make five-card suit hands repeatedly.

### Gold components

- **Smeared Joker** — materially changes suit feasibility by pairing red and black suits.
- **The Tribe** — direct multiplicative Flush payoff.
- **Four Fingers** — major consistency enabler.
- **Bloodstone** in a Hearts-focused shell.
- **Arrowhead** in a Spades-focused shell.
- **Onyx Agate** in a Clubs-focused shell.
- **Rough Gem** in a Diamonds-focused shell when its economy contribution is strategically relevant.

### Silver components

- Droll Joker.
- Crafty Joker.
- Castle when discard routing can scale it without sacrificing survival.
- Ancient Joker when the current deck/suit flexibility can exploit its selected suit often enough.
- Seeing Double / Flower Pot only under deck states that actually satisfy their multi-suit conditions.

### Bronze components

- Generic Chips/Mult/economy.
- Temporary suit payoffs that do not justify changing the whole deck by themselves.

### Preferred deck manipulation

- Suit Tarot cards are high priority when they increase the dominant-suit share.
- Lovers/Wild, Death and targeted destruction can improve suit density.
- Sigil is a major structural enabler when the hand-size loss is survivable.
- Avoid splitting transformations across incompatible suit-specific Gold pieces unless Smeared Joker or another concrete bridge makes both useful.

### D1 play/discard profile

- Count dominant-suit outs explicitly.
- Preserve suit density even when individual off-suit cards have higher nominal rank value.
- With Four Fingers, evaluate four-card Flush clears directly rather than continuing to hunt a fifth suit card.

### Conflicts

- Multiple incompatible single-suit payoffs without Smeared Joker.
- Mature rank-concentration strategies unless transitioning to Flush House/Flush Five.
- Straight-specific deck shaping unless Straight Flush is already feasible.

### Natural pivots

- Straight Flush if rank connectivity becomes strong.
- Flush House if two/three rank clusters emerge inside the target suit structure.
- Flush Five if one rank becomes overwhelmingly dominant.

### Mature signal

The dominant effective suit count makes Flushes routine, Jupiter/Flush scaling is meaningful, and at least one strong suit/Flush payoff exists beyond generic Bronze stats.

---

## 5.7 Full House

**Strategic hand:** Full House  
**Planet:** Earth  
**Identity:** Maintain two concentrated rank groups so a three-plus-two structure is repeatable. It is a natural bridge between Two Pair/Three of a Kind and the advanced rank builds.

### Gold components

- **The Trio** — multiplicative payoff for the three-of-a-kind portion.
- **The Duo** — multiplicative payoff for the pair portion when the hand-condition model recognizes the contained Pair.
- **Spare Trousers** when Full House legally satisfies its contained Two Pair condition in the game model.
- Strong rank-copying tools that deliberately maintain **two** useful rank clusters rather than collapsing immediately to one.

### Silver components

- Zany Joker / Wily Joker.
- Mad Joker / Clever Joker when their contained-hand conditions are satisfied.
- Jolly Joker / Sly Joker.
- Supernova / Card Sharp after Full House frequency is proven.

### Bronze components

- Generic scoring/economy.
- Rank-specific payoffs matching either of the two primary ranks.

### Preferred deck manipulation

- Duplicate two chosen ranks.
- Thin unrelated ranks.
- Death/Cryptid should normally copy one of the established clusters.
- Do not overuse Ouija or single-rank conversion unless intentionally pivoting to Four/Five of a Kind.

### D1 play/discard profile

- Preserve pairs/triples and complementary rank groups.
- Evaluate whether a current Pair/Two Pair is a safe clear before spending all discards searching for the full five-card hand.

### Conflicts

- Half Joker and other <=3-card requirements.
- Severe hand-size penalties that make five-card assembly unreliable.
- Broad Straight rank diversity.

### Natural pivots

- Four/Five of a Kind if one rank dominates.
- Flush House if the rank clusters also become suit-concentrated.
- Two Pair/Three of a Kind if five-card reliability is insufficient.

### Mature signal

Two rank clusters are dense enough for repeatable Full Houses, Earth investment/direct hand-condition payoffs are meaningful, and hand-size/discard economy can support the five-card requirement.

---

# 6. Advanced transition playbooks

These should not normally become early-run primary targets from an untouched deck.

## 6.1 Four of a Kind

**Strategic hand:** Four of a Kind  
**Planet:** Mars

### Gold components

- **The Family** — direct multiplicative Four-of-a-Kind payoff.
- Strong single-rank cloning/conversion: Cryptid, Death, Ouija and equivalent persistent deck shaping.
- Rank-specific retrigger/scaling pieces when they match the chosen rank.

### Silver components

- The Trio / Three-of-a-Kind direct payoffs that remain useful inside Four of a Kind.
- Pair-condition payoffs that remain active.
- Square Joker when exactly four cards are the normal played hand.
- Supernova / Card Sharp once repetition is reliable.

### Bronze components

- Generic score/economy compatible with single-rank concentration.

### Deck objective

One dominant rank with enough copies that four can be drawn within the normal hand/discard budget.

### Conflicts

Straight rank coverage and any strategy requiring broad rank diversity.

### Natural pivots

Five of a Kind, or Flush Five if the dominant rank also becomes suit-concentrated.

### Mature signal

Four copies of the target rank are routinely accessible and the build has a direct high-end multiplier/scaler rather than relying solely on Mars levels.

---

## 6.2 Five of a Kind

**Strategic hand:** Five of a Kind  
**Planet:** Planet X

### Gold components

- **The Family** as a contained Four-of-a-Kind multiplier where applicable.
- Extreme rank-copying/conversion: Cryptid, Death, Ouija.
- Rank-specific retrigger/multiplier pieces matching the chosen rank.

### Silver components

- The Trio / Pair-condition payoffs that remain active.
- Supernova / Card Sharp once Five of a Kind is genuinely repeatable.

### Bronze components

- Generic score/economy.

### Deck objective

A heavily concentrated single-rank deck with enough copies to make five-card draws realistic.

### Conflicts

Straight, ordinary Two Pair and broad multi-rank deck plans.

### Natural pivots

Flush Five when one suit also becomes dominant.

### Mature signal

Five copies are routinely accessible without spending the entire discard budget, and the build has multiplicative scaling suitable for late blinds.

---

## 6.3 Straight Flush

**Strategic hand:** Straight Flush  
**Planet:** Neptune  
**Parent playbooks:** Straight + Flush

### Gold components

- Shortcut.
- Four Fingers.
- The Order.
- The Tribe.
- Seance when Straight Flush frequency is already high enough to generate Spectral value reliably.
- Smeared Joker when it materially increases valid suit connectivity.

### Silver components

- Runner.
- Crazy/Devious Joker.
- Droll/Crafty Joker.
- Superposition in an Ace-capable sequence.
- Suit-specific scoring matching the chosen effective suit.

### Bronze components

- Generic score/economy that does not damage either parent structure.

### Deck objective

A connected rank band concentrated into one effective suit group.

### Entry rule

Do not focus Straight Flush merely because one Neptune appears. Require an already-functional Straight or Flush parent plus concrete evidence that the second constraint is achievable.

### Conflicts

Single-rank concentration and transformations that destroy rank connectivity.

### Natural fallback

Return to whichever parent, Straight or Flush, remains more reliable.

### Mature signal

Straight Flushes are repeatable within normal resource budgets and both rank and suit structure are robust enough that a single bad draw does not collapse the run.

---

## 6.4 Flush House

**Strategic hand:** Flush House  
**Planet:** Ceres  
**Parent playbooks:** Full House + Flush

### Gold components

- The Tribe.
- The Trio / The Duo where their contained hand conditions apply.
- Smeared Joker or equivalent suit consistency enabler.
- Persistent transformations that copy the chosen two ranks while preserving the chosen effective suit.

### Silver components

- Droll/Crafty Joker.
- Pair/Two Pair/Three-of-a-Kind direct scoring that remains active.
- Suit-specific scoring matching the target suit.

### Bronze components

- Generic scoring/economy.

### Deck objective

Two dense rank clusters contained primarily inside one effective suit group.

### Entry rule

Require a mature Flush or Full House parent plus strong evidence for the missing dimension. Never chase Ceres from a normal deck solely because the Planet is available.

### Conflicts

Broad Straight structure, incompatible suit splitting and premature collapse to one rank.

### Natural fallback

Full House or Flush, whichever retains the stronger current consistency/payoff package.

### Mature signal

Both the 3+2 rank requirement and suit requirement are repeatedly satisfied with ordinary hand/discard resources.

---

## 6.5 Flush Five

**Strategic hand:** Flush Five  
**Planet:** Eris  
**Parent playbooks:** Five of a Kind + Flush

### Gold components

- The Tribe.
- The Family where its contained Four-of-a-Kind condition applies.
- Smeared Joker if it expands the effective suit set without damaging rank concentration.
- Cryptid/Death/Ouija plus suit conversion sufficient to reproduce one rank in one effective suit.
- Suit-specific scoring matching the chosen suit.

### Silver components

- The Trio / Pair-condition payoffs that remain active.
- Droll/Crafty Joker.
- Retrigger effects matching the chosen card identity.

### Bronze components

- Generic score/economy.

### Deck objective

Extreme concentration toward one rank and one effective suit/card identity.

### Entry rule

Only transition from an already-functional Five-of-a-Kind or very concentrated Flush shell. Do not reserve resources for Flush Five without persistent deck evidence.

### Conflicts

Nearly every broad rank/suit diversity strategy.

### Natural fallback

Five of a Kind or Flush depending on which structural axis remains stronger.

### Mature signal

Five same-rank, same-effective-suit cards are routinely accessible and the score engine scales multiplicatively enough for endgame targets.

---

# 7. Composable overlay playbooks

These overlays modify a primary poker-hand playbook. They should not automatically replace it.

## 7.1 Face Cards

### Gold examples

- Triboulet.
- Sock and Buskin.
- Photograph + retrigger support.
- Pareidolia only when making all cards face cards creates positive net value rather than disabling another engine.

### Silver examples

- Scary Face.
- Smiley Joker.
- Business Card when economy is useful.
- Reserved Parking.

### Main conflicts

- Ride the Bus / explicit No-Face strategies.
- Boss or deck conditions that make face dependence unsafe unless mitigated.

---

## 7.2 No Face Cards / low-rank shell

### Gold examples

- Ride the Bus.
- Hack when the deck is concentrated in 2-5.
- Wee Joker when 2 density is intentionally increased.
- Fibonacci when the deck naturally centers on its supported ranks.

### Silver examples

- Even Steven / Odd Todd when parity concentration supports them.
- Walkie Talkie when 10/4 concentration is deliberate.

### Main conflicts

- Pareidolia, Triboulet, Sock and Buskin, Photograph and other face-dependent engines.

---

## 7.3 Held Cards

### Gold examples

- Baron.
- Mime.
- Steel-card concentration.

### Silver examples

- Shoot the Moon.
- Raised Fist.
- Blackboard.
- Reserved Parking.

### Play rule

D1 must explicitly value cards remaining in hand; playing an otherwise unnecessary held-value card is a strategic cost.

---

## 7.4 Discard scaling

### Gold examples

- Burnt Joker.
- Castle.
- Yorick when discard volume is the intended long-run engine.

### Play rule

The agent may spend discards for persistent scaling only after accounting for the current blind clear path and the value of keeping emergency recovery resources.

### Main conflicts

- Green Joker.
- Banner / Delayed Gratification style rewards for retaining or avoiding discards.
- Burglar when discards are removed.

---

## 7.5 No-discard / hand-volume shell

### Gold examples

- Green Joker.
- Burglar.
- Ramen where preserving its multiplier favors avoiding discard expenditure.

### Silver examples

- Banner.
- Delayed Gratification.
- repeat-hand scaling that benefits from additional hands.

### Main conflicts

- Burnt Joker, Castle and other effects that require intentional discarding to scale.

---

## 7.6 Economy shell

### Gold examples

- Bull when banked money is converted into meaningful Chips.
- Bootstraps when banked money is converted into meaningful Mult.
- Rocket / To the Moon when the run can protect capital long enough to compound.

### Silver examples

- Golden Joker.
- Business Card.
- Reserved Parking.
- Rough Gem in Diamond-compatible scoring.

### Play rule

Economy is an amplifier, not a reason to lose the run. The resource valuator still protects current blind survival before interest or long-horizon scaling.

---

## 7.7 Consumable / Planet shell

### Gold examples

- Constellation for sustained Planet acquisition/use.
- Fortune Teller for sustained Tarot use.
- Perkeo when duplicated consumables create a concrete scoring/economy engine.

### Silver examples

- Hallucination and other pack/consumable generation when slots and economy can support it.
- Astronomer/Telescope-style Planet support when it advances the active primary hand.

### Play rule

Consumable generation is only valuable when the generated category has a plausible use path and inventory slots are not blocking higher-value tactical consumables.

---

# 8. Planet priority map

| Playbook | Primary Planet |
|---|---|
| High Card | Pluto |
| Pair | Mercury |
| Two Pair | Uranus |
| Three of a Kind | Venus |
| Straight | Saturn |
| Flush | Jupiter |
| Full House | Earth |
| Four of a Kind | Mars |
| Straight Flush | Neptune |
| Five of a Kind | Planet X |
| Flush House | Ceres |
| Flush Five | Eris |

Planet acquisition must still consider expected future hand frequency and marginal level gain. Merely matching the active playbook does not make a Planet an automatic buy/take.

---

# 9. Transformation priorities by archetype

This is a directional guide for D4-D10 later; exact card-level EV remains contextual.

| Transformation | Usually helps | Usually hurts / risks |
|---|---|---|
| Suit conversion | Flush, Straight Flush, Flush House, Flush Five | unrelated single-rank plans if it consumes better transformations |
| Rank copying | Pair, Two Pair, Trips, Full House, Four/Five, Flush House/Five | Straight rank diversity |
| Rank shifting | Straight repair, rank concentration when targeted | can destroy existing pairs/connectivity if used blindly |
| Card destruction | almost every focused deck when removing off-plan cards | can damage Straight/Full House redundancy if target choice is poor |
| Steel creation | High Card/Held Cards, low-card shells | opportunity cost when all cards must score in a five-card hand |
| Glass creation | boss/finisher scoring, concentrated repeated-rank hands | long-run fragility if the card is repeatedly required |
| Wild creation | Flush and hybrid suit hands | may be inferior to permanent suit concentration when a specific suit payoff matters |
| Cryptid-style copying | rank builds, exact-card builds, Flush Five | consumes slot/opportunity and can overconcentrate away from Straight |
| Ouija-style rank conversion | Trips/Four/Five and exact-rank transitions | Straight and multi-rank Full House structure; hand-size penalty |
| Sigil-style suit conversion | Flush-family builds | non-Flush plans; hand-size penalty |

---

# 10. Future implementation shape

The first code implementation should use explicit data structures rather than scattered `if joker == ...` logic across D1-D14.

A playbook record should eventually contain fields equivalent to:

```text
id
primary_hand
parent_playbooks
gold_components
silver_components
bronze_components
hard_conflicts
soft_conflicts
preferred_planet
preferred_transformations
deck_shape_requirements
hand_construction_rules
entry_signals
focus_signals
lock_signals
mature_signals
pivot_targets
overlays
```

The scorer should produce diagnostics such as:

```text
playbook = FLUSH
state = FOCUSED
evidence = [Smeared Joker, 18 effective Hearts, Jupiter level 3]
gold_hits = 1
silver_hits = 2
conflicts = []
next_needs = [multiplicative payoff, more suit concentration]
pivot_candidates = [STRAIGHT_FLUSH: weak]
```

Those diagnostics should then be shared by D1-D14 so hand play, Joker acquisition, consumables, Planets, packs, rerolls, blind skips and resource valuation are all reasoning from the same build definition.

---

# 11. Implementation order

1. Review/freeze this catalogue at the design level.
2. Encode playbook records and component memberships.
3. Add deck-shape evidence and conflict scoring.
4. Replace the current loose affinity-only build intent with playbook candidate/focus/lock state while preserving public-information constraints.
5. Feed the resolved playbook context into D1-D14.
6. Add deterministic playbook unit tests and anti-synergy regressions.
7. Only then resume live strategy tuning and the final Red Deck / White Stake acceptance run.

No acceptance result should be treated as the final v1.0 strategy baseline until this playbook layer is implemented.