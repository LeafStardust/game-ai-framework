# Changelog

This file records notable development changes to the project. Active and future work belongs in `ROADMAP.md`; detailed implementation evidence remains in commits, tests, and run logs.

## Unreleased

### Added

- Added the **offline Optuna Bond-tuning subsystem** defined in `docs/balatro/BALATRO_BOND_TUNING.md`: typed immutable `BondCalibration`, audited Phase-A parameter overrides, seeded and authoritative-live evaluators, persistent revision-bound Optuna studies, exact run provenance, production-baseline queuing/tagging, fresh-boundary live preflight, baseline-aware reports, and conservative holdout/promotion comparison. Optuna remains excluded from the normal live-agent decision path, cannot redefine Bond semantics or use hidden information, and cannot automatically promote its output.
- Added the Red/White **Build Health** layer with auditable Survival, Immediate Scoring, Scaling, Coherence, and Runway dimensions so a full Joker roster is no longer assumed to be a functioning build.
- Added realized engine lifecycle diagnostics (`OWNED_INACTIVE`, `ACTIVATED_WEAK`, `ACTIVATED_HEALTHY`, `MATURE`) for Blue/Hologram deck growth, Burnt Joker, Castle, Green Joker, Red Card, Runner, and Bull/Bootstraps cash scoring.
- Added structural `CORE` / `ENGINE` / `SUPPORT` / `FILLER` / `CONFLICT` Joker-role diagnostics relative to the realized active build.
- Added bounded two-component shop planning for Bull + Bootstraps and Blue/Hologram + Certificate/Marble. The planner emits exactly one sell/buy action and requires authoritative re-observation before continuing the sequence.
- Added Build Health, scaling-deficit/inactive-engine warnings, and realized component roles to structured decision postmortems and the live agent monitor.
- Added canonical Bond motif prescription preferences beneath existing pack/shop safety authorities for Baron/Mime/Steel, Photograph/Hanging Chad, Vampire/Midas, Burnt target leveling, and Hack low-rank retrigger engines.
- Added a production SHOP survival adapter that samples only unordered public owned-deck opening hands and runs a narrow, node-bounded D1 `LiveBlindClearPlanner` from each opening to estimate next-blind clear probability.
- Added deterministic regression contracts for Build Health evaluation, shop admission/replacement/reroll behavior, realized pivot readiness, bounded bundles, component roles, monitor output, production arbiter inheritance, cache invalidation, Bond pivot authority, Bond prescription normalization, SHOP clear-probability fallback/isolation, public deck-order invariance, copy-Joker projection safety, and the Red/White live planner budget.

### Changed

- Removed the remaining pre-Bond categorical `PlaystyleIntent` and irreversible Ante lock from Joker valuation, held-card decisions, Planet selection, packs, blind skipping, and production runtime wiring. Canonical Bonds/composition and Strategy Plans are now the only strategic direction source; mechanical build profiling remains a subordinate evidence layer.
- Replaced `build_intent` telemetry with canonical `bond_build` events containing the mechanical build profile, Bond/composition diagnostics, and behavior-backed synergies.
- Retired the neutral pack/shop/hand playstyle compatibility shells and renamed installed timestamp-, batch-, and release-labelled modules around the stable mechanics they implement.
- Converted systematic Bond numerical calibration from a documentation-only plan into an implemented staged offline optimization path. The first live gate is now a clean production-default 3-run baseline on one unchanged repository HEAD; only then may Phase-A candidate trials begin. Promotion requires a fresh comparison with at least **20 completed episodes per arm** plus the implemented objective, Ante, runtime, diversity, win-rate, and illegal-action checks.
- Continued Red Deck / White Stake post-release calibration from repeated five-run autonomous batches before advancing stake progression.
- Replaced the old Ante 1–2 “any positive immediate scorer” exception with Build-Health-based survival admission: an off-route purchase must materially improve projected survival rather than merely add local scoring value. Production SHOP survival now reuses D1 whole-blind clear-probability semantics through a strictly bounded public-state opening-hand projection; if that bounded projection is unavailable, the generic Build Health capacity estimate remains the fail-safe.
- Kept the new SHOP D1 projection production-only so injected/custom Build Health scorers and offline deterministic contracts retain the generic estimator rather than unexpectedly invoking live planner semantics.
- Made midgame Joker acquisition, legal replacement, bounded rerolls, and complementary shop bundles respond to realized scaling deficits instead of relying on Joker count or isolated candidate value.
- Added realized-maturity pivot pressure so late theoretical engines pay buildup/runway cost: an untrained late Runner or inactive Hologram no longer gets the same pivot treatment as an already-realized high-cash Bull/Bootstraps route.
- Made canonical pivot authority require trustworthy Joker-slot telemetry before treating the roster as full, preventing missing/zero/invalid slot observations from triggering structural replacement promotion or veto logic.
- Normalized Bond prescription matching across live naming/telemetry variants for consumables, Planet target hands, rank aliases, Steel enhancements, and Red/Blue Seals while retaining bounded bonuses and child-policy legality/safety authority.
- Made Blue Joker recognize Certificate/Marble as realized future deck-growth capacity, matching the bounded deck-growth bundle planner.
- Expanded Build Health cache identity from deck size alone to complete public deck structure, preventing same-size rank/suit/enhancement/seal/edition changes from reusing stale health.
- Replaced the active categorical Gold/Silver/Bronze strategy-tree architecture during v1.0.x with the canonical Currency-Wars-style Bond/composition architecture. Historical v1.0.0 release notes below remain historical evidence rather than current runtime documentation.
- Kept Red Card as a real scaling route but made an owned Red Card prioritize booster-pack skips so its Mult actually develops.
- Added realized-roster pressure to shop decisions so weak/full boards with surplus cash can spend on bounded rerolls rather than preserving money into a losing blind.
- Added weak-full-roster booster reserves so repeated speculative packs cannot drain the run to near-zero cash while the board still needs a Joker upgrade.
- Added final-discard opportunity cost so the last discard is preserved unless its modeled survival/scoring improvement is material.
- Reconciled Bond realization semantics so ordinary public-state realization tracks currently available engines/opportunities, while explicit discard/scoring/blind-selection telemetry remains authoritative for exact trigger windows and Joker-order-sensitive effects such as Vampire/Midas.
- Tightened Red/White live D1 from 5,000 to **2,500 maximum search nodes** while preserving horizon 5, `probe-deepest`, and the 8-second hard wall clock.
- Increased upgrade pressure against weak full rosters and stopped generator-only Marble/Certificate structures from being treated as completed deck-growth scoring routes when their actual scoring payoff is absent.

### Fixed

- Corrected canonical hand-Bond membership so Mad/Clever advance their actual Two Pair condition instead of falsely advancing Four of a Kind. Jolly/Sly retain legitimate shared Pair and Two Pair membership because their Pair condition also triggers inside Two Pair.
- Made lifecycle semantic checkpoints suppress independent random score rolls. Misprint and other stochastic Jokers can still provide modeled score value, but random checkpoint drift can no longer fabricate Planet, Tarot, discard, round, or arbitrary event scaling dependencies.
- Propagated D1's hard wall-clock deadline into every held-The-Sun target preview and escape search. A consumable escape can no longer run an independent 81-second search behind an advertised eight-second D1 budget.
- Fixed stale README links to removed strategy-tree documents and aligned collection-mode wording with Bond/composition authority.
- Fixed Burnt Bond execution so a safe first discard can level its target hand even when Banner is owned; temporary Banner discard-chip value no longer suppresses the defining Burnt mechanic.
- Fixed canonical pivot authority so an ACTIVE/MATURE power engine cannot be casually dismantled merely because a replacement creates several fresh partial Bonds; power-engine protection remains a cost, not an absolute lock.
- Fixed late-game marginal side-pack spending that could drain a vulnerable Ante 5+ run to near-zero cash despite existing reserve diagnostics.
- Fixed repeated D1 Bond-composition recomputation inside candidate tie-breaks by caching Bond hand intents per settled decision.
- Corrected Hermit payout/timing integration while preserving the established B6/D4 use contract and Buy-and-Use metadata.
- Added threatened-boss Luchador activation through the autonomous mid-blind sale path.
- Prevented D1 from preferring an all-debuffed scoring hand against suit-debuff bosses when an active-card alternative still satisfies required pace.
- Added Perkeo consumable seeding/surplus-copy economy behavior instead of leaving its duplication ability idle.
- Modeled Observatory held-Planet x1.5 scoring, preservation timing, and infrastructure-aware voucher valuation.
- Corrected realization edge cases across discard triggers, debuffed cards, Gold/Blue Seal timing, Card Sharp repetition history, Four Fingers advanced hands, held retriggers, Vampire/Midas order, Satellite unknown history, and renewable-feed fallback semantics.
- Fixed Blueprint/Brainstorm live projection so supported scored-card and held-card targets such as Photograph can contribute to Joker-order optimization instead of leaving Blueprint as a rightmost no-op. Unsupported copy targets remain fail-closed; Bloodstone is not treated as an independently validated copy target.

### Validation

- Nine uploaded Red/White attempts from 2026-08-24 through 2026-08-25 were reviewed as forensic evidence. They confirmed the hand-Bond catalogue and stochastic-lifecycle defects above; they also predate the current conflict, Planet-scaler, ordering, and engine-retention fixes, so a fresh unchanged-HEAD batch is required before numerical calibration.
- The complete Balatro deterministic suite was green after the categorical-to-Bond migration and subsequent stale-test cleanup on 2026-08-23 before the newest live-batch fixes; each new execution/pivot/resource change remains subject to a fresh full `python -m pytest -q tests/balatro` gate.
- A subsequent five-run Red/White batch exposed Burnt under-utilization, weak power-engine preservation, marginal late pack spending, and a D1 Bond recomputation performance defect; those concrete defects have been corrected and require fresh unchanged-HEAD live validation.
- The authoritative tuning foundation is implemented, but **Phase-A candidate search is not yet unlocked**. The historical `e0cb0984` baseline is forensic/reference evidence only because later semantic/runtime fixes changed the repository SHA. The next empirical gate is a clean production-default 3-run live baseline on the final unchanged HEAD; any new semantic/runtime fix invalidates that study and requires a new baseline.
- Red Deck stake progression begins with v1.1 after the current Red/White calibration branch is accepted.
- Fresh-profile collection progression remains active but is non-blocking for the v1.0 competence line.

## v1.0.0 — Red Deck / White Stake competence — 2026-08-20

The entries below describe the historical v1.0.0 release architecture. The active v1.0.x runtime has since migrated to canonical Bonds/composition.

### Added

- Universal Balatro strategy-tree semantics with leaf-only ranking, parent-foundation evidence, descendant inheritance, fallback suppression, Ante pressure, and production diagnostics.
- Complete production catalogue migration for strategy-tree Sections 1–12. The 136-node forest owns poker hands, ranks/faces, suits/held cards, enhancements, seals, destruction/thinning, deck growth/training, consumable engines, economy, Joker-board composition, discard rotation, and hand scheduling.
- Conditional placement of Section 14 support Jokers into compatible existing routes, including Blueprint/Brainstorm copy support, Astronomer, Chaos the Clown, Drunkard/Merry Andy, Juggler/Troubadour, Splash, Showman, and Invisible Joker.
- Portable universal Joker value separated from route-bound strategy value, including dynamic off-path pressure and exclusive dominant-strategy behavior from Ante 6.
- Strategy-aware decisions across hand play, discards, Joker acquisition/replacement, consumables, packs, Planets, rerolls, vouchers, boosters, and blind skips.
- Autonomous Joker-board ordering for Blueprint, Brainstorm, additive/XMult placement, and projected Ceremonial Dagger sacrifice.
- Pre-play hand ordering for first-card retriggers such as Hanging Chad and Photograph.
- Default-off collection unlock campaigns for Hit the Road and Stuntman, guarded by authoritative unlock state and blind-clear safety in ordinary competence runs.
- Opt-in collection-first profile progression with hard priority for explicitly undiscovered visible Jokers, consumables, Vouchers, boosters, and pack choices.
- Live-monitor strategy diagnostics showing the dominant leaf, status, score, pressure, relevant components, and topology path.

### Changed

- Expanded strategy catalogues with meaningful Gold, Silver, and Bronze support while keeping route-specific Jokers Neutral outside compatible infrastructure.
- Kept Superposition as **Bronze** support for the standalone Straight strategy rather than promoting it to Silver.
- Retired the seven coarse compatibility strategies and the standalone Edition strategy after the complete tree assumed catalogue ownership; Joker editions remain portable universal value.
- Migrated production policy lookups to root-to-leaf inherited semantics so child routes retain parent hand, card, pack, tag, and cartridge behavior.
- Protected Negative Jokers from ordinary standalone sales, shop replacement transactions, and non-Dagger sacrifice ordering.
- Prioritized The Soul in early Antes when a Legendary Joker is a safe, legal choice.
- Added strategy-aware paid-reroll stop losses, late-Ante survival reserves, and stricter Gold Card/Gold Seal economy reserves.
- Added marginal cash-scaling cost to every paid shop action while Bootstraps or Bull is owned.
- Preserved held Steel cards and Blue Seals before ordinary strategy-fit tie-breaking.
- Bounded late-Ante D1 search, Boss-Blind search, Joker-order analysis, and complete D1 decisions to interactive live budgets.
- Scoped the safe-pace survival invariant to the production strategy-aware D1 policy.
- Applied weak-build scoring-readiness vetoes only at the final strategy-aware D13 blind-skip layer while retaining base tag economics as authoritative inputs.

### Fixed

- Rejected enhancement Tarot targets that already have the requested enhancement.
- Wired Cerulean Bell forced-card handling and Verdant Leaf emergency Joker sales through authoritative injected actions.
- Prevented blind-selection Joker-order searches from blocking the start of a blind.
- Corrected late-run Small/Big Blind stalls caused by unbounded hand search.
- Added an eight-second wall-clock budget across each complete D1 decision.
- Made expired-budget D1 recovery strictly bounded.
- Prevented the production safe-pace rule from overriding lower-level `CLEAR_PATH` planner contracts or equal-safety hand-selection contracts used by reusable policy tests.
- Stopped paid rerolls from continuing past configured cost and reserve limits.
- Treated an authoritative `won=true` snapshot as terminal even while Balatro still reports `ROUND_EVAL`.
- Allowed a freshly restarted agent to recognize and resume a manually continued post-win Endless run while retaining the default automatic stop at the initial Ante-8 win.

### Validation

- Passed the complete deterministic repository suite after the full historical strategy-tree and Negative-retention migration: **1,787 tests on 2026-08-18**.
- Completed an **unseeded, fully autonomous Red Deck / White Stake win** on 2026-08-18 against Amber Acorn with normal Steam progression preserved.
- The winning run exposed the post-win `ROUND_EVAL` finalization gap; the resulting terminal-detection fix is covered by deterministic regressions.

## v0.9 — Autonomous live integration

- Completed the real-game observe → decide → execute → verify → log → restart/stop loop; authoritative live state, injected execution, stochastic projection, 150/150 Joker validation and Boss Blind coverage.
