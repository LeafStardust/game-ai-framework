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

Passing isolated Bond regressions is not enough. A pilot must naturally form in production state, reach the consumer that owns the decision, change the final action for the correct reason, remain subordinate to survival/economy, and be diagnosable in live traces.

# Why the current reengineering exists

Phase 5 semantic validation reached 74/74 green, but baseline and Tunes A–F repeatedly produced **0/10 wins**. Local semantic correctness therefore did not equal game competence.

The response is **not** catalogue-wide polishing. The response is to reengineer and validate a deliberately small three-strategy pilot, prove that the agent can actually build and use those strategies, then test whether this improves real games.

# THREE-BOND PILOT — AUTHORITATIVE SCOPE

Only these three strategic verticals drive current work.

## Pilot A — Burnt / persistent hand-level development

Must prove that the agent can:
- recognize Burnt as persistent development;
- use a safe first discard to develop the intended hand;
- value compatible target-hand support;
- exploit the persistent hand level later;
- stop development greed when survival requires scoring now.

## Pilot B — Deck shaping / deck thinning

Must prove that the agent can:
- recognize Erosion/Trading Card-style thinning as a coherent construction direction;
- value compatible thinning/destruction acquisitions for strategy reasons;
- prefer compatible construction over unrelated Bond collection when the canonical owner is otherwise near-indifferent;
- carry thinning goals into existing deck-removal/transform consumers where supported;
- never sacrifice immediate survival/economy for speculative thinning.

## Pilot C — Held-card / Steel-style persistent-card preservation

Must prove that the agent can:
- recognize held-card payoff/retrigger mechanics before a complete Baron/Mime/Steel package exists;
- stay construction-only while FORMING;
- graduate naturally to PINNED+ when the public engine is coherent enough;
- preserve relevant Kings/Steel/held-engine cards among safe-equivalent D1 choices;
- value compatible construction pieces through canonical acquisition consumers;
- spend engine cards when survival or a materially stronger line requires it.

The pilots intentionally test different authority paths:
- Burnt: persistent development + D1 execution.
- Deck thinning: construction/acquisition authority.
- Held-card/Steel: commitment graduation + preservation authority.

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

# Three-pilot production integration — GREEN

The three strategic pilots have now cleared the required production-path gates using real modeled state and canonical consumers.

## Pilot A Burnt — GREEN THROUGH REAL PRODUCTION D1

Validated locally:
- real modeled `BurntJoker` hard-unlocks the Bond;
- `evaluate_bond_composition()` naturally forms `burnt_target_level` at FORMING authority;
- the real strategy plan reaches D1 without a test-injected candidate;
- first-discard strategy fit changes the final safe-equivalent D1 choice;
- the public persistent hand-level gain is later exploitable by the canonical scorer/policy;
- deterministic survival overrides further development greed.

Relevant tests:
- `test_balatro_d1_burnt_native_evidence.py`
- `test_balatro_d1_burnt_final_arbitration.py`
- `test_balatro_d1_burnt_controlled_sequence.py`

## Pilot B Deck Thinning — GREEN THROUGH FINAL D2 BUY/HOLD

Validated locally:
- Erosion naturally forms a FORMING deck-thinning strategy;
- Trading Card deepens the same strategy and creates real Card Destruction ↔ Deck Thinning reinforcement;
- unrelated positive Bond development receives less/no equivalent transition value;
- final `JokerAcquisitionPolicy.decide()` changes under a controlled counterfactual with identical candidate/economics and only the existing Erosion strategy fact changed;
- D2 no longer rewards same-purchase self-synergy between two newly created Bond labels as if it reinforced an established engine.

Relevant tests:
- `test_balatro_deck_thinning_strategy_transition.py`
- `test_balatro_deck_thinning_production_integration.py`

## Pilot C Held-card / Steel — GREEN THROUGH REAL PRODUCTION D1

Validated locally:
- Baron alone naturally yields the intended FORMING `baron_mime_steel` candidate;
- Baron + Mime naturally graduates the real composition to PINNED+;
- no fake injected strategy candidate is required;
- real `StrategyAwareLiveHandActionPolicy` preserves the held King in a safe-equivalent discard choice only after PINNED authority exists;
- deterministic survival still spends the King when required.

Relevant tests:
- `test_balatro_d1_pinned_held_card_preservation.py`
- `test_balatro_d1_pinned_held_card_final_action.py`
- `test_balatro_held_card_production_integration.py`

## Supporting contradiction / overlap fixes — GREEN

Supporting architecture defects uncovered while proving the pilots remain retained:
- Burnt × No-Discard conflict suppresses conflicting structural reward;
- Vampire/Midas defining-core direction corrected;
- newly appearing synergies only receive transition reward when they reinforce at least one already-established axis.

These are support for the three-pilot architecture, not new pilot scope.

# P1–P4 status

## P1 — natural production formation — GREEN

All three pilots now form from real public state with real modeled components and appropriate commitment.

## P2 — canonical consumer reachability — GREEN FOR PILOT TESTBED

The production integration target was to prove the distinct authority path represented by each pilot:
- Burnt reaches D1 execution/development authority;
- Deck Thinning reaches final D2 acquisition authority;
- Held-card/Steel reaches D1 preservation authority after real PINNED graduation.

Do **not** expand into every possible D3/D4/D9/D14 consumer before live validation. Missing downstream behavior should now be discovered from live traces when an actual pilot opportunity reaches that owner. This prevents another catalogue/consumer-completeness detour.

## P3 — controlled production counterfactuals — GREEN

For each pilot, the relevant public strategy fact changes the canonical final decision for the intended reason and the effect disappears or weakens when that fact is removed.

## P4 — telemetry / diagnosability — GREEN

Canonical Bond diagnostics now expose:
- relevant Bond developments and contributors;
- strategy candidates, commitment, confidence, strength, and pinned identity;
- motifs and present/missing components;
- active `strategy_plan`;
- core sources;
- Bond goals and next ranks;
- missing features/components;
- prescriptions;
- plan completion.

The acting D1/D2 policies already emit rationale for strategy/transition effects, allowing live failures to be classified at the first wrong stage:
- `MECHANIC_MODEL`
- `BOND_REPRESENTATION`
- `ROLE_DESCRIPTOR`
- `SEMANTIC_LINKING`
- `STRATEGY_FORMATION`
- `GOAL_PRESCRIPTION`
- `PROJECTED_TRANSITION`
- `CONSUMER_VALUATION`
- `FINAL_ARBITRATION`

Relevant test:
- `test_balatro_pilot_strategy_diagnostics.py`

# Catalogue detour — RETAIN BUT DEFER

Earlier work accidentally expanded into the 46-Bond catalogue. Legitimate fixes already committed should remain unless they regress behavior, including hard-unlock, authority-boundary, overlap, and Batch-5 reachability fixes.

From this point:
- no further catalogue-wide audit;
- no catalogue-wide threshold sweep;
- no broad motif/relationship expansion;
- no new Bond families;
- no catalogue-completeness tuning.

Full catalogue refurbishment remains blocked until the three-pilot system demonstrates production usefulness and live improvement.

# ACTIVE PHASE — CONTROLLED LIVE PILOT VALIDATION

The production integration gate is complete. The next task is to test whether the three-Bond architecture improves actual Red Deck / White Stake play.

## Live batch protocol

1. Use the current production agent exactly as committed after P1–P4.
2. **Do not introduce Tune G first.**
3. Run a small controlled Red Deck / White Stake batch.
4. Retain the normal live telemetry/logging path.
5. For each run, record:
   - win/loss and ante reached;
   - whether Burnt, Deck Thinning, or Held-card/Steel opportunities appeared;
   - whether the relevant strategy was recognized;
   - whether construction/preservation/execution behavior followed the plan;
   - whether pilot behavior caused an avoidable death or missed acquisition;
   - the first causal failure category if something went wrong.
6. Diagnose semantics/authority before changing numbers.
7. Fix the first incorrect ownership layer only.
8. Repeat the same controlled batch after causal fixes.

## Live success criteria

Success is **not** that every run contains a pilot and not necessarily an immediate high win rate.

The pilot passes when:
- actual pilot opportunities are recognized reliably;
- the agent pursues/preserves/executes them coherently;
- strategy behavior remains subordinate to survival and economy;
- bad decisions can be traced to a specific first-wrong stage;
- the agent begins converting at least some runs into wins instead of remaining structurally stuck at 0/10.

If the batch remains 0/10, use the traces to identify the dominant causal failure. Do not respond with blind threshold tuning.

# EXACT NEXT ACTION

1. Treat Phase 6C three-pilot production integration as **COMPLETE / GREEN**.
2. Do not perform more catalogue or generic consumer audits before live evidence.
3. Start the first controlled Red Deck / White Stake pilot batch using the current production stack.
4. Do not apply Tune G before this baseline pilot batch.
5. Collect the existing Bond/build diagnostics plus action rationales.
6. After the batch, inspect the first causal failure in each bad run.
7. Group repeated failures by ownership category and fix the earliest incorrect layer.
8. Re-run the same batch after those fixes.
9. Only after live pilot usefulness is demonstrated should the architecture be generalized to the remaining Bond catalogue.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 — D1 survival expansion — COMPLETE
3. Phase 2 — simple shop survival — COMPLETE
4. Phase 3 — coherent build evidence — COMPLETE
5. Phase 4 — resource semantics — COMPLETE
6. Phase 5 — initial live validation — COMPLETE; exposed 0/10 competence failure
7. Phase 6A — strategy authority contract — COMPLETE / GREEN
8. Phase 6B — three-pilot deterministic architecture proofs — COMPLETE / GREEN
9. Phase 6C — three-pilot production integration — COMPLETE / GREEN
10. Phase 6D — controlled live pilot validation — **ACTIVE**
11. Phase 6E — pilot-driven semantic fixes / repeated live validation — BLOCKED ON 6D EVIDENCE
12. Phase 6F — full catalogue refurbishment/expansion — BLOCKED ON LIVE PILOT SUCCESS
13. Phase 6G — broader numerical/action-quality tuning — BLOCKED

Future stake/deck progression remains blocked until Red/White competence passes.
