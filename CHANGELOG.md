# Changelog

This file records notable development changes to the project. Active and future work belongs in `ROADMAP.md`; detailed implementation evidence remains in commits, tests, and run logs.

## Unreleased

### Changed

- Continued Red Deck / White Stake post-release calibration from repeated five-run autonomous batches before advancing stake progression.
- Retired support-only catalogue leaves from active Primary/Secondary/Tertiary strategy competition when they cannot plausibly clear a run as an independent scoring engine. Abstract Joker, standalone face-economy leaves, Satellite economy, Cloud 9 economy, Mail-In Rebate economy, Banner/Delayed Gratification reserve, and standalone cash-growth/hoard leaves remain ordinary or conditional support rather than win conditions. Raised Fist remains a deliberately weak active scoring route rather than a retired support leaf.
- Consolidated cash generation under **Bull / Bootstraps Cash Scoring**. Bull or Bootstraps activates the scoring route; Rocket, To the Moon, Cloud 9, Satellite, Reserved Parking, Business Card, Faceless Joker, Mail-In Rebate, Delayed Gratification, Golden Joker, Golden Ticket, and Rough Gem may reinforce it when their own trigger infrastructure is usable. Rocket + To the Moon together are Gold support after a cash scorer exists; cash generators alone cannot activate the route.
- Made **Pareidolia Gold activation evidence for the Face Cards family**. Pareidolia is also Gold support for PhotoChad when Photograph is present and for the Triboulet route when Triboulet is present, without fabricating those specialized routes by itself.
- Reduced Joker Stencil from Gold to Silver standalone evidence and Banner from Silver to Bronze support where applicable.
- Kept Red Card as a real scaling route but made an owned Red Card prioritize booster-pack skips so its Mult actually develops.
- Added realized-roster pressure to shop decisions so weak/full boards with surplus cash can spend on bounded rerolls rather than preserving money into a losing blind. The release-candidate calibration broadens this beyond a small hard-coded filler set, recognizes decaying public Joker state, allows a deeper one-reroll search for clearly weak full boards, and makes cash-rich Ante 5+ boards search once even when they are not classified as filler-heavy.
- Added weak-full-roster booster reserves so repeated speculative packs cannot drain the run to near-zero cash while the board still needs a Joker upgrade.
- Added final-discard opportunity cost so the last discard is preserved unless its modeled survival/scoring improvement is material.
- Added Burnt Joker first-discard training when the blind has sufficient safety margin.
- Corrected Rocket / To the Moon semantics: individually cash support rather than standalone Gold strategy cores.
- Made Ante phase pressure authoritative across all strategy consumers: Foundation Antes 1-2 use 25%, Formation Antes 3-5 use 50%/70%/90%, and Commitment Ante 6+ uses 100%. Removed an accidental second phase multiplication in Joker build evaluation.

### Fixed

- Corrected Hermit payout/timing integration while preserving the established B6/D4 use contract and Buy-and-Use metadata.
- Added threatened-boss Luchador activation through the autonomous mid-blind sale path.
- Prevented D1 from preferring an all-debuffed scoring hand against suit-debuff bosses when an active-card alternative still satisfies required pace.
- Added Devious Joker + Four Fingers activation logic so a viable Straight route can replace weak filler instead of being blocked by the current first-place strategy.
- Added Perkeo consumable seeding/surplus-copy economy behavior instead of leaving its duplication ability idle.
- Made Low-Rank Scoring require Hack as its defining engine, with Raised Fist banned from that route and Hack banned from the Raised Fist route.
- Made Scholar Silver alone and Gold only with DNA, and reduced Sixth Sense standalone evidence while adding safe first-hand single-6 utilization when consumable capacity and pace permit it.
- Modeled Observatory held-Planet x1.5 scoring, preservation timing, and infrastructure-aware voucher valuation.

- Red Deck stake progression begins with v1.1 after the current Red/White calibration branch is accepted.
- Fresh-profile collection progression remains active but is non-blocking for the v1.0 competence line.

## v1.0.0 — Red Deck / White Stake competence — 2026-08-20

### Added

- Universal Balatro strategy-tree semantics with leaf-only ranking, parent-foundation evidence, descendant inheritance, fallback suppression, Ante pressure, and production diagnostics.
- Complete production catalogue migration for strategy-tree Sections 1–12. The 136-node forest owns poker hands, ranks/faces, suits/held cards, enhancements, seals, destruction/thinning, deck growth/training, consumable engines, economy, Joker-board composition, discard rotation, and hand scheduling.
- Conditional placement of Section 14 support Jokers into compatible existing routes, including Blueprint/Brainstorm copy support, Astronomer, Chaos the Clown, Drunkard/Merry Andy, Juggler/Troubadour, Splash, Showman, and Invisible Joker. These components do not seed unsupported standalone strategies.
- Portable universal Joker value separated from route-bound strategy value, including dynamic off-path pressure and exclusive dominant-strategy behavior from Ante 6.
- Strategy-aware decisions across hand play, discards, Joker acquisition/replacement, consumables, packs, Planets, rerolls, vouchers, boosters, and blind skips.
- Autonomous Joker-board ordering for Blueprint, Brainstorm, additive/XMult placement, and projected Ceremonial Dagger sacrifice.
- Pre-play hand ordering for first-card retriggers such as Hanging Chad and Photograph.
- Default-off collection unlock campaigns for Hit the Road and Stuntman, guarded by authoritative unlock state and blind-clear safety in ordinary competence runs.
- Opt-in collection-first profile progression with hard priority for explicitly undiscovered visible Jokers, consumables, Vouchers, boosters, and pack choices. This mode is separate from the v1.0.0 competence gate and may continue evolving after release.
- Live-monitor strategy diagnostics showing the dominant leaf, status, score, pressure, relevant components, and topology path.

### Changed

- Expanded strategy catalogues with meaningful Gold, Silver, and Bronze support while keeping route-specific Jokers Neutral outside compatible infrastructure.
- Kept Superposition as **Bronze** support for the standalone Straight strategy rather than promoting it to Silver.
- Retired the seven coarse compatibility strategies and the standalone Edition strategy after the complete tree assumed catalogue ownership; Joker editions remain portable universal value.
- Migrated production policy lookups to root-to-leaf inherited semantics so child routes retain parent hand, card, pack, tag, and cartridge behavior.
- Protected Negative Jokers from ordinary standalone sales, shop replacement transactions, and non-Dagger sacrifice ordering. Measured whole-build harm and active-strategy intentional destruction are explicit, logged exceptions; Verdant Leaf remains a survival emergency.
- Increased Gold relationship influence for defining strategy cores and strengthened Silver support where the relationship is materially useful.
- Prioritized The Soul in early Antes when a Legendary Joker is a safe, legal choice.
- Added strategy-aware paid-reroll stop losses, late-Ante survival reserves, and stricter Gold Card/Gold Seal economy reserves.
- Added marginal cash-scaling cost to every paid shop action while Bootstraps or Bull is owned.
- Preserved held Steel cards and Blue Seals before ordinary strategy-fit tie-breaking.
- Bounded late-Ante D1 search, Boss-Blind search, Joker-order analysis, and complete D1 decisions to interactive live budgets.
- Scoped the safe-pace survival invariant to the production strategy-aware D1 policy. The live agent plays when it can meet the current remaining-score-per-hand pace, otherwise prefers a legal discard, and falls back to its strongest bounded play when no discard remains.
- Applied weak-build scoring-readiness vetoes only at the final strategy-aware D13 blind-skip layer while retaining base tag economics as authoritative inputs.
- Tightened weak-board booster spending while preserving strategy-seeding opportunities where appropriate.

### Fixed

- Rejected enhancement Tarot targets that already have the requested enhancement.
- Wired Cerulean Bell forced-card handling and Verdant Leaf emergency Joker sales through authoritative injected actions.
- Prevented blind-selection Joker-order searches from blocking the start of a blind.
- Corrected late-run Small/Big Blind stalls caused by unbounded hand search.
- Added an eight-second wall-clock budget across each complete D1 decision so an individually expensive expectimax node cannot leave early or mid-run hands appearing frozen after the existing node budget.
- Made expired-budget D1 recovery strictly bounded: production may take one legal discard and re-observe, while minimal/test planners retain the bounded structural fallback.
- Prevented the production safe-pace rule from overriding lower-level `CLEAR_PATH` planner contracts or equal-safety hand-selection contracts used by reusable policy tests.
- Stopped paid rerolls from continuing past configured cost and reserve limits.
- Treated an authoritative `won=true` snapshot as terminal even while Balatro still reports `ROUND_EVAL`, preventing unintended entry into Endless and allowing immediate run finalization.
- Allowed a freshly restarted agent to recognize and resume a manually continued post-win Endless run while retaining the default automatic stop at the initial Ante-8 win.
- Corrected the Section 1 Straight strategy contract so its standalone topology and Superposition Bronze-support relationship agree with the intended runtime behavior.

### Validation

- Passed the complete deterministic repository suite after the full strategy-tree and Negative-retention migration: **1,787 tests on 2026-08-18**.
- Completed an **unseeded, fully autonomous Red Deck / White Stake win** on 2026-08-18 against Amber Acorn with normal Steam progression preserved.
- The winning run exposed the post-win `ROUND_EVAL` finalization gap; the resulting terminal-detection fix is covered by deterministic regressions.
- v1.0.0 freezes the Red Deck / White Stake competence baseline. Further collection-system work is non-blocking, and stake-specific adaptation continues in v1.1+.

## v0.9 — Autonomous live integration

- Completed the real-game observe → decide → execute → verify → log → restart/stop loop.
- Added authoritative Windows process-memory observation and first-party injected execution without hidden RNG or future draw-pile access.
- Completed modeled behavior validation for all 150 Jokers and Boss Blind coverage.

## v0.8 — Balatro planning and environment

- Added Balatro search/planning, probability/EV analysis, blind-clear paths, stake rules, and deck architecture.

## v0.7 — Balatro mechanics

- Added cards, hands, scoring, Jokers, consumables, editions, enhancements, and card modifiers.

## v0.1–v0.6 — Framework foundation

- Established repository structure, configuration, logging, metrics, events, agent and policy abstractions, heuristic evaluation, softmax selection, experiment execution, reproducible seeds, comparisons, and aggregate metrics.
