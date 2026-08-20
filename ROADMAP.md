# Roadmap

> The roadmap tracks active milestones, not release notes. Detailed implementation evidence belongs in tests, logs, commits, `CHANGELOG.md`, and release documentation.
>
> Balatro uses **one permanent agent and one permanent mechanics/state/execution stack**. Universal Balatro strategies are shared game knowledge. A replaceable **deck/stake cartridge** modifies effectiveness, feasibility, economy, and thresholds for the observed live run.
>
> Production observation is repository-owned, read-only Windows process memory. Production execution is the repository-owned first-party in-process bridge. Hidden future information remains excluded: no RNG-state/seed exploitation and no ordered future draw pile.

## Status

| Milestone | Status | Gate |
|---|---|---|
| v0.1–v0.9 Foundation + autonomous integration | Complete | — |
| **v1.0.0 Red Deck / White Stake competence** | **Complete** | Released 2026-08-20 |
| **v1.0.x Red/White calibration** | **In progress** | Build Health / realized-strength validation before Red Stake work |
| v1.1–v1.7 Red Deck stake progression | Next | Begins from Red Stake after Red/White calibration |
| Fresh-profile collection progression | In progress, non-blocking | May continue alongside stake progression |
| v2+ Additional decks | Not started | Begins after Red Deck progression |

## Completed milestones

| Version | Completed scope |
|---|---|
| v0.1 | Repository foundation, core abstractions and game runner |
| v0.2 | Configuration, logging, metrics and events |
| v0.3 | Agent architecture, decision pipeline and policy system |
| v0.4 | Evaluation framework and Balatro play/discard/risk heuristics |
| v0.5 | Softmax policy, configurable policy selection and reproducible seeds |
| v0.6 | Experiment runner, multi-episode evaluation, comparisons and metrics |
| v0.7 | Balatro cards, hands, scoring, Jokers, consumables and card modifiers |
| v0.8 | Search/planning, probability/EV analysis, blind-clear paths, stakes and deck architecture |
| v0.9 | Autonomous real-game observe → decide → execute → verify → log → restart/stop loop; authoritative live state, injected execution, stochastic projection, 150/150 Joker validation and Boss Blind coverage |
| **v1.0.0** | **Red Deck / White Stake competence: universal strategy tree, coherent build planning, strategy-aware D1–D14 decisions, bounded live search, economy/shop competence, boss handling, ordering, diagnostics, and autonomous unseeded win validation** |

---

## v1.0.0 — Red Deck / White Stake Competence — COMPLETE

Released: **2026-08-20**

Goal achieved: the permanent Balatro agent can play Red Deck / White Stake autonomously using coherent run-level strategy rather than isolated local-value decisions.

### Completed release scope

- [x] Make blind-clear probability and feasible remaining clear paths the dominant D1 objective while preserving hand efficiency and unused-hand economy.
- [x] Preserve strategically useful held structure, including Steel cards and Blue Seals, when survival-equivalent lines permit it.
- [x] Maintain coherent build intent across hand play, discards, Joker acquisition/replacement, consumables, Planets, packs, rerolls, vouchers, boosters, and blind skips.
- [x] Model anti-synergies and explicit conflicts without treating every competing strategy as mechanically banned.
- [x] Complete the universal strategy-tree migration. Sections 1–12 are production-owned, with 136 definition-backed topology nodes and leaf-only actionable ranking.
- [x] Separate portable universal Joker value from route-bound strategy evidence and dynamic off-path pressure.
- [x] Enforce exclusive dominant-strategy prescription from Ante 6 while retaining secondary strategies for diagnostics.
- [x] Complete Gold/Silver/Bronze/Banned and conditional-relationship audits across the production strategy forest.
- [x] Integrate useful support components into compatible routes rather than creating weak standalone strategies.
- [x] Keep Joker editions as portable value while preserving explicit strategy/mechanical conflicts.
- [x] Protect Negative Jokers from ordinary sales, replacement, and unrelated sacrifice; retain explicit measured-harm, active-Dagger, and Verdant Leaf exceptions.
- [x] Add autonomous Joker-board ordering for Blueprint/Brainstorm copy targeting, additive-before-XMult scoring, and Ceremonial Dagger sacrifice planning.
- [x] Add authoritative pre-play hand ordering for first-card effects such as Hanging Chad and Photograph.
- [x] Wire Cerulean Bell forced-card handling and Verdant Leaf emergency sales through authoritative injected actions.
- [x] Bound Boss-Blind, late-Ante, Joker-order, and complete D1 search by interactive node/time budgets.
- [x] Add paid-reroll stop losses, survival reserves, Gold Card/Gold Seal economy protection, and Bull/Bootstraps cash-spending opportunity cost.
- [x] Keep ordinary undiscovered-item preference bounded to a one-ULP tie-break so collection interest cannot override competence.
- [x] Add strategy/build diagnostics to the live monitor and structured run logs.
- [x] Preserve normal Steam progression and hidden-information restrictions.

### Acceptance evidence

- [x] Full deterministic repository suite passed after the complete strategy-tree and Negative-retention migration: **1,787 tests on 2026-08-18**.
- [x] Completed an **unseeded, fully autonomous Red Deck / White Stake win** on 2026-08-18 against Amber Acorn with no manual gameplay input after activation and normal Steam progression preserved.
- [x] Fixed the `won=true` / `ROUND_EVAL` terminal-detection gap exposed by that winning run and covered the fix deterministically.
- [x] Fixed the final Section 1 Straight contract so **Superposition remains Bronze support** while Straight remains a standalone leaf.

The additional live confirmation of immediate automatic OFF after a winning `ROUND_EVAL` transition remains useful regression validation, but it is no longer a blocker for the v1.0.0 competence release because the terminal fix is deterministic-test covered and the autonomous win itself is already authoritative.

---

## v1.0.x — Red/White calibration — IN PROGRESS

The initial Red/White release demonstrated competence, but repeated five-run calibration exposed a higher-level decision gap: the agent can own several individually useful Jokers and accumulate strong strategy evidence while the **realized build remains inactive, incoherent, or too slow to scale**.

The implementation contract is documented in [`docs/balatro/BUILD_HEALTH_AND_REALIZED_STRENGTH.md`](docs/balatro/BUILD_HEALTH_AND_REALIZED_STRENGTH.md).

### Build Health / realized-strength work

- [x] Add a pure `BuildHealth` evaluator with auditable Survival, Immediate Scoring, Scaling, Coherence, and Runway dimensions.
- [x] Distinguish catalogue relationship from realized engine state (`NOT_OWNED`, `OWNED_INACTIVE`, `ACTIVATED_WEAK`, `ACTIVATED_HEALTHY`, `MATURE`).
- [x] Cover an initial engine set: Blue/Hologram growth, Burnt Joker, Castle, Green Joker, Red Card, Runner, and Bull/Bootstraps.
- [ ] Replace early-game "positive scorer" admission with next-blind **survival adequacy** using the existing whole-blind clear-probability model. The legacy positive-scorer override is retired and Build Health now owns survival admission, but the shop-time health adapter still uses a bounded public-state scoring-capacity estimate rather than invoking the full D1 expectimax planner.
- [x] Detect midgame scaling deficits when present strength can clear current blinds but is unlikely to keep pace with the next one to two Antes.
- [x] Make shop buy/replace/reroll decisions sensitive to Build Health delta rather than Joker count or isolated item value alone.
- [x] Keep committed Gold/Silver structure protected while still allowing immediate stronger same-route upgrades.
- [x] Make pivot decisions compare realized current strength, transition cost, required buildup, and remaining runway; theoretical ceiling alone is insufficient.
- [x] Add bounded short-horizon multi-action planning for complementary shop pairs and activation sequences.
- [x] Expose Build Health and inactive-engine/scaling-deficit warnings in the live monitor and structured logs.
- [x] Add deterministic regressions before each behavior change. **Regression files are present but have not yet been executed on the current branch head.**
- [ ] Run a fresh unchanged-HEAD five-run Red/White validation batch only after the complete layer is green.

### Calibration gate before Red Stake

Do not begin Red/Red `1.1.0` implementation until:

- [ ] the full Balatro deterministic suite is green;
- [ ] Build Health diagnostics are stable and auditable;
- [ ] repeated five-run losses no longer show obvious "full board but non-functioning build" failures;
- [ ] at least one fresh unchanged-HEAD Red/White batch contains an Ante-8 clear without a repeated release-blocking decision defect.

---

## Fresh-profile collection progression — IN PROGRESS, NON-BLOCKING

Collection-first mode is intentionally separate from ordinary competence. It may sacrifice current-run strength for permanent profile progress and therefore does **not** define the v1.0.0 Red/White competence gate.

Already implemented:

- [x] Explicit collection-first operating mode with hard `COLLECTION_CRITICAL` action priority.
- [x] Guaranteed legal/affordable acquisition of explicitly undiscovered visible Jokers, consumables, Vouchers, boosters, and pack choices.
- [x] Capacity-aware Joker replacement while excluding Eternal and Negative incumbents from collection-capacity sales.
- [x] Hit the Road and Stuntman collection campaigns may intentionally sacrifice blind-clear probability in collection-first mode.
- [x] Preserve the normal automatic stop at the first Ante-8 win while allowing a newly started agent to resume a manually continued Endless run.

Remaining collection work:

- [ ] Expose authoritative unlocked/discovered state for every relevant collection entry while preserving unknown state as unknown.
- [ ] Rank unopened boosters by expected missing-collection opportunity.
- [ ] Add a declarative unlock-condition registry rather than hard-coding conditions into the permanent agent.
- [ ] Model repeatable Voucher prerequisites and account-wide counters.
- [ ] Cover deterministic/collection targets including Golden Ticket, Arrowhead, Merry Andy, Seeing Double, Satellite, and Astronomer.
- [ ] Extend Soul-opportunity diagnostics for undiscovered Legendary Jokers without pretending the random Legendary outcome is controllable.
- [ ] Add campaign progress/impossibility diagnostics and deterministic regressions.
- [ ] Confirm ordinary competence behavior remains unchanged when collection-first mode is disabled.

---

## v1.1–v1.7 — Red Deck stake progression

| Version | Stake | New adaptation focus |
|---|---|---|
| **v1.1** | **Red** | **No Small Blind reward money** |
| v1.2 | Green | Green Stake score scaling |
| v1.3 | Black | Eternal Joker strategy |
| v1.4 | Blue | Reduced-discard strategy |
| v1.5 | Purple | Purple Stake score scaling |
| v1.6 | Orange | Perishable Joker strategy |
| v1.7 | Gold | Rental Joker strategy and Red Deck all-stakes validation |

Each stake milestone modifies the effectiveness, feasibility, and economy of the universal Balatro strategies as required by that stake, retunes the Red Deck cartridge only when necessary, and requires successful unseeded live validation. Stake milestones must not duplicate or redefine the universal strategy tree.

### Higher-stake economy and hand-efficiency requirement

- [ ] Explicitly prioritize clearing blinds with as few hands as safely possible to maximize unused-hand cash-out.
- [ ] Pursue >2× blind-target finishes for extra-cash benefit when the line is strategically safe and EV-positive.

---

## v2+ — Additional decks

Planned deck order after Red Deck completion:

1. **Blue Deck — v2.x**
2. **Yellow Deck — v3.x**
3. **Green Deck — v4.x**
4. **Black Deck — v5.x**

Additional-deck cartridges reuse the same universal Balatro strategy tree and supply only deck/stake-specific strategy modifiers and thresholds.
