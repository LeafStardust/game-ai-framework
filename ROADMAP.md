# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative roadmap/handoff for the Balatro Red/White competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests/live games locally. **Do not run tests or live games from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Every focused pytest command must use `-q`.
- Preserve exact Balatro mechanics, public-state legality, boss rules, affordability, and hidden-information boundaries.
- Prefer canonical ownership over late wrappers/rescue layers.
- Bond/composition and Build Health are evidence/planning layers, not direct score/action authorities.
- Numerical tuning must not compensate for missing strategy semantics.
- Before Bond/strategy work, read `docs/balatro/BALATRO_STRATEGY_SYSTEM.md` and `docs/balatro/BALATRO_RELATIONSHIPS_MOTIFS.md`.
- Use scoped Conventional Commit messages.

# Objective

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

The Bond system matters only if the production agent can use it to make better run-winning decisions.

Canonical causal chain:

```text
public game state
→ literal Balatro mechanics
→ Bond evidence + semantic mechanics
→ coherent strategy candidate / commitment
→ bounded goals, construction, preservation, execution preferences
→ existing canonical D1/D2/D3/D4/D9/D11/D14 owner
→ final legal/survival-aware action
→ better run outcome
```

Passing isolated regressions is not enough. The production agent must convert local correctness into actual winning runs.

# Strategy authority contract

Development, realization, and commitment remain separate:

```text
Development = Bond R0–R5
Realization = DORMANT / PARTIAL / ACTIVE / MATURE
Commitment  = EXPLORATORY / FORMING / PINNED / ESTABLISHED / DOMINANT
```

## FORMING = construction authority only

FORMING may:
- expose a bounded strategy plan;
- emit `seek_feature:*`, `seek_component:*`, or equivalent construction goals;
- influence admitted acquisition/development choices.

FORMING may not merely by existing:
- protect components from replacement;
- dictate hand execution;
- impose held-card preservation;
- create fake pivot resistance;
- be internally promoted to PINNED.

## PINNED+ = preservation/execution authority

PINNED / ESTABLISHED / DOMINANT may additionally influence preservation/execution, but remain subordinate to:
- legality;
- deterministic or materially safer survival;
- affordability/economy;
- boss correctness;
- materially stronger projected alternatives.

# Three-Bond pilot — production integration GREEN

The deliberately small pilot remains the reference architecture for future catalogue work.

## Pilot A — Burnt / persistent hand-level development

Validated:
- real modeled `BurntJoker` hard-unlocks the Bond;
- `evaluate_bond_composition()` naturally forms `burnt_target_level` at FORMING authority;
- the real strategy plan reaches D1 without a test-injected candidate;
- first-discard strategy fit changes the final safe-equivalent D1 choice;
- the public persistent hand-level gain is later exploitable;
- deterministic survival overrides development greed.

Relevant tests:
- `test_balatro_d1_burnt_native_evidence.py`
- `test_balatro_d1_burnt_final_arbitration.py`
- `test_balatro_d1_burnt_controlled_sequence.py`

## Pilot B — Deck shaping / deck thinning

Validated:
- Erosion naturally forms a FORMING deck-thinning strategy;
- Trading Card deepens the same strategy and creates real Card Destruction ↔ Deck Thinning reinforcement;
- unrelated positive Bond development receives less/no equivalent transition value;
- final `JokerAcquisitionPolicy.decide()` changes under a controlled counterfactual;
- same-purchase self-synergy no longer masquerades as reinforcement of an established engine.

Relevant tests:
- `test_balatro_deck_thinning_strategy_transition.py`
- `test_balatro_deck_thinning_production_integration.py`

## Pilot C — Held-card / Steel preservation

Validated:
- Baron alone naturally yields the intended FORMING `baron_mime_steel` candidate;
- Baron + Mime naturally graduates the real composition to PINNED+;
- no fake injected strategy candidate is required;
- real `StrategyAwareLiveHandActionPolicy` preserves the held King in a safe-equivalent choice only after PINNED authority exists;
- deterministic survival still spends the King when required.

Relevant tests:
- `test_balatro_d1_pinned_held_card_preservation.py`
- `test_balatro_d1_pinned_held_card_final_action.py`
- `test_balatro_held_card_production_integration.py`

# P1–P4 status

- P1 natural production formation — GREEN
- P2 canonical consumer reachability for the pilot testbed — GREEN
- P3 controlled production counterfactuals — GREEN
- P4 telemetry / diagnosability — GREEN

The pilot architecture is locally valid. That does **not** imply game competence.

# Controlled live pilot result — FAILED COMPETENCE GATE

Three fixed-production 10-attempt Red Deck / White Stake batches were completed.

## Batch 1

Repository SHA: `4158851ea97aabc7fa9ea6f49c411523db949f14`

- wins: 0/10
- average ante: 2.100
- median ante: 1.000
- power-engine utilization: 0.245
- unused active engines: 0.000
- destructive pivots: 0.000
- illegal actions: 0.000

This exposed a D1 timeout defect: a successful shallow Joker-aware search could be discarded when a later deep search exhausted the wall-clock budget.

Retained fix:
- `7cbc13439c7ec0f047772dc01eb4b4626feeb47d` — preserve the deepest successfully completed D1 search on timeout.

## Batch 2

Repository SHA: `7cbc13439c7ec0f047772dc01eb4b4626feeb47d`

- wins: 0/10
- average ante: 3.100
- median ante: 3.000
- power-engine utilization: 0.437
- unused active engines: 0.000
- destructive pivots: 0.000
- illegal actions: 0.000

This was a material survival improvement but still 0/10.

Postmortem exposed a discard-beam bug: with normal `discard_width=1`, `_diverse_discard_beam()` selected the best one-card discard first and filled the entire beam, preventing 2–5 card recovery discards from entering that search stage.

Retained fix:
- `7ddf49542e652d9b2583568b693b0761a5e28097` — width one now means the best discard candidate overall, not a one-card discard by construction.

## Batch 3

Repository SHA: `7ddf49542e652d9b2583568b693b0761a5e28097`

- wins: 0/10
- average ante: 2.400
- median ante: 2.000
- power-engine utilization: 0.420
- unused active engines: 0.000
- destructive pivots: 0.000
- illegal actions: 0.000

Do not infer from this small sample that the discard-beam semantic fix is harmful; its structural bug is real and its focused regression is green. But the combined live result is decisive enough to stop open-ended repeated validation.

## Aggregate

- total controlled attempts: **30**
- wins: **0**
- illegal actions: 0 in every reported batch
- destructive pivots: 0 in every reported batch
- unused active engines: 0 in every reported batch

Conclusion: **Red/White competence is still structurally broken.**

The problem is broader than whether one Bond reaches one consumer. Do not ask the user for another repeated 10-run batch until a concrete run-level competence defect is identified and corrected offline.

Detailed evidence and audit scope: `docs/balatro/RED_WHITE_COMPETENCE_AUDIT.md`.

# Catalogue status — REQUIRED LATER, BLOCKED NOW

The remaining Bond catalogue still requires systematic redesign/refurbishment. The three-pilot subset is a proof architecture, not a replacement for the other Bonds.

Do **not** refurbish the remaining ~43 Bonds yet. First establish a viable Red/White production baseline so catalogue semantics are not built on top of a losing core agent.

When catalogue refurbishment resumes, review every Bond for:
- whether the Bond should exist;
- correct public contributors and literal mechanics;
- meaningful R0–R5 development;
- realization semantics;
- strategy formation/linking;
- FORMING vs PINNED+ authority;
- construction goals/prescriptions;
- correct D1/D2/D3/D4/D9/D11/D14 consumers;
- conflicts, synergies, and motifs;
- realistic reachability;
- whether the production agent can actually act on it rather than merely detect it.

# ACTIVE PHASE — OFFLINE RED/WHITE COMPETENCE AUDIT

No further live batch is currently authorized.

Audit the canonical owners that dominate White Stake survival as one run-level system.

## A. D1 — hand survival/search

Audit whether:
- candidate generation admits materially distinct play/discard recovery lines;
- shallow/deep expectimax values are comparable and free of horizon artifacts;
- pace semantics correctly use remaining score, hands, and discards;
- discard use values redraw opportunity rather than only retained visible structure;
- final-hand/final-discard behavior maximizes actual survival probability;
- timeout/fallback semantics preserve trustworthy completed evidence;
- normal search budgets spend time on decision-relevant branches instead of predictably timing out in deep horizons.

## B. D2 / shop economy — immediate scoring vs scaling

Audit whether:
- the agent buys enough immediate scoring power early enough to survive Antes 1–3;
- HOLD, BUY, REPLACE, REROLL, voucher, and pack decisions share coherent opportunity-cost semantics;
- speculative scaling cannot crowd out mandatory immediate scoring;
- replacement economics compare current contribution against admitted candidates correctly;
- Bond/strategy construction bonuses remain bounded and cannot rescue a weak raw purchase;
- insufficient-build states explicitly prioritize raw tempo over engine elegance.

## C. Run-level build progression

Audit whether the independent canonical owners collectively produce:

```text
early survival
→ first scoring engine
→ economy stabilization
→ scalable engine
→ boss-safe execution
```

The key question is not whether each owner is locally plausible. It is whether their combined incentives grow score fast enough before blind requirements outscale the build.

## D. Telemetry gap before next live batch

The current pilot postmortem still reports terminal `ante=None` in per-run summaries. Before the next live validation, durable diagnostics should expose enough state to classify:
- ante/blind of death;
- blind requirement and achieved score;
- money and shop purchases leading into the loss;
- joker set and immediate/scaling contribution before death;
- hands/discards spent in the terminal blind;
- whether the run died from insufficient build power or incorrect hand execution.

# EXACT NEXT ACTION

1. Treat the three-pilot local architecture as **GREEN but insufficient for competence**.
2. Treat the 30-run Red/White live gate as **FAILED: 0/30**.
3. **Do not run another repeated 10-attempt batch now.**
4. **Do not apply Tune G.**
5. **Do not begin the remaining ~43-Bond refurbishment yet.**
6. Perform the offline Red/White competence audit in `docs/balatro/RED_WHITE_COMPETENCE_AUDIT.md`.
7. Start with the earliest run-level owner defect that can explain repeated death: D1 survival/search and D2 early scoring/economy must be audited together rather than as isolated Bond consumers.
8. Add or improve durable death/build telemetry where the current logs cannot distinguish insufficient build power from incorrect hand execution.
9. Resume live validation only after a concrete run-level defect has a controlled production counterfactual and focused regression.
10. The next live batch must test a specific hypothesis; it must not be open-ended debugging.
11. After a viable Red/White baseline and useful pilot behavior are demonstrated, systematically refurbish the remaining Bond catalogue.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 — D1 survival expansion — COMPLETE
3. Phase 2 — simple shop survival — COMPLETE
4. Phase 3 — coherent build evidence — COMPLETE
5. Phase 4 — resource semantics — COMPLETE
6. Phase 5 — initial live validation — COMPLETE; exposed competence failure
7. Phase 6A — strategy authority contract — COMPLETE / GREEN
8. Phase 6B — three-pilot deterministic architecture proofs — COMPLETE / GREEN
9. Phase 6C — three-pilot production integration — COMPLETE / GREEN
10. Phase 6D — controlled live pilot validation — COMPLETE / FAILED COMPETENCE GATE (0/30)
11. Phase 6E — offline Red/White competence audit and run-level fixes — **ACTIVE**
12. Phase 6F — hypothesis-driven live revalidation — BLOCKED ON 6E
13. Phase 6G — full catalogue refurbishment/expansion — BLOCKED ON VIABLE RED/WHITE BASELINE
14. Phase 6H — broader numerical/action-quality tuning — BLOCKED

Future stake/deck progression remains blocked until Red/White competence passes.
