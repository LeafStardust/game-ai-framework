# Balatro Red/White Competence Roadmap

Status: **D14 / D11 SHOP latency gate closed; D1 authority-latency gate closed; next gate is unchanged-HEAD Red/White competence baseline / calibration**

This document is the handoff contract for Red Deck / White Stake competence work. It exists so future contributors do not have to reconstruct the intended Balatro play philosophy from live-run postmortems.

## Future-chat operating contract

This section is authoritative for future chats working on this roadmap. Do not guess commands, branch names, validation state, entrypoints, artifact locations, or runtime workflow when the repository or this roadmap can answer them.

### Repository and branch

- Repository: `LeafStardust/game-ai-framework`.
- Active competence branch: `feat/v1.0-red-white-competence`.
- Stay on that branch unless the user explicitly changes the target.
- After the assistant pushes any commit that the user needs locally, the first command given to the user must be exactly:

```powershell
git pull
```

Do not replace this with a longer remote/branch form unless the user's local Git setup actually requires it.

### Canonical Windows commands

Use the repository-provided batch entrypoints instead of inventing Python entrypoints.

Normal single Balatro live attempt:

```powershell
git pull
.\BalatroAgentToggle.bat
```

Three-attempt batch, only when a three-run batch is explicitly required by the current gate:

```powershell
git pull
.\BalatroAgentToggle.bat --three
```

Five-attempt batch, only when a five-run batch is explicitly required:

```powershell
git pull
.\BalatroAgentToggle.bat --five
```

Full deterministic Balatro test suite:

```powershell
git pull
python -m pytest -q tests/balatro
```

Diagnostics report:

```powershell
.\BalatroAgentDiagnosticsReport.bat
```

Crash report:

```powershell
.\BalatroAgentCrashReport.bat
```

Runtime monitor:

```powershell
.\BalatroAgentMonitor.bat
```

Collection-first compatibility mode exists as `BalatroAgentCollectionToggle.bat`, but collection-first behavior is retired from the ordinary Red/White competence path and must not be used for normal competence validation.

Never tell the user to run `python main.py` for the Balatro live agent. Never invent a `python -m ...` live command when a repository batch entrypoint already provides the supported command. If a command is uncertain or appears to have changed, inspect the relevant `.bat` file or runtime module in the repository before answering.

### Validation ownership and cadence

- The assistant must **not run tests or live Balatro attempts**. The user runs local validation and reports the result / uploads the generated artifacts.
- Reading tests, writing tests, and adding regression coverage is allowed; executing them is not.
- Do not ask the user to rerun the full suite when they have already reported it green for the current code HEAD and no subsequent code/test commit has invalidated that result.
- A documentation-only commit does not by itself invalidate a green gameplay/test checkpoint.
- After a code/test commit, provide `git pull` followed by every exact command the user needs to run. Do not give only part of the command sequence and do not make the user infer the live entrypoint.
- When a focused single live run is sufficient for a profiler/performance gate, request `.\BalatroAgentToggle.bat`, not a three- or five-run batch.
- For live evidence, ask for the generated run summary and JSONL trace. If their exact output path or filename convention is uncertain, inspect the runtime implementation first rather than guessing.

### No-guess handoff rule

Future chats must treat missing operational knowledge as a repository-reading task, not an invitation to improvise. Before giving a command or claiming a current checkpoint, verify it against this roadmap, the relevant helper script/module, recent commits, or the supplied live evidence.

Any durable detail discovered during work that would materially help the next chat must be written back into repository documentation before the work session is considered handed off. At minimum, record newly discovered or changed:

- canonical commands and helper entrypoints;
- active branch / release gate constraints;
- who owns local validation and which tests are already green;
- generated artifact names/locations needed for analysis;
- current decision-authority boundaries;
- profiler field meanings and instrumentation caveats;
- current measured blocker and next validation step;
- install/wrapper ordering requirements that affect production behavior;
- important failure signatures that have been fixed and should not be re-diagnosed blindly;
- any other fact that caused avoidable reconstruction, contradictory instructions, or guessing across chats.

Put stable cross-chat instructions in this roadmap. Put detailed dated implementation evidence in `BALATRO_ROADMAP_IMPLEMENTATION_HISTORY.md` or the relevant audit document, and link/summarize the current consequence here when future work depends on it. Do not rely on chat memory alone for information the next contributor will need.

## Current checkpoint — 2026-08-28

The D14/D11 SHOP latency blocker is **closed**. The measured reroll-active D11 future path fell from approximately **20.8 s** before the Joker/Tarot bounds to approximately **3.17 s**, with no meaningful hidden residual. Do not continue optimizing SHOP families unless new profiling evidence reopens that gate.

The D1 authority-latency blocker is also **closed** on current evidence. Before the deadline repair, focused run `balatro-20260828T114850Z-0fbca9a7-attempt-001` contained 41 D1 decisions with approximately **1.56 s mean / 1.59 s median / 8.70 s max** total latency. One pathological decision spent approximately **8.69 s** entirely in `immediate_fallback_search` and reported that the D1 wall-clock budget was exhausted before pace fallback completed.

Root cause was candidate generation / candidate-priority projection occurring before the first planner node while deadline enforcement historically lived only around node consumption. The repair moved hard deadline checks and the 0.75 s initial-root candidate bootstrap into canonical `LiveBlindClearPlanner`; `semantic_search_guard_policy` now preserves only its semantic prefilters/reserves and delegates deadline/bootstrap to the planner. `games/balatro/d1_candidate_deadline_policy.py` remains compatibility-only and must not be reinstalled as a competing `_candidate_actions` authority.

The user reported the focused D1 tests and full `tests/balatro` suite **green** after the final deadline-authority consolidation. Focused live validation run `balatro-20260828T123054Z-88fe4bcc-attempt-001` then produced **73 D1 decisions** with approximately:

- total D1 mean: **1.78 s**;
- total D1 median: **1.97 s**;
- total D1 max: **4.37 s**;
- `base_policy` mean / max: **0.52 s / 1.82 s**;
- `adaptive_search` mean / max: **0.48 s / 1.11 s**;
- `confirmation_search` mean / max: **0.03 s / 0.39 s**;
- `immediate_fallback_search` mean / max: **0.75 s / 1.77 s**;
- Strategy Health mean / max: approximately **0.003 s / 0.005 s**;
- residual: effectively zero.

There were **no** `budget_exceeded=True` search records and **no** `D1 wall-clock budget exhausted` rationale messages. The former 8.69 s fallback class therefore disappeared. The new worst decision (4.37 s) was distributed across `base_policy` (~1.82 s), adaptive search (~1.11 s), and fallback (~1.43 s), so no single replacement pathological bucket emerged. Discard decisions were still materially slower than Play decisions (about **2.69 s mean** vs **1.02 s mean**), but that cost is distributed across ordinary base/adaptive/fallback work rather than a deadline defect. Further reduction would now be broad quality-vs-speed tuning and must not proceed without a new measured reason.

The focused live run reached **Ante 5 Big Blind** and lost naturally at **15,668 / 16,500** with `$113`, four Jokers, no crash, and no latency-budget exhaustion. One loss is not evidence of a semantic regression. The next gate is therefore an **unchanged-HEAD Red/White competence baseline / calibration pass**, not another latency micro-optimization.

## Git commit convention

All commits made while working this roadmap must follow the repository's existing Conventional Commit-style subject format.

Use lowercase type and optional lowercase scope followed by a colon and concise imperative subject, for example:

- `fix(balatro): keep downgraded joker tiers exclusive`
- `test(balatro): expect Bronze Superposition support`
- `docs: finalize v1.0.0 changelog`
- `feat: install Balatro v1.0.0 policy`

For Balatro-specific implementation or regression work, prefer an explicit `(balatro)` scope when it matches the surrounding history. Do not use unscoped sentence-style subjects such as `Benchmark canonical safe pace D1 authority`.

## Consolidation batching rule

Phase-0 and competence cleanup work may and should batch multiple related low-risk migrations in one implementation pass when they share the same authority boundary. Do not artificially stop after each wrapper or one-file cleanup. A batch is appropriate when each included change is independently understood, preserves the same canonical objective, and can be covered by the same local semantic/regression gate.

Keep unrelated or high-risk authority changes separate when combining them would make failures ambiguous. The user performs local validation; repository-side work should therefore make meaningful grouped progress between validation checkpoints instead of requesting a rerun after every trivial migration.

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

The deterministic Balatro suite is green at the latest validated current checkpoint after the final D1 deadline-authority consolidation.

Completed or implementation-audited in the current semantic/runtime pass:

- literal current/candidate score authority is implementation-complete: D2 representative probes include played-card chips, exact hand levels and the three secret hands, legal Blueprint/Brainstorm ordering, stateful conditional contexts such as Card Sharp, post-transaction cash for Bull/Bootstraps, next-round discard allowance for Banner, and analytic public-mechanics expectation for stochastic score sources such as Bloodstone/Misprint; the final category-only early-Joker force-buy was removed so semantic labels cannot manufacture score or admission;
- the shared literal scorer and D2 representative probe catalogue include **Five of a Kind, Flush House, and Flush Five** with their exact base scores, so secret-hand runs no longer lose those hand types during shop current/candidate valuation;
- the named contextual-Joker valuation audit is complete for **Joker Stencil, Card Sharp, Ride the Bus, Bull, Bootstraps, Banner, Green Joker, Blueprint, and Brainstorm**;
- Joker replacement implementation compares a common literal incumbent/candidate baseline, post-transaction cash, economy, edition/slot effects, realized-engine retention, FORMING/PINNED strategy disruption, Negative retention, and exact selected shop-copy identity;
- D14 replacement cash-scaling cost excludes the sold incumbent, preventing Bull/Bootstraps from being charged as though they still existed after replacement;
- D3 voucher admission is authoritative inside D14 instead of being bypassed by the generic shop layer, with parent money/interest/reserve costs normalized on the shared resource scale;
- persistent voucher parent value now uses grounded unavoidable-round mechanics where possible and fails closed for future-policy-contingent event counts instead of inheriting arbitrary cross-family constants;
- D11 future-shop Joker value comes from the current public eligible Joker pools through D2/D14, including replacement admission and public edition odds; only unseen future price remains an explicit prior;
- D11 future-shop Planet value averages the currently eligible Planet pool through D4/D14;
- D11 future-shop Tarot value uses the same held public-mechanics future-use evaluator as D14, including High Priestess, Emperor and Judgement generation semantics rather than a synthetic fixed gross-value prior;
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
- held High Priestess/Emperor/Judgement purchases are valued through their installed future D9 public-mechanics paths; the held card's own consumption releases the slot before generated consumables resolve, so the pre-purchase occupancy is the correct post-use generation occupancy;
- **Ouija** uses exact uniform expectation over all 13 rank rewrites minus a shared literal permanent hand-size opportunity cost; injected completion verifies the common-rank rewrite and exact `hand.limit - 1` transition;
- **Ectoplasm** uses the public escalating `ecto_minus`, a shared permanent hand-size opportunity model, and the marginal D11 public future-Joker value of one additional Joker slot instead of a fixed Negative-edition bonus; injected completion verifies exactly one editionless Joker becomes Negative, hand limit falls by the pre-use penalty, and `ecto_minus` increments;
- the shared permanent hand-size opportunity model compares expected best literal future-hand score at `H` versus `H-N` from unordered public permanent-deck composition, uses D1's deterministic public draw model, and explicitly removes transient current-blind/current-round/shop state from that future valuation;
- **Cryptid**, **Familiar**, **Grim**, **Incantation**, and **Immolate** have explicit production outcome/target models and semantic execution verification rather than generic deferred handling;
- **Wheel of Fortune** shop and pack paths share analytic public-state expectation rather than synthetic option floors;
- **The Soul** uses expectation over the five modeled Legendary outcomes instead of a fixed early-Ante bonus;
- deterministic targeted Tarot/Spectral execution preserves live-card identity, rejects no-op transformations, and verifies resulting mutations;
- **Black Hole** completion requires every modeled poker-hand level to increase by exactly one;
- **The Serpent**, **The Hook**, **The Tooth**, **The Ox**, **The Psychic**, **Cerulean Bell**, and the other Red/White bosses are accounted for by exact D1/live-state mechanics; the full static production inventory is documented in `BALATRO_BOSS_MECHANICS_AUDIT.md`;
- Verdant Leaf and proactive Luchador sale decisions are now conditional on strict D1 survival improvement rather than boss identity/debuff presence alone;
- target-hand execution, Card Sharp repetition, Eye/Mouth constraints, and D1 search prefilters use the same state-aware hand rules as the canonical scorer;
- safe-pace, pinned-strategy, no-discard, Mouth redraw, Sixth Sense, DNA, Castle and Burnt substitutions are subordinate to canonical full-blind clear probability rather than local pace/setup value;
- the core D1 tuple hierarchy now keeps full-blind clear/progress/hands/discards above held-card preservation, Bond fit and Vagabond setup preference;
- held-resource D1 semantics keep Steel inside literal scoring and use Blue Seal/Gold preservation only when mechanically appropriate;
- Ceremonial Dagger, Blueprint/Brainstorm exact-play ordering, first-card-sensitive ordering, dominated Gold/Blue-Seal/Steel overplay, Purple-Seal discard branch coverage, and Ride the Bus terminal-stack preservation are represented in the production path;
- visible two-Joker shop combination assembly is generic and Bond-derived: D2 projects the first exact visible purchase, reruns canonical D2 on the second, requires the second to become a real BUY because of the first, normalizes both steps on D14, executes one checkpoint, then re-observes. The historical named-pair short-horizon planner is retired from production authority;
- FORMING, PINNED, developed-Bond and invested tactical-scaler retention cannot veto an upstream-legal replacement when current Build Health is already critical and the exact post-transaction projected state strictly improves survival;
- pre-blind temporary-Joker cleanup/Riff-Raff cycling cannot sacrifice modeled survival merely to free a slot or cash out an expiring scorer;
- the first-party injected bridge tolerates transient Windows access races;
- the bounded three-attempt supervisor stops after attempt 3 without invoking a fourth restart.

## Static audit result before local validation

No remaining known **semantic/runtime authority inversion** was found in the installed Red/White production path during this pass. The remaining intentionally conservative behavior is not represented as fake utility:

- policy-contingent persistent vouchers whose payoff requires an unknown number of future optional rerolls/purchases/packs/shop opportunities remain fail-closed at D14 rather than receiving invented event counts;
- threshold-driven cash floors, D13 skip/tag weighting, local setup floors, pack-goal bonuses and similar numeric preferences remain calibration parameters for the later Python/Optuna phase;
- historical compatibility modules may remain in-tree, but the hard-coded named Joker bundle planner is no longer a production combination authority.

This is the point at which static semantic work stops and local execution evidence becomes authoritative. Any deterministic regression failure or clearly dominated live action reproduced on unchanged HEAD reopens the semantic/runtime gate before numerical tuning.

## Current repair queue

The historical semantic repair queue below is retained as implementation history. Current operational work has passed the SHOP and D1 latency gates; do not regress to those workstreams without new measurements.

- [x] Ensure literal score projection is authoritative for current and candidate builds; remove synthetic category substitutes. Implementation audit complete.
- [x] Audit contextual Joker valuation, beginning with Stencil, Card Sharp, Ride the Bus, Bull, Bootstraps, Banner, Green Joker, Blueprint, and Brainstorm.
- [x] Wire strategy formation and R0 evidence into acquisition from Ante 1 without making strategy outrank survival.
- [x] Repair shop cross-family arbitration so visible Joker strength, vouchers, packs, consumables, rerolls, and economy compare on a common parent scale.
- [x] Repair Joker replacement using actual incumbent/candidate score, scaling, economy, realization, and strategy disruption.
- [x] Repair D1 discard selection at the authoritative planner/controller layer so multi-card redraws are considered correctly and strategy-specific discard mechanics execute.
- [x] Audit pack/consumable skipping for positive-EV opportunities and harmful opportunity-cost mistakes.
- [x] Audit boss-specific execution against exact mechanics.
- [x] Bound the three-attempt supervisor so final attempt completion cannot issue a fourth restart; retire the historical post-`run_finished` crash unless reproduced on current unchanged HEAD.
- [x] Add direct Red/White regression coverage for the concrete semantic defects introduced/closed in this pass where a compact deterministic regression is available; broader existing subsystem regressions remain part of `tests/balatro`.
- [x] **Current deterministic gate:** focused D1 deadline/latency tests and full `tests/balatro` reported green after final deadline-authority consolidation.
- [x] **SHOP live latency gate:** D14/D11 future-family profiling and Joker/Tarot bounds reduced the measured D11 future path from ~20.8 s to ~3.17 s; SHOP latency blocker closed.
- [x] **D1 live latency gate:** 73-decision focused run removed the former ~8.69 s immediate-fallback spike; no budget exhaustion and no new dominant pathological bucket observed.
- [ ] **Current baseline gate:** establish a clean unchanged-HEAD Red/White live competence baseline suitable for post-semantic calibration / promotion work.
- [ ] Keep new gameplay features, decks, stake progression, and broader v1.1+ work frozen until the Red/White competence/performance gate closes.

## Calibration and promotion gate

Three live runs are sufficient for rapid defect discovery, not for proving a candidate is better. Any semantic/runtime fix invalidates the current calibration baseline because the repository SHA changed.

After a clean unchanged-HEAD baseline exists, numerical tuning may resume under the existing Bond tuning contract. Promotion still requires the documented fresh holdout/comparator gate rather than a lucky three-run result.
