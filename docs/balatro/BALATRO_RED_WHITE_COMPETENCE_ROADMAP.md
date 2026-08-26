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

The deterministic Balatro suite is green at the latest validated checkpoint. Changes after that checkpoint remain pending the user's next local suite run; do not interpret the list below as a claim that current HEAD has been tested.

Completed or implementation-audited in the current semantic/runtime pass:

- literal current/candidate score authority is implementation-complete: D2 representative probes include played-card chips, exact hand levels and the three secret hands, legal Blueprint/Brainstorm ordering, stateful conditional contexts such as Card Sharp, post-transaction cash for Bull/Bootstraps, next-round discard allowance for Banner, and analytic public-mechanics expectation for stochastic score sources such as Bloodstone/Misprint; the final category-only early-Joker force-buy was removed so semantic labels cannot manufacture score or admission;
- the shared literal scorer and D2 representative probe catalogue include **Five of a Kind, Flush House, and Flush Five** with their exact base scores, so secret-hand runs no longer lose those hand types during shop current/candidate valuation;
- the named contextual-Joker valuation audit is complete for **Joker Stencil, Card Sharp, Ride the Bus, Bull, Bootstraps, Banner, Green Joker, Blueprint, and Brainstorm**;
- Joker replacement implementation compares a common literal incumbent/candidate baseline, post-transaction cash, economy, edition/slot effects, realized-engine retention, FORMING/PINNED strategy disruption, Negative retention, and exact selected shop-copy identity;
- D14 replacement cash-scaling cost excludes the sold incumbent, preventing Bull/Bootstraps from being charged as though they still existed after replacement;
- D3 voucher admission is authoritative inside D14 instead of being bypassed by the generic shop layer, with parent money/interest/reserve costs normalized on the shared resource scale;
- D11 future-shop Joker value comes from the current public eligible Joker pools through D2/D14, including replacement admission and public edition odds; only unseen future price remains an explicit prior;
- D11 future-shop Planet value averages the currently eligible Planet pool through D4/D14; future Tarot value fails closed instead of using the old synthetic `3.2` gross-utility prior until a real held-Tarot option model exists;
- D8 Buffoon value uses a conservative public eligible-Joker D2/D14 expectation instead of fixed hit/value priors, supports full-roster replacement, and scores prospective Joker outcomes at post-pack-spend cash;
- D8 Celestial acquisition enumerates the current eligible Planet pool, respects held duplicates/Showman, computes best-visible one/two-selection expectation without reading hidden contents, values permanent Planet sequences through literal direct scoring, includes Constellation progression and secret hands, and retains Bull/Bootstraps cash-scaling spend cost;
- D8 Standard acquisition uses Balatro's exact public generator distribution: 60% Base / 40% Enhanced, uniform 52-card fronts, uniform eight-card Enhanced pool conditional on enhancement, 20% uniformly distributed Seals, and the exact public `edition_rate` Foil/Holographic/Polychrome distribution. The current build profile is cached once and D9 visible-card mechanics provide a conservative one-offer lower bound rather than fixed family priors;
- Standard selected-card deck growth no longer receives a fixed `+1.0` Blue Joker/Hologram bonus. Vanilla-card dilution remains a separate deck-quality cost, while Blue Joker's exact `+2 Chips/card` and Hologram's exact `+0.25 XMult/card` progression are valued by literal before/after build projection in both D8 and D9;
- D8 Arcana acquisition uses the current public eligible Tarot/Spectral generation pools instead of fixed family priors. It mirrors `get_current_pool` culling, held-duplicate/Showman rules, challenge bans, pool flags, empty-pool fallbacks, the exact Omen Globe 80% Tarot / 20% Spectral branch, and the exact 0.3% soulable special override. Unresolved outcomes contribute the true opened-pack Skip=0 baseline and best-of-3/5/Mega upside is omitted conservatively;
- D8 Spectral acquisition likewise uses the current public eligible Spectral pool plus the exact 0.3% soulable special override, with Black Hole final precedence when eligible and Soul otherwise. Unresolved outcomes contribute Skip=0 and best-of-2/4/Mega upside is omitted conservatively;
- all five unopened booster families—**Buffoon, Celestial, Standard, Arcana, and Spectral**—therefore have public-mechanics D8 expectation authority rather than the original fixed family hit/value priors;
- Hanged Man is no longer hard-vetoed merely because Blue Joker is owned. B6 subtracts Blue Joker's exact `2 Chips/card` deck-size coefficient on the existing chip-normalized intrinsic scale, so weak-card thinning may still be selected only when the net target remains positive;
- D1 discard ranking is under the canonical D1 evaluator/planner path instead of a competing mini-heuristic;
- opened-pack Skip uses the true sunk-cost baseline in the Red/White production cartridge;
- **The High Priestess** uses a public-state eligible-Planet expectation with duplicate/Showman rules;
- **Wraith** uses the current public eligible Rare-Joker pool, public edition odds, whole-build Joker valuation, and the full cash-to-zero resource cost; injected completion requires one new Rare Joker and `$0` money;
- **Judgement** uses current public Common/Uncommon/Rare Joker pools with the real 70/25/5 rarity mixture and public edition odds; newly generated To Do List branches are averaged over visible poker-hand targets and injected completion requires one new Joker;
- **The Emperor** uses the current public eligible Tarot pool, exact free-slot generation count and without-replacement generation unless Showman; generated outcomes are valued through the ordinary D9 Tarot authority with a conservative better-generated-card lower bound;
- **Ouija** uses exact uniform expectation over all 13 rank rewrites minus a shared literal permanent hand-size opportunity cost; injected completion verifies the common-rank rewrite and exact `hand.limit - 1` transition;
- **Ectoplasm** uses the public escalating `ecto_minus`, a shared permanent hand-size opportunity model, and the marginal D11 public future-Joker value of one additional Joker slot instead of a fixed Negative-edition bonus; injected completion verifies exactly one editionless Joker becomes Negative, hand limit falls by the pre-use penalty, and `ecto_minus` increments;
- the shared permanent hand-size opportunity model compares expected best literal future-hand score at `H` versus `H-N` from unordered public permanent-deck composition, uses D1's deterministic public draw model, and explicitly removes transient current-blind/current-round/shop state from that future valuation;
- **Cryptid**, **Familiar**, **Grim**, **Incantation**, and **Immolate** have explicit production outcome/target models and semantic execution verification rather than generic deferred handling;
- **Wheel of Fortune** shop and pack paths share analytic public-state expectation rather than synthetic option floors;
- **The Soul** uses expectation over the five modeled Legendary outcomes instead of a fixed early-Ante bonus;
- deterministic targeted Tarot/Spectral execution preserves live-card identity, rejects no-op transformations, and verifies resulting mutations;
- **Black Hole** completion requires every modeled poker-hand level to increase by exactly one;
- **The Serpent**, **The Hook**, **The Tooth**, **The Ox**, **The Psychic**, **Cerulean Bell**, and the other Red/White bosses are accounted for by exact D1/live-state mechanics; the full static production inventory is documented in `BALATRO_BOSS_MECHANICS_AUDIT.md`;
- held-resource D1 semantics keep Steel inside literal scoring and use Blue Seal/Gold preservation only when mechanically appropriate;
- Ceremonial Dagger, Blueprint/Brainstorm exact-play ordering, first-card-sensitive ordering, and dominated Gold/Blue-Seal/Steel overplay are represented in the production path;
- the first-party injected bridge tolerates transient Windows access races;
- the bounded three-attempt supervisor stops after attempt 3 without invoking a fourth restart.

Implemented after the latest validated deterministic checkpoint and awaiting the user's next local suite run include, among others:

- Verdant Leaf and Crimson Heart newest regression cases;
- literal consumable-target value corrections;
- Wraith/Judgement and generated-Spectral expectation/execution work;
- Emperor, Ouija, Ectoplasm, shared future hand-size opportunity valuation, and their semantic execution guards;
- post-transaction Joker valuation, Banner reset-resource valuation, R0/FORMING transition influence, D11 public-pool reroll EV, all five D8 public-mechanics booster expectations, secret-hand shop scoring, D2 played-card-chip/stochastic expectation, Hanged Man/Blue Joker opportunity cost, literal Standard deck-growth value, consumable-generation public-pool observation, and subsequent pack corrections.

Still open before a new live baseline:

- validate the completed pack/consumable semantic audit on the user's local deterministic suite; there are no remaining known explicit Emperor/Ouija/Ectoplasm implementation blockers in this audit;
- finish D14 cross-family arbitration; replacement, vouchers, D11 Joker/Planet, and all five D8 booster families are implementation-repaired, while held-Tarot/future-consumable units remain unresolved;
- verify the installed early FORMING/R0 authority under the user's local regression/live validation rather than claiming verification from static inspection;
- finish any remaining D1 discard-trigger/hand-play contradiction audit after the current batch validates;
- rerun the full Balatro suite after the remaining changes, then perform a fresh production-default three-run Red/White batch.

## Current repair queue

Do not start another live calibration baseline until these semantic/runtime issues are addressed:

- [x] Ensure literal score projection is authoritative for current and candidate builds; remove synthetic category substitutes. Implementation audit complete; current-HEAD local regression validation remains pending.
- [x] Audit contextual Joker valuation, beginning with Stencil, Card Sharp, Ride the Bus, Bull, Bootstraps, Banner, Green Joker, Blueprint, and Brainstorm.
- [ ] Verify strategy formation and R0 evidence influence acquisition from Ante 1 without overpowering survival. Implementation is installed; local validation remains pending.
- [ ] Repair shop cross-family arbitration so visible Joker strength, vouchers, packs, consumables, rerolls, and economy compare on a run-winning basis rather than incompatible local units.
- [x] Repair Joker replacement using actual incumbent/candidate score, scaling, economy, realization, and strategy disruption. Implementation audit complete; local regression validation remains part of the suite gate below.
- [x] Repair D1 discard selection at the authoritative planner/controller layer so multi-card redraws are considered correctly and strategy-specific discard mechanics execute.
- [x] Audit pack/consumable skipping for positive-EV opportunities and harmful opportunity-cost mistakes. Implementation audit complete across all five D8 booster families and the known D9/D10 consumable blockers; current-HEAD local regression validation remains pending.
- [x] Audit boss-specific execution against exact mechanics. Static production authority inventory is complete; newest regressions remain pending the next local suite run.
- [x] Bound the three-attempt supervisor so final attempt completion cannot issue a fourth restart; retire the historical post-`run_finished` crash unless reproduced on current unchanged HEAD.
- [ ] Add direct regressions for every live defect above before a new authoritative batch.
- [x] Run `tests/balatro` and require green before live validation. Latest validated deterministic checkpoint is historical on 2026-08-26; all changes listed as awaiting validation above require the next local suite run before current HEAD can be called green.
- [ ] Only after semantic/runtime defects are clean, run a fresh three-run Red/White production-default baseline.
- [ ] Keep Optuna numerical tuning frozen until the clean baseline contains no obvious semantic/runtime contradiction.

## Calibration and promotion gate

Three live runs are sufficient for rapid defect discovery, not for proving a candidate is better. Any semantic/runtime fix invalidates the current calibration baseline because the repository SHA changed.

After a clean unchanged-HEAD baseline exists, numerical tuning may resume under the existing Bond tuning contract. Promotion still requires the documented fresh holdout/comparator gate rather than a lucky three-run result.