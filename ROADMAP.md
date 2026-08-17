# Roadmap

> The roadmap tracks active milestones, not release notes. Completed work is summarized; detailed implementation evidence belongs in tests, logs, commits and release documentation.
>
> Balatro uses **one permanent agent and one permanent mechanics/state/execution stack**. Universal Balatro strategies are shared game knowledge. A replaceable **deck/stake cartridge** only modifies the effectiveness, feasibility, economy, and thresholds of those strategies for the observed live run.
>
> Production observation is repository-owned, read-only Windows process memory. Production execution is the repository-owned first-party in-process bridge. Hidden future information remains excluded: no RNG-state/seed exploitation and no ordered future draw pile.

## Status

| Milestone | Status | Gate |
|---|---|---|
| v0.1–v0.9 Foundation + autonomous integration | Complete | — |
| **v1.0 Red Deck / White Stake competence** | **In progress** | Universal strategy scoring system + final acceptance |
| v1.1–v1.7 Red Deck stake progression | Not started | Begins after v1.0 |
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
| v0.9 | Autonomous real-game loop: observe -> decide -> execute -> verify -> log -> restart/stop; authoritative live state, injected execution, stochastic projection, 150/150 Joker validation and Boss Blind coverage |

---

## v1.0.0 — Red Deck / White Stake Competence — IN PROGRESS

Goal: turn the completed autonomous stack into a **deliberate, repeatable Red Deck / White Stake player** that discovers and reinforces coherent strategies from the current run instead of relying on isolated local-value purchases.

### 1.0A — Blind survival and hand efficiency

- [x] Make clear probability and a feasible remaining clear path the dominant D1 objective, with pace discipline across remaining hands/discards.
- [x] Among similarly safe clear lines, prefer fewer hands and capture unused-hand economy.
- [x] Preserve future hand value explicitly, including retained structure, Steel cards, Blue Seals and other build-relevant held cards.
- [x] Tune discard/recovery behavior around the active clear path rather than isolated hand value.

### 1.0B — Initial build coherence

- [x] Maintain persistent public build/archetype intent and apply B3–B7 reasoning consistently across D1–D14.
- [x] Make Joker, hand, discard, Planet, consumable and pack decisions reinforce the active build.
- [x] Detect and penalize anti-synergies/conflicts, including a Ride the Bus + Business Card regression case.
- [x] Give useful Negative Jokers explicit slot-free acquisition value.
- [x] Log meaningful build-intent changes and detected conflicts.

> 1.0B established the first build-intent layer. 1.0F replaces its loose archetype inference with explicit universal strategy playbooks and current-state strategy scoring while preserving useful public-state/build profiling work.

### 1.0C — Planet and consumable competence

- [x] Value Planets by expected future hand frequency, marginal level gain, build synergy and feasibility; suppress speculative upgrades such as unsupported early Straight Flush/Neptune lines.
- [x] Align consumable acquisition with use timing and finalize held-consumable use/target thresholds.

> The universal strategy system in 1.0F becomes the authoritative strategic relevance layer: Tarot/Spectral effects may seed strategies early, unopened consumables do not count as achieved strategy evidence, and paid Planet acquisition normally requires real poker-hand evidence. A used Planet contributes small persistent evidence through the resulting hand-level investment.

### 1.0D — Shop, pack and economy competence

- [x] Calibrate D3/D8/D9/D10/D11 acquisition, reroll and pack thresholds around survival, build value and economy; keep D12 threshold-free and calibrate D14 shared resource valuation on the same scale.
- [x] Model run-wide voucher value plus reserve/interest breakpoints, including observable voucher-modified caps or thresholds.
- [x] Keep undiscovered-item acquisition bias bounded so it never overrides survival or build coherence.

### 1.0E — Blind skip/tag strategy

- [x] Evaluate skip/tag EV against blind reward, lost shop/economy opportunity, build strength, ante and boss preparation.
- [x] Validate skip/tag behavior with real-run examples before freezing thresholds.

### 1.0F — Universal strategy playbooks and scoring

- [x] Define one flat universal Balatro strategy pool with strategy-owned exact Gold/Silver/Bronze/banned component mappings, Neutral as the unlisted default, generated inverse component lookup, and deck/stake cartridges limited to strategy effectiveness/feasibility modifiers.
- [x] Split the design contract from the concrete strategy catalogues for poker-hand, mechanic, and niche/synergy strategies.
- [ ] Audit and finalize the concrete strategy catalogue against actual repository components: exact Joker tiers/conflicts, Tarot/Spectral/support relationships, entry evidence, maturity evidence, and natural pivots. No vague categories such as "generic Mult" are valid implementation data.
- [ ] Encode universal `StrategyDefinition` data and generate the inverse `component -> strategy/relationship` index without editing all 150 Joker classes.
- [ ] Implement tunable strategy evidence weights with the intended ordering/sign: Gold > Silver > Bronze > Neutral > Banned; begin with approximately `+5 / +3 / +1 / 0 / -8` and tune through deterministic/live validation.
- [ ] Recompute every strategy from **current public build state**, not historical ownership. Buying/selling Jokers and persistent deck mutations must add/remove their evidence immediately.
- [ ] Keep unopened/held consumables out of achieved strategy evidence; value them by expected effect, then rescore after use. Used Planets must provide small persistent evidence through hand-level investment.
- [ ] Keep **strategy score** separate from **candidate purchase/retention score**. At a zero-evidence start, strategy adjustment is approximately zero and ordinary/meta/context value drives early purchases.
- [ ] Compute candidate strategic alignment from the current positive relevance of supported strategies and the candidate's Gold/Silver/Bronze/banned relationships; prevent negative-score × negative-conflict arithmetic from creating accidental positive bonuses.
- [ ] Implement Ante-scaled strategy pressure: weak exploration in Antes 1–2, progressively stronger convergence in Antes 3–5, and strong specialization from Ante 6 onward around one dominant strategy plus at most two relevant strategies.
- [ ] Implement sell/replace behavior from the same playbook matrix: banned/conflicting Jokers lower strategy coherence and retention value, but are not automatically sold when doing so would endanger survival; direct functional contradictions may receive exceptional urgency.
- [ ] Keep early Tarot/Spectral strategy-seeding available while requiring real poker-hand evidence before meaningful paid Planet investment.
- [ ] Add Red Deck / White Stake cartridge modifiers over the universal strategies without redefining their component relationships.
- [ ] Integrate dominant/relevant strategy state through D1–D14 so acquisition, selling, packs, rerolls, deck shaping, consumables, Planets, and preferred hand pursuit reinforce coherent strategies while guaranteed blind survival remains superior.
- [ ] Log current strategy scores, score contributors, candidate strategy adjustment, Ante pressure, dominant/relevant ranking changes, pivots, conflicts, sell/replacement rationale, and final decision decomposition in authoritative run logs.
- [ ] Add deterministic regressions covering zero-evidence early buying, evidence creation on Joker purchase, evidence removal on sale, Planet-use investment, conflict penalties, direct contradictions, Ante pressure, dominant/relevant selection, pivots, consumables, packs, and D1 hand preference.
- [ ] Run specialized live validation after deterministic strategy behavior is stable.

### 1.0G — Final freeze and acceptance gate

The earlier Red/White threshold freeze was performed against the pre-playbook policy and is therefore **historical/provisional**, not the final v1.0 freeze.

- [ ] Run the full test suite only after 1.0F is complete; re-tune only where strategy integration proves it necessary, then freeze the final Red/White D1–D14 thresholds and strategy evidence/pressure/effectiveness parameters.
- [ ] Complete **one unseeded Red Deck / White Stake win** with no manual gameplay input after activation, normal Steam progression preserved, a complete replayable authoritative run log with decision/build/strategy rationales, and automatic OFF after the win.

---

## v1.1–v1.7 — Red Deck stake progression

| Version | Stake | New adaptation focus |
|---|---|---|
| v1.1 | Red | No Small Blind reward money |
| v1.2 | Green | Green Stake score scaling |
| v1.3 | Black | Eternal Joker strategy |
| v1.4 | Blue | Reduced-discard strategy |
| v1.5 | Purple | Purple Stake score scaling |
| v1.6 | Orange | Perishable Joker strategy |
| v1.7 | Gold | Rental Joker strategy and Red Deck all-stakes validation |

Each stake milestone modifies the effectiveness/feasibility/economy of the universal Balatro strategies as required by that stake, retunes the Red Deck cartridge when necessary, and requires one successful unseeded run. Stake milestones should not duplicate or redefine the universal strategy catalogue.

### Higher-stake economy and hand-efficiency requirement

- [ ] In higher-stake runs, explicitly prioritize clearing blinds with as few hands as safely possible to maximize unused-hand cash-out, and pursue >2× blind-target finishes for their extra-cash benefit when the line is strategically safe and EV-positive.

## v2+ — Additional decks

Planned deck order after Red Deck completion:

1. **Blue Deck — v2.x**
2. **Yellow Deck — v3.x**
3. **Green Deck — v4.x**
4. **Black Deck — v5.x**

Additional-deck cartridges reuse the same universal Balatro strategy catalogue and supply only deck/stake-specific strategy modifiers and thresholds.
