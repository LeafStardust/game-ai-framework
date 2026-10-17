# Changelog

This file records notable development changes to the project. Active and future work belongs in `ROADMAP.md`; detailed implementation evidence remains in commits, tests, and run logs.

## Unreleased

- Bundled capture and automatic Mahjong play under one supervised agent launcher; added a read-only capture/suggestion monitor launcher, exact capture-file binding, startup readiness and owned-process cleanup.

- Wired ATK automatic play to visually verified single-choice Chi/Pon, with legal-action filtering that declines kan and ambiguous call menus instead of requiring manual input; retained durable recordings and server-confirmed input sequencing.

- Upgraded four-player ATK to v0.2 for manual suggestions: scored tenpai value, yaku-aware Chi/Pon, cautious kan, furiten/dama Riichi checks, broader danger ranking and room-rule-aware open Tanyao; added an action-only suggestion launcher.

- Extended automatic Mahjong play to Riichi, Ron, Tsumo and combined-offer Skip; added forced post-Riichi discards, cursor parking, live capture health, an exclusive agent lock, automatic session evidence and an incident-report CLI.

- Connected Mahjong playbooks to an opt-in 1080p discard/Chi-Skip runner with reviewed tile recognition, stable-frame checks, one persistent controller and exact server confirmation; unsupported actions remain manual.

- Added the four-player ATK playbook with bounded ukeire/value trade-offs, selective value pushes and constrained counter-Riichi; registry selection now uses player count and playstyle, with balanced unchanged as the default.

- Added versioned three/four-player Mahjong playbooks, shared value/defense features and a manual-only balanced policy with dora/yakuhai tie-breaks, genbutsu folding and Riichi threat settings.

- Audited a completed ten-round manual Mahjong match and replay-validated all 164 current-policy decisions, including five Riichi recommendations, without game decode or proposal errors.

- Added server-offered Riichi recommendations using the best offered tenpai discard; changed readable tile labels to Man, Pin and Sou.

- Simplified Mahjong shadow output to readable recommended actions only; full analysis/metadata JSON now requires `--json`.

- Added a shanten/visible-ukeire discard policy with fixed-meld, kan, red-five and sanma handling; made it the read-only shadow/evaluation CLI default and validated it on two recorded captures.

- Made Mahjong shadow terminal output suggestions-only by default; diagnostic statuses remain available with `--verbose`.

- Added a persistent read-only Mahjong shadow runner with game-connection freshness checks, historical bootstrap suppression, board deduplication and capture lifecycle regression coverage.

- Added an isolated Mahjong policy adapter, deterministic integration baseline and offline contract evaluator; validated all 131 decision-bearing recorded boards without input or policy failures.

- Added board-bound read-only Mahjong decision requests and strict current-server-offer proposal validation, with exact tile/call semantics and offline capture replay coverage.

- Reviewed Mahjong reader/input readiness, documented the decision-interface boundary and added generation/board identity to consumer observations.

- Confirmed the native 1920x1080 post-call two-tile double-click discard with exact 4m server acknowledgement, independently of drawn-slot validation.

- Confirmed a native 1920x1080 two-tile double-click discard through the server; fixed module-CLI plan identity before controller dispatch and added a subprocess regression.

- Added explicit native double-click discards as one guarded controller action, with 80 ms spacing, inter-click window checks and matching server acknowledgement instead of a manual confirmation pause.

- Tested the complete manual discard session with closed stdin and cross-process file confirmation; made failures terminal and bound live selection to the visually inspected board token.

- Added a persistent manual Mahjong discard validation runner with unique file confirmation tickets, unchanged-board and freshness checks, and regression coverage for delayed visual confirmation.

- Verified native selection of the two-tile drawn slot after restoring live capture; documented expiry before discard confirmation and retained the remaining validation limits.

- Added separate 1920x1080 two-tile draw and post-call discard layouts from reviewed screenshots and manual click/server confirmations, preserving exact-context and forbidden-discard guards.

- Completed live validation of sparse Mahjong calibration recording at 1920x1080, including Pon and Riichi click evidence; documented transitional win frames and remaining two-tile layout gaps.

- Reduced passive Mahjong calibration screenshot storage by buffering animations and saving actionable checkpoints and fresh click evidence; measured 88.3% fewer PNG bytes on the existing recording and made size-limit shutdown clean.

- Reviewed passive 1920x1080 calibration evidence and documented actual coverage, missing click confirmations and the recording storage limitation.

- Validated passive calibration against live play and fixed stale timestamps when unchanged screenshots are recaptured.

- Added a passive local Mahjong Soul calibration recorder for client screenshots, player clicks and conservative server-event correlation, with bounded sessions and no automatic profile activation.

- Confirmed native Pon at 1920x1200 and mapped existing action-button rows while preserving exact offer guards.

- Added guarded viewport coordinate remapping and live-validated 1920x1200 fourteen-tile discard variants, with automatic size selection.

- Verified native fullscreen Tsumo with exact self-draw confirmation and added its own-turn offer layout.

- Verified native fullscreen single-choice closed kan and added its exact own-turn offer layout.

- Verified fullscreen Riichi natively through server acceptance; fixed generic discard lookup colliding with the Riichi hand profile.

- Verified native fullscreen added kan with exact Pon/fourth-tile matching and added its own-turn offer layout.

- Verified native fullscreen Chi menu opening and two-choice selection end to end through the shared controller.

- Verified native fullscreen Pon-only offers with their own exact-context layout.

- Calibrated fullscreen Riichi menu and discard selection, with server acceptance verified after manual final confirmation; full native acceptance retest remains outstanding.

- Verified native fullscreen Ron with exact winning-tile confirmation and added its Ron-only offer layout.

- Verified native fullscreen Pon in the combined Chi/Pon offer and added its exact-context layout.

- Mahjong Soul: add the verified fullscreen eight-tile post-call discard layout.

- Added and natively verified a fullscreen initial-dealer discard profile, keeping round-start and own-draw contexts distinct even at the same hand count.

- Added automatic selection of uniquely calibrated Mahjong Soul discard geometry by size, hand count and action context, including observed five-tile fullscreen layouts.

- Enforced Mahjong Soul post-call discard restrictions, including red-five equivalents and unknown-encoding rejection; verified native fullscreen Chi and the greyed-out forbidden discard UI.

- Verified native fullscreen open-kan delivery with exact source confirmation; added reusable open-kan offer variants and the fullscreen eight-tile draw layout.

- Verified native fullscreen Skip acknowledgement and added calibrated eleven-tile draw/post-call layouts, preserving their distinct final-slot positions.

- Added serialized Chi-menu opening and explicit visual-choice binding; verified fullscreen Chi menu/choice coordinates and committed reusable calibrated layouts.

- Added explicit Mahjong Soul client-size profile variants, physical geometry inspection, minimized-window rejection, and pre-input geometry rechecks; verified a native discard at 1920x1080 fullscreen.

- Added guarded single-choice added-kan input using exact Pon/offer multiset matching; verified the Steam upgrade button and replacement draw while preserving red-five identity checks.

- Added guarded single-choice open-kan input with exact own/source tile checks; verified the combined Pon/Kan UI and replacement draw through the live reader.

- Verified native Mahjong Soul Ron input through the shared controller, including exact own winning tile, discard-win type, final scores, and return to idle after acknowledgement.

- Added guarded win input requiring the exact winner, winning tile, and tsumo/ron type; verified the Steam Tsumo button and resulting scores, with Ron covered offline pending live calibration.

- Verified the shifted Chi button in a combined Mahjong Soul Chi/Pon offer; added regression coverage for offer-specific coordinates, single-offer profile rejection, and shared-controller overlap prevention.

- Added guarded single-choice concealed-kan input with exact own contributions and live event confirmation; verified the Steam Kan button, replacement draw, and additional dora indicator.

- Added staged Mahjong Soul riichi input with offered-discard and visual-selection checks, exact declaration matching, and server-acceptance confirmation; verified the Steam UI declaration and 1,000-point deposit.

- Added guarded Mahjong Soul Skip input confirmed by a connection/request-matched cancellation acknowledgement; verified a live Chi-offer skip and prevented delayed acknowledgements from clearing newer operations.

- Hardened Mahjong Soul Pon planning and confirmation to require the exact uncalled source discard, contributed red-five identities, and tile source seats.

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
