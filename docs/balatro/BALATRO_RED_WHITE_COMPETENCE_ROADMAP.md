# Balatro Red/White Competence Roadmap

Status: **Active v1.0.x semantic/runtime repair gate**

This document is the handoff contract for Red Deck / White Stake competence work. It exists so future contributors do not have to reconstruct the intended Balatro play philosophy from live-run postmortems.

## Primary objective

The permanent Balatro agent has one gameplay objective:

> **Maximize the probability of winning the run.**

Collection-first / unlock-chasing behavior is retired from the ordinary competence path. Profile discovery state may remain as bounded metadata or exact-tie information, but it must never justify a strategically worse action, sacrifice blind-clear probability, or override win-oriented decisions.

## Early-game doctrine

Ante 1–2 is a survival phase, not a strategy-free phase.

The agent should acquire only enough immediate chips and/or Mult to clear early blinds with safe margin, while **already** recognizing and developing coherent Bonds/strategies from the first relevant pieces. It must not postpone strategy formation until Ante 3 or later.

Early temporary scoring is valid when needed for survival, but it is not the end goal. The agent should continually compare temporary power against emerging long-term engines, scaling routes, economy, and replacement opportunity.

## Literal score authority

Scoring must be evaluated as Balatro actually scores it.

The score model must use the exact modeled mechanics that apply to the current state, including hand base chips/Mult, played-card chips, enhancements, editions, seals, Joker ordering, additive Mult, XMult, retriggers, held effects, hand levels, boss modifiers, and stateful Joker conditions.

Bond rank, strategy commitment, motif strength, composition coherence, or synthetic category coverage must **never** be converted into fake chips/Mult or otherwise treated as literal score.

A defect exists whenever a decision layer substitutes an abstract label such as “has chips” / “has Mult” for the actual marginal score contribution of the current build.

## Strategy and Bond authority

The canonical Bond/composition architecture applies from the beginning of the run:

- positive R0 evidence is strategically visible;
- candidate strategies may be EXPLORATORY or FORMING before a Bond is highly ranked;
- meaningful mechanical relationships may PIN a strategy before a motif is ACTIVE;
- pinned strategies receive bounded construction, preservation, and execution authority;
- strategy commitment remains reversible when a materially stronger projected line exists;
- isolated new Bond labels must not be collected merely because they add composition score;
- once a useful engine exists, deepening or coherently extending it should generally outrank unrelated structural diversification.

Recognition without execution is a defect. Examples include Card Sharp without repeated-hand preference, Green Joker / no-discard engines that still discard casually, or a realized held-card engine whose required cards are played away unnecessarily.

## Joker valuation

Jokers must be valued from their exact current and prospective mechanics, not broad categories.

Examples of required context-sensitive reasoning:

- **Joker Stencil:** empty Joker slots are part of its scoring value; an empty or sparse roster can make it immediately powerful.
- **Card Sharp:** value depends on whether repeatable hand types are realistically available and D1 actually repeats them.
- **Ride the Bus:** face-card play resets it; face-heavy engines such as Scary Face can be mechanically contradictory.
- **Bull / Bootstraps:** current cash directly affects scoring value; selling either with triple-digit cash is presumptively wrong unless a clearly superior replacement justifies the loss.
- **Banner:** remaining discards affect chips, but this must not blindly suppress defining discard engines such as Burnt Joker.
- **Green Joker:** discards have a direct strategic cost because they reduce its scaling.
- **Blueprint / Brainstorm:** value depends on actual copy target and order, not a static universal score.

Known stable interactions and anti-interactions require explicit regressions when generic semantics are insufficient.

## Shop decision doctrine

Every visible shop action competes on expected contribution to winning the run.

The comparison must account for:

- immediate survival margin;
- actual marginal score from the current build;
- scaling runway;
- strategy formation / completion;
- economy and interest;
- Joker and consumable slot opportunity cost;
- replacement quality;
- boss vulnerability;
- pack option value;
- reroll opportunity and stop-loss;
- current and prospective conditional mechanics.

A strong visible Joker must not lose to a weak voucher, reroll, or speculative pack merely because unrelated local utilities use larger synthetic numbers.

Examples of unacceptable behavior from the 2026-08-25 live batch:

- ending the first shop with zero Jokers while **Joker Stencil** is affordable and strong in the current empty-slot state;
- buying **Clearance Sale** plus a Buffoon Pack while passing **Card Sharp** in a weak build;
- buying **Wasteful** while a clearly useful scoring Joker such as **Blue Joker** is available without a compelling strategic reason;
- repeatedly ending shops while strong visible upgrades remain.

## Replacement doctrine

Replacement must compare the incumbent’s **actual current contribution plus prospective strategic value** against the candidate’s projected contribution.

The agent must avoid both extremes:

- protecting mediocre filler indefinitely because it happens to belong to a Bond;
- destroying a realized or strongly scaling engine for a superficially attractive local upgrade.

Mechanically important state must be preserved. Selling Bull or Bootstraps with very high cash, breaking an ACTIVE/MATURE engine, or sacrificing a committed strategy component requires a materially better projected run outcome.

## Economy doctrine

Money is both a purchase resource and, for some builds, a scoring resource.

The agent must decide reserve, interest, rerolls, vouchers, and spending from the actual run state. No fixed cash rule is globally correct.

Economy is valuable when it improves future survival and scaling, but it is subordinate to immediate survival when the build is weak. Conversely, a healthy build should not burn cash on marginal speculative value merely because funds are available.

Bull/Bootstraps and similar conditional mechanics make cash opportunity cost part of score projection, not just shop economics.

## Packs and consumables

Pack and consumable decisions must use expected win value and exact mechanics.

The agent should not skip a pack when there is effectively no meaningful downside and positive expected value, but it also should not buy packs blindly when the money, slot, strategy, or visible-shop opportunity cost is greater.

Wheel of Fortune should be bought/used when its public-state stochastic value is positive and the purchase does not materially reduce win probability. Pack Wheel and shop Wheel should follow the same mechanical expectation model where appropriate.

Tarot/Planet/Spectral use must respect the actual current strategy, target cards, held-value cards, and future opportunity rather than generic category preference.

## Hand-play doctrine

D1 must maximize blind-clear probability using exact modeled score and legal boss mechanics, then use survival-equivalent alternatives to preserve economy and strategic resources.

Required behavior includes:

- preserve Steel/Gold/Blue-Seal held value when survival-equivalent;
- order first-card effects correctly;
- execute Card Sharp / hand-repetition strategy when viable;
- avoid discards that damage no-discard engines when a viable play exists;
- exploit Burnt Joker first-discard value when safe;
- intentionally cycle non-scoring cards when doing so improves future hands without sacrificing needed held effects;
- obey all boss-specific legality and score modifiers.

## Discard doctrine

A discard token costs one discard regardless of whether one or several cards are redrawn.

Repeated singleton discards are therefore exceptional, not normal. A one-card discard is justified only when preserving the other held structure is materially better than cycling additional cards.

The agent must evaluate:

- retained made-hand / draw structure;
- number and quality of dead cards;
- expected improvement from redrawing multiple cards;
- remaining discard count;
- held-card value;
- discard-triggering / no-discard Joker mechanics;
- boss-specific effects;
- current required scoring pace.

The 2026-08-25 three-run batch demonstrated a release-blocking defect: the agent repeatedly spent four or five discard tokens as singletons. Fix this at the actual planner/controller layer that selects live actions, not by adding a bonus to an evaluator that the authoritative decision path can bypass.

## Boss doctrine

Boss rules are authoritative mechanics, not soft preferences. Normal strategy may be overridden when the boss changes legality, card effectiveness, hand constraints, forced selection, sale requirements, or score projection.

Boss-specific behavior should be implemented as exact mechanical constraints or exact score transformations wherever possible, rather than arbitrary bonuses/penalties.

## “Stupid behavior” classification

Treat clearly dominated or mechanically contradictory decisions as semantic/runtime defects before considering numerical tuning.

Examples include:

- Ride the Bus paired/executed through frequent face-card play that resets it;
- selling Bull or Bootstraps while very high cash makes them major scoring engines;
- skipping a positive-value pack when there is no meaningful opportunity cost;
- passing a strong context-sensitive Joker such as Stencil or Card Sharp for weaker utility;
- collecting unrelated Bonds instead of strengthening a functioning engine;
- repeatedly rerolling while a strong visible option already exists;
- playing held-value cards such as Steel unnecessarily;
- destroying an ACTIVE/MATURE engine without a materially superior projected replacement;
- repeated singleton discards when several dead cards can safely be cycled.

## Repair progress — 2026-08-26

The deterministic Balatro suite is green at the latest validated checkpoint.

Completed or validated in the current semantic/runtime pass:

- synthetic chip/Mult/XMult coverage overrides were removed from the Red/White correction layer; literal modeled scoring remains the score authority;
- stateful/contextual scoring paths used by shop valuation were repaired and covered by regressions, including repeated-hand activation for Card Sharp and current-state contribution/replacement behavior;
- D1 discard ranking was moved back under the canonical D1 evaluator/planner path instead of a competing mini-heuristic, with multi-card redraw behavior covered by deterministic tests;
- **The Psychic** now scores legal 1–4 card burn/cycling plays as zero while preserving normal scoring for valid five-card plays;
- **Purple Seal** discard value now survives planner search: a mechanically distinct Purple-Seal branch is preserved when a Tarot can actually be generated, and generated consumables are carried only as a late survival-equivalent expectimax tie-break;
- shop Wheel remains admitted through the public-state stochastic edition model rather than being deterministically rejected;
- **The Soul** no longer receives a fixed `8 + early-Ante bonus` pack score; pack selection now uses a uniform expectation over the five modeled Legendary Joker outcomes evaluated against the current build through B3;
- **The Serpent** planner transition now forces exactly three public draw cards after either Play or Discard, with Chicot restoring ordinary draw counts;
- **The Hook** uses exact random two-card forced-discard branching and canonical discard-trigger projection, and D1 now preserves each branch-specific post-Hook hand rather than rebuilding children from a common retained hand;
- **The Tooth** and **The Ox** apply their cash effects before Joker scoring so Bull/Bootstraps read the correct post-boss cash; regressions cover Tooth per-card cash loss, Ox target-hand reset, and Chicot bypass;
- **Cerulean Bell** root and recursive Play/Discard actions obey the currently observed forced-selection constraint;
- **Cerulean Bell** deeper D1 projections now branch uniformly over every possible next forced-selected card after hypothetical redraws, so recursive child legality is modeled rather than marked incomplete; Chicot bypasses the Bell brancher;
- **Cerulean Bell** live process-memory hydration now carries public `card.ability.forced_selection` through the normalized snapshot and translator into `BalatroCard.forced_selection`, so the validated D1 legality logic is active in production observations rather than only synthetic states;
- the full `tests/balatro` suite is green through the complete Cerulean Bell current-hand, future-forced-selection, and live-state hydration checkpoint on 2026-08-26.

Still open before a new live baseline:

- complete the remaining pack/consumable opportunity-cost and target-selection audit beyond Wheel/Soul and the already modeled deterministic target paths;
- complete the remaining boss-mechanics audit beyond Psychic, Serpent, Hook, Tooth, Ox, and Cerulean Bell;
- finish the semantic D1 audit for held-value cards, discard-trigger engines, and boss interactions;
- diagnose/fix the post-`run_finished` three-attempt supervisor/shutdown crash;
- rerun the full Balatro suite after the remaining changes, then perform a fresh production-default three-run Red/White batch.

## Current repair queue

Do not start another live calibration baseline until these semantic/runtime issues are addressed:

- [ ] Ensure literal score projection is authoritative for current and candidate builds; remove synthetic category substitutes.
- [ ] Audit contextual Joker valuation, beginning with Stencil, Card Sharp, Ride the Bus, Bull, Bootstraps, Banner, Green Joker, Blueprint, and Brainstorm.
- [ ] Verify strategy formation and R0 evidence influence acquisition from Ante 1 without overpowering survival.
- [ ] Repair shop cross-family arbitration so visible Joker strength, vouchers, packs, consumables, rerolls, and economy compare on a run-winning basis rather than incompatible local units.
- [ ] Repair Joker replacement using actual incumbent/candidate score, scaling, economy, realization, and strategy disruption.
- [ ] Repair D1 discard selection at the authoritative planner/controller layer so multi-card redraws are considered correctly and strategy-specific discard mechanics execute.
- [ ] Audit pack/consumable skipping for positive-EV opportunities and harmful opportunity-cost mistakes.
- [ ] Audit boss-specific execution against exact mechanics.
- [ ] Diagnose and fix the three-attempt supervisor/shutdown crash observed after all three run logs had already emitted `run_finished`.
- [ ] Add direct regressions for every live defect above before a new authoritative batch.
- [x] Run `tests/balatro` and require green before live validation. Latest validated deterministic checkpoint: green on 2026-08-26 through complete Cerulean Bell D1 legality/future-forced-selection/live-hydration handling.
- [ ] Only after semantic/runtime defects are clean, run a fresh three-run Red/White production-default baseline.
- [ ] Keep Optuna numerical tuning frozen until the clean baseline contains no obvious semantic/runtime contradiction.

## Calibration and promotion gate

Three live runs are sufficient for rapid defect discovery, not for proving a candidate is better. Any semantic/runtime fix invalidates the current calibration baseline because the repository SHA changed.

After a clean unchanged-HEAD baseline exists, numerical tuning may resume under the existing Bond tuning contract. Promotion still requires the documented fresh holdout/comparator gate rather than a lucky three-run result.
