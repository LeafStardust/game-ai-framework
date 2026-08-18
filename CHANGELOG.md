# Changelog

This file records notable development changes to the project. Active and future work belongs in `ROADMAP.md`; detailed implementation evidence remains in commits, tests, and run logs.

## Unreleased

### v1.0 — Red Deck / White Stake competence (in progress)

#### Added

- Universal Balatro strategy-tree semantics with leaf-only ranking, parent-foundation evidence, descendant inheritance, fallback suppression, Ante pressure, and production diagnostics.
- Complete production catalogue migration for strategy-tree Sections 1–12. The 136-node forest now owns poker hands, ranks/faces, suits/held cards, enhancements, seals, destruction/thinning, deck growth/training, consumable engines, economy, Joker-board composition, discard rotation, and hand scheduling.
- Conditional placement of Section 14 support Jokers into compatible existing routes, including Blueprint/Brainstorm copy support, Astronomer, Chaos the Clown, Drunkard/Merry Andy, Juggler/Troubadour, Splash, Showman, and Invisible Joker. These components do not seed unsupported standalone strategies.
- Portable universal Joker value separated from route-bound strategy value, including dynamic off-path pressure and exclusive dominant-strategy behavior from Ante 6.
- Strategy-aware decisions across hand play, discards, Joker acquisition/replacement, consumables, packs, Planets, rerolls, vouchers, boosters, and blind skips.
- Autonomous Joker-board ordering for Blueprint, Brainstorm, additive/XMult placement, and projected Ceremonial Dagger sacrifice.
- Pre-play hand ordering for first-card retriggers such as Hanging Chad and Photograph.
- Default-off collection unlock campaigns for Hit the Road and Stuntman, guarded by authoritative unlock state and blind-clear safety.
- Opt-in collection-first profile progression with hard priority for explicitly undiscovered visible Jokers, consumables, Vouchers, boosters, and pack choices. The mode can sell a lower-retention incumbent to free Joker or consumable capacity, and its Hit the Road/Stuntman campaigns may intentionally sacrifice the current run.
- Live-monitor strategy diagnostics showing the dominant leaf, status, score, pressure, relevant components, and topology path.

#### Changed

- Expanded strategy catalogues with meaningful Silver and Bronze support while keeping route-specific Jokers Neutral outside compatible infrastructure.
- Retired the seven coarse compatibility strategies and the standalone Edition strategy after the complete tree assumed catalogue ownership; Joker editions remain portable universal value.
- Migrated production policy lookups to root-to-leaf inherited semantics so child routes retain parent hand, card, pack, tag, and cartridge behavior.
- Protected Negative Jokers from ordinary standalone sales, shop replacement transactions and non-Dagger sacrifice ordering. Measured whole-build harm and active-strategy intentional destruction are explicit, logged exceptions; Verdant Leaf remains a survival emergency.
- Increased Gold relationship influence for defining strategy cores and strengthened Silver support where the relationship is materially useful.
- Prioritized The Soul in early Antes when a Legendary Joker is a safe, legal choice.
- Added strategy-aware paid-reroll stop losses, late-Ante survival reserves, and stricter Gold Card/Gold Seal economy reserves.
- Added marginal cash-scaling cost to every paid shop action while Bootstraps or Bull is owned.
- Preserved held Steel cards and Blue Seals before ordinary strategy-fit tie-breaking.
- Bounded late-Ante D1 search, Boss-Blind search, and Joker-order analysis to interactive live budgets.

#### Fixed

- Rejected enhancement Tarot targets that already have the requested enhancement.
- Wired Cerulean Bell forced-card handling and Verdant Leaf emergency Joker sales through authoritative injected actions.
- Prevented blind-selection Joker-order searches from blocking the start of a blind.
- Corrected late-run Small/Big Blind stalls caused by unbounded hand search.
- Stopped paid rerolls from continuing past configured cost and reserve limits.
- Treated an authoritative `won=true` snapshot as terminal even while Balatro still reports `ROUND_EVAL`, preventing unintended entry into Endless and allowing immediate run finalization.
- Allowed a freshly restarted agent to recognize and resume a manually continued post-win Endless run while retaining the default automatic stop at the initial Ante-8 win.

#### Validation

- Passed the complete deterministic repository suite after the full strategy-tree and Negative-retention migration: 1,787 tests on 2026-08-18.
- Completed the first unseeded, fully autonomous Red Deck / White Stake win on 2026-08-18 against Amber Acorn with normal Steam progression preserved.
- The first win exposed the post-win `ROUND_EVAL` finalization gap. The fix is deterministic-test covered; one additional live win is required to validate the complete winning log and immediate automatic OFF behavior.

## v0.9 — Autonomous live integration

- Completed the real-game observe → decide → execute → verify → log → restart/stop loop.
- Added authoritative Windows process-memory observation and first-party injected execution without hidden RNG or future draw-pile access.
- Completed modeled behavior validation for all 150 Jokers and Boss Blind coverage.

## v0.8 — Balatro planning and environment

- Added Balatro search/planning, probability and expected-value analysis, blind-clear paths, stake rules, and deck architecture.

## v0.7 — Balatro mechanics

- Added cards, hands, scoring, Jokers, consumables, editions, enhancements, and card modifiers.

## v0.1–v0.6 — Framework foundation

- Established repository structure, configuration, logging, metrics, events, agent and policy abstractions, heuristic evaluation, softmax selection, experiment execution, reproducible seeds, comparisons, and aggregate metrics.
