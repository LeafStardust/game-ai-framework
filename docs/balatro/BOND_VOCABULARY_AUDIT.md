# Balatro Bond Vocabulary Audit

This document is the Phase A vocabulary audit for the Currency-Wars-style Bond architecture defined in `ROADMAP.md`.

A Bond is a **run-level strategic axis**. Components and mechanics contribute to Bonds; Bonds are not command systems and should not normally be named after a single component.

## Validity tests

A retained Bond must satisfy all four tests:

1. **Real strategic axis** — the run can meaningfully build around it.
2. **Multi-component development** — multiple components, persistent state features, or mechanical operations can strengthen it.
3. **Future-choice effect** — developing it changes the strategic value of compatible future choices.
4. **Distinctness** — it is not merely a duplicate measurement of another Bond.

Classification values are `KEEP`, `MERGE`, `RENAME`, `DEMOTE TO MECHANIC`, and `REMOVE`.

## Audit result

The current registry contains 46 Bonds. The audit retains the strategic coverage but renames three entries whose current names describe a component or an overly narrow implementation rather than the underlying strategic axis.

| Current Bond | Decision | Canonical Bond after audit | Rationale |
|---|---|---|---|
| `burnt` | **RENAME** | `hand_leveling` | Burnt Joker is a contributor/mechanic, not the strategic axis. The build direction is persistent hand-level development through Burnt, Planets, Space Joker, Blue Seals, Telescope, copying, and other hand-level infrastructure. This Bond should compose with the selected hand-specialization Bond rather than represent one Joker. |
| `held_cards` | **KEEP** | `held_cards` | Broad held-state strategy supported by Baron, Shoot the Moon, Blackboard, Steel, hand size, and other held-card payoffs/infrastructure. |
| `held_retrigger` | **KEEP** | `held_retrigger` | Distinct retrigger axis for effects triggered while cards remain in hand; composes strongly with held-card and Steel strategies. |
| `steel` | **KEEP** | `steel` | Persistent deck-shaping axis with multiple creation, density, scoring, and retrigger interactions. |
| `pair` | **KEEP** | `pair` | Distinct hand specialization; Joker support, Planet investment, deck shaping, and play consistency alter future value. |
| `high_card` | **KEEP** | `high_card` | Distinct low-complexity hand specialization with dedicated payoff and permanent hand-level investment. |
| `aces` | **KEEP** | `aces` | Rank-density strategy with multiple payoff, duplication, enhancement, and deck-shaping paths. |
| `no_discard` | **KEEP** | `no_discard` | Distinct execution/resource strategy around preserving discard-free scalers/payoffs and valuing hands/resources differently. |
| `cash` | **KEEP** | `cash` | Money-retention/generation/scaling is a genuine run-level economy/scoring axis supported by many components; distinct from Gold-card infrastructure. |
| `lucky` | **KEEP** | `lucky` | Enhancement-density/payoff axis with creation, probability manipulation, retriggers, and Lucky-specific scaling. |
| `glass` | **KEEP** | `glass` | Enhancement-density/payoff axis with creation, destruction, retrigger, and Glass Joker interactions. |
| `face_cards` | **KEEP** | `face_cards` | Broad J/Q/K density/payoff axis; distinct from individual rank specializations and directly conflicts with face-free strategies. |
| `two_pair` | **KEEP** | `two_pair` | Distinct hand specialization with dedicated scalers/payoffs, Planet investment, and deck-shaping consequences. |
| `three_kind` | **KEEP** | `three_kind` | Distinct rank-concentration hand specialization. |
| `four_kind` | **KEEP** | `four_kind` | Distinct deeper rank-concentration hand specialization with materially different deck-shaping requirements. |
| `straight` | **KEEP** | `straight` | Distinct rank-distribution strategy with substantial support mechanics such as Shortcut/Four Fingers and dedicated payoffs. |
| `flush` | **KEEP** | `flush` | Distinct suit-concentration strategy with suit conversion, Wild cards, dedicated payoffs, and Planet investment. |
| `played_retrigger` | **KEEP** | `played_retrigger` | Generic played-card retrigger axis spanning Red Seals and multiple Jokers; composes with rank/suit/enhancement strategies. |
| `stone` | **KEEP** | `stone` | Distinct enhancement/deck-composition axis with creation and density payoffs, materially different from ordinary rank/suit strategies. |
| `gold_economy` | **RENAME** | `gold_cards` | The strategic axis is building/holding Gold cards and exploiting their economy/held-card interactions. `gold_economy` incorrectly conflates the card mechanic with the broader `cash` Bond. |
| `deck_thinning` | **KEEP** | `deck_thinning` | Persistent deck-composition axis: reduced deck size/concentration changes draw quality and increases future removal value. |
| `deck_growth` | **KEEP** | `deck_growth` | Persistent deck-growth axis supported by DNA, Certificate, Marble Joker, Hologram, card creation, and quality-of-addition choices. |
| `full_house` | **KEEP** | `full_house` | Distinct mixed rank-structure hand specialization; not reducible to Pair plus Trips because its construction and Planet payoff are specific. |
| `straight_flush` | **KEEP** | `straight_flush` | Distinct advanced hand specialization requiring joint rank/suit consistency and receiving unique Planet/scoring payoff. |
| `five_kind` | **KEEP** | `five_kind` | Distinct extreme rank-concentration strategy enabled by duplication/deck shaping and unique hand-level payoff. |
| `flush_house` | **KEEP** | `flush_house` | Distinct secret-hand specialization requiring simultaneous suit and pair/trips structure. |
| `flush_five` | **KEEP** | `flush_five` | Distinct secret-hand specialization requiring same-rank/same-suit concentration; materially different construction from Five of a Kind alone. |
| `hearts` | **KEEP** | `hearts` | Suit-specific axis with dedicated payoff Jokers and suit-density shaping. |
| `spades` | **KEEP** | `spades` | Suit-specific axis with dedicated payoff Jokers and suit-density shaping. |
| `clubs` | **KEEP** | `clubs` | Suit-specific axis with dedicated payoff Jokers and suit-density shaping. |
| `diamonds` | **KEEP** | `diamonds` | Suit-specific axis with dedicated payoff Jokers and suit-density shaping. |
| `low_ranks` | **KEEP** | `low_ranks` | Multi-rank 2–5 strategy supported by Hack, Wee Joker, Fibonacci and other rank-specific effects; broader than any single-rank mechanic. |
| `kings` | **KEEP** | `kings` | King-density/held-scoring axis with Baron, Triboulet, Steel/Mime, duplication, and deck-shaping interactions. |
| `queens` | **KEEP** | `queens` | Queen-density/held-scoring axis with Shoot the Moon, Triboulet, duplication, and deck shaping. |
| `jacks` | **KEEP** | `jacks` | Jack-density/discard-payoff axis, especially Hit the Road; deck transformations and duplication can deliberately deepen it even though the current evaluator is too Joker-centric. |
| `tarot` | **KEEP** | `tarot` | Consumable-generation/use infrastructure is a genuine engine axis with multiple generators, vouchers, Fortune Teller/Vagabond-style payoffs, and deck-shaping feedback. |
| `planet` | **KEEP** | `planet` | Planet-generation/use infrastructure is a genuine hand-development/scaling axis that composes with hand specialization and `hand_leveling`. |
| `discard` | **KEEP** | `discard` | Generic discard-resource/payoff axis spanning multiple Jokers and tactical/resource consequences. Burnt is one contributor, not the Bond identity. |
| `blind_skip` | **KEEP** | `blind_skip` | Skipping can become a deliberate run-level strategy through Throwback, tags and skip history; future tag/shop tradeoffs change once developed. |
| `sell_value` | **KEEP** | `sell_value` | Sell-value accumulation/conversion is a real engine axis through Swashbuckler, Egg, Gift Card and slot/economy management. |
| `joker_sacrifice` | **KEEP** | `joker_sacrifice` | Deliberate Joker destruction/fodder management is a distinct strategy through Dagger, Madness, Riff-Raff and related slot-generation choices. |
| `card_destruction` | **KEEP** | `card_destruction` | Destruction is an active mechanic/payoff axis, while `deck_thinning` describes resulting deck structure. They should remain separate and synergize. |
| `hand_repetition` | **KEEP** | `hand_repetition` | Repeated-hand payoff/consistency is a distinct strategic axis through Card Sharp, Supernova and repeatable-hand construction. |
| `enhanced_cards` | **KEEP** | `enhanced_cards` | Generic enhanced-card density is a broad axis useful to Driver's License and other enhancement-sensitive mechanics. It must no longer be hard-locked to one Joker; realization should express whether density has a current payoff. |
| `no_face_cards` | **KEEP** | `no_face_cards` | Face-free deck/play construction is a distinct strategic axis around Ride the Bus and future face-card removal/avoidance choices. It should not conceptually require the payoff Joker merely to exist as evidence. |
| `vampire` | **RENAME** | `enhancement_consumption` | Vampire is the payoff component. The actual strategy is generating enhanced-card feedstock and consuming/stripping enhancements for scaling. Naming the Bond after the Joker confuses component with strategic axis. |

## Frozen canonical vocabulary after Phase A

The cleaned vocabulary remains 46 strategic axes:

```text
hand_leveling
held_cards
held_retrigger
steel
pair
high_card
aces
no_discard
cash
lucky
glass
face_cards
two_pair
three_kind
four_kind
straight
flush
played_retrigger
stone
gold_cards
deck_thinning
deck_growth
full_house
straight_flush
five_kind
flush_house
flush_five
hearts
spades
clubs
diamonds
low_ranks
kings
queens
jacks
tarot
planet
discard
blind_skip
sell_value
joker_sacrifice
card_destruction
hand_repetition
enhanced_cards
no_face_cards
enhancement_consumption
```

## Important implementation corrections discovered by the audit

The vocabulary audit also exposes several legacy-model assumptions that must **not** survive migration:

1. **No Bond should be hard-locked merely because its current defining payoff Joker is absent.**
   - Example: enhanced-card density can exist before Driver's License.
   - Example: face-free deck structure can exist before Ride the Bus.
   - Example: sell-value infrastructure can exist before Swashbuckler.
   - `realization` and resulting `BuildValue` should determine how strategically useful that structure currently is.

2. **Component names must move down into mechanical descriptors/contributions.**
   - Burnt Joker contributes strongly to `hand_leveling` and `discard`.
   - Vampire contributes strongly to `enhancement_consumption`.
   - Midas Mask, enhancement creation and current feedstock can also contribute to `enhancement_consumption`.

3. **Current rank-policy tables are legacy strategy-command artifacts.**
   Their mechanic knowledge may be useful during migration, but policy strings such as `capstone_*_commitment`, `actively_shape_*`, and `protect_*` are not part of the final Bond authority model.

4. **Current evaluators are useful evidence maps, not final scoring implementations.**
   Their Joker/card/state mappings should be mined into the canonical mechanical-descriptor → contribution system rather than retained as 46 independent policy modules indefinitely.

5. **Relationships remain sparse.**
   `card_destruction` and `deck_thinning`, for example, remain distinct Bonds because one represents an active destruction engine and the other resulting deck concentration; their overlap belongs in relationship value, not a merge.

## Migration aliases

During migration only, old IDs may resolve to the cleaned IDs so production consumers can be moved safely:

```text
burnt        -> hand_leveling
gold_economy -> gold_cards
vampire      -> enhancement_consumption
```

These aliases are temporary compatibility aids. They must be deleted at the Bond migration cleanup gate once all canonical consumers/tests/docs use the cleaned IDs.

## Phase A conclusion

No Bond is removed or merged in this audit. That is intentional rather than conservative: after applying the four validity tests, each retained axis changes future candidate value in a distinct way. The three renames correct category errors where the existing identifier describes a component or narrower implementation instead of the strategy itself.

Phase A vocabulary is therefore frozen at **46 Bonds with 43 IDs retained and 3 renamed**. The next work is dependency inspection and controlled migration of those three IDs, followed by Phase B mechanical semantic coverage.