# Changelog

This file records notable development changes to the project. Active and future work belongs in `ROADMAP.md`; detailed implementation evidence remains in commits, tests, and run logs.

## Unreleased

- Verified repository-native Mahjong Soul mouse delivery and shared-controller acknowledgement in a Steam AI room: selected and discarded the drawn tile using the observed two-click flow.

- Added shared Mahjong Soul input coordination across discard/Pon/Chi with timeout/disconnect blocking, explicit newer-board recovery, and duplicate protection scoped to authenticated game generation and round.

- Added visually verified multi-choice Chi selection with exact combination-order guards; a live three-choice Steam panel confirmed selection of a red-five meld without conflating the ordinary-five alternative.

- Added guarded single-choice Chi input with exact tile/source confirmation; verified a Steam UI Chi through the live reader. Multiple-combination panels remain blocked pending calibration.

- Added guarded single-choice Pon input and action-context-bound discard layouts; live UI tests confirmed a leftmost discard and Pon, while ambiguous call panels remain blocked.

- Verified Mahjong Soul two-click discard selection/confirmation through the Steam UI and live game events; added explicit visual-confirmation guards and a dry-run input CLI. Native backend delivery and call-panel calibration remain pending.

- Added opt-in Mahjong Soul discard planning and Windows mouse input with calibrated client coordinates, foreground/board checks, expiry, repeat prevention, and live-event confirmation; native clicks await live calibration.

- Added a versioned Mahjong Soul observation adapter with reader readiness, absolute seats, public board data, preserved server operation payloads, and independent snapshots; checked it against the completed live four-player capture.

- Added explicit Mahjong Soul board readiness and a documented consumer interface; hardened replay metadata validation and preserved text-frame diagnostics.

- Added Mahjong Soul capture auditing, connection-close handling, fresh-game board reset, and opaque lobby schema warnings; verified a complete four-player AI match including chi/pon, concealed kan, exhaustive draw, and final scores with 685 contiguous actions.

- Added normalized visible-tile counts and explicit visibility completeness to the Mahjong Soul reader, preserving uncertainty in snapshots/concealed red fives and flagging invalid or physically impossible tile counts.

- Added the shared Mahjong Soul game-reader API and live terminal viewer with per-connection diagnostics, match-end lifecycle, called-discard marking, riichi/drawn-tile/furiten state, and ordinary exhaustive-draw score handling.

- Verified Steam capture on a complete three-player AI match; fixed process-scoped numeric-IP endpoint capture, three-seat state arrays, and match-start handling. All 77 game actions decoded and replayed without gaps; an unrelated lobby schema mismatch remains documented.

- Added isolated Mahjong Soul Windows setup/capture launchers, explicit process capture, worktree-local schema/certificates, timestamped logs, startup validation, and a real loopback WebSocket proxy test.

- Added concealed/added kan state reduction with red-five preservation, reconnect snapshot restoration before action replay, and duplicate round-start protection for Mahjong Soul capture.
- Added schema-driven Mahjong Soul event decoding, connection-scoped RPC matching, seat inference, offline capture replay, and conservative visible-state tracking. Live Steam verification and complete kan/reconnect state reduction remain pending.
- Mahjong Soul Steam capture foundation: loopback proxy launcher, JSONL recording, Liqi envelope/action metadata inspection, and offline capture tests. Live Steam verification and full game-state decoding remain pending.
- Red Deck stake progression begins with v1.1.
- Fresh-profile collection progression remains active but is non-blocking for the v1.0.0 competence release.

## v1.0.0 â€” Red Deck / White Stake competence â€” 2026-08-20

### Added

- Universal Balatro strategy-tree semantics with leaf-only ranking, parent-foundation evidence, descendant inheritance, fallback suppression, Ante pressure, and production diagnostics.
- Complete production catalogue migration for strategy-tree Sections 1â€“12. The 136-node forest owns poker hands, ranks/faces, suits/held cards, enhancements, seals, destruction/thinning, deck growth/training, consumable engines, economy, Joker-board composition, discard rotation, and hand scheduling.
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

## v0.9 â€” Autonomous live integration

- Completed the real-game observe â†’ decide â†’ execute â†’ verify â†’ log â†’ restart/stop loop.
- Added authoritative Windows process-memory observation and first-party injected execution without hidden RNG or future draw-pile access.
- Completed modeled behavior validation for all 150 Jokers and Boss Blind coverage.

## v0.8 â€” Balatro planning and environment

- Added Balatro search/planning, probability and expected-value analysis, blind-clear paths, stake rules, and deck architecture.

## v0.7 â€” Balatro mechanics

- Added cards, hands, scoring, Jokers, consumables, editions, enhancements, and card modifiers.

## v0.1â€“v0.6 â€” Framework foundation

- Established repository structure, configuration, logging, metrics, events, agent and policy abstractions, heuristic evaluation, softmax selection, experiment execution, reproducible seeds, comparisons, and aggregate metrics.
