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

# Deterministic architecture proofs

## Pilot A Burnt — GREEN

Validated:
- Burnt recognition and target-hand evidence;
- first-discard valuation;
- final D1 arbitration counterfactual;
- persistent hand-level gain;
- later exploitation;
- survival override.

Relevant tests:
- `test_balatro_d1_burnt_native_evidence.py`
- `test_balatro_d1_burnt_final_arbitration.py`
- `test_balatro_d1_burnt_controlled_sequence.py`

## Pilot B deck thinning — GREEN AT TRANSITION HELPER

Validated:
- Erosion naturally forms a low-authority deck-thinning direction;
- Trading Card deepens it;
- Card Destruction ↔ Deck Thinning synergy is recognized;
- unrelated positive Bond development receives less/no equivalent D2 transition value.

Relevant test:
- `test_balatro_deck_thinning_strategy_transition.py`

Limitation: this proves `_bond_transition_bonus`, not yet final production `JokerAcquisitionPolicy.decide()` BUY/HOLD authority.

## Pilot C held-card / Steel — GREEN THROUGH REAL PRODUCTION D1

Validated locally:
- manually injected consumer-boundary proof: FORMING does not preserve, PINNED does, survival overrides;
- real production composition now proves natural formation and commitment using actual Jokers/state;
- Baron-only yields the intended FORMING candidate;
- Baron + Mime naturally yields PINNED+ held-card authority;
- real `StrategyAwareLiveHandActionPolicy` preserves the King in a safe-equivalent discard choice;
- deterministic survival still spends the King when required.

Relevant tests:
- `test_balatro_d1_pinned_held_card_preservation.py`
- `test_balatro_d1_pinned_held_card_final_action.py`
- `test_balatro_held_card_production_integration.py`

Pilot C P1 and the core D1 portion of P2/P3 are therefore GREEN. D2/D4/D9/D14 reachability still needs audit before live testing.

## Supporting contradiction proof — GREEN

Burnt × No-Discard proves incompatible axes cannot both collect positive structural reward indiscriminately. This is supporting architecture evidence, not a fourth pilot.

# Catalogue detour — RETAIN BUT DEFER

Earlier work accidentally expanded into the 46-Bond catalogue. Legitimate fixes already committed should remain unless they regress behavior, including hard-unlock, authority-boundary, overlap, and Batch-5 reachability fixes.

But from this point:
- no further catalogue-wide audit;
- no catalogue-wide threshold sweep;
- no broad motif/relationship expansion;
- no new Bond families;
- no catalogue-completeness tuning.

Full catalogue refurbishment remains blocked until the three-pilot system demonstrates production usefulness and live improvement.

# ACTIVE PHASE — THREE-PILOT PRODUCTION INTEGRATION

Each pilot must clear four gates.

## P1 — natural production formation

Use real Jokers/cards/state fields and prove:
- intended Bond evidence exists;
- intended StrategyCandidate forms naturally;
- commitment is appropriate;
- removing the public mechanic removes/weakens the strategy;
- no fake injected candidate is required.

Status:
- Pilot C: GREEN.
- Pilot B: formation GREEN from existing Erosion proof; final D2 reachability active.
- Pilot A: deterministic D1 proof exists; full production-stack audit still required.

## P2 — canonical consumer reachability

### Pilot A Burnt
Required consumers:
- D1 discard/execution;
- D2 relevant Joker construction/replacement where applicable;
- D3/D4/D9 target-hand development only where those canonical owners already support semantic goals.

### Pilot B deck thinning
Required consumers:
- D2 Joker acquisition/replacement;
- existing D4/D9 deck-removal/deck-transform owners where admitted;
- D14 must not erase child-policy preference.

### Pilot C held-card / Steel
Required consumers:
- D1 preservation/execution — GREEN;
- D2 compatible Joker construction/replacement;
- existing D4/D9 Steel/Seal/card-shaping owners where admitted;
- D14 must preserve child-policy authority.

Do not create another final arbiter. Missing strategy information must feed the existing owner.

## P3 — controlled production counterfactual

For each pilot:

```text
same legal candidates + same economics/survival context
remove relevant strategy mechanic → ordinary final decision
restore relevant strategy mechanic → strategically correct final decision
```

The action difference must disappear when the strategy fact disappears.

## P4 — telemetry / diagnosability

Before live games, traces must expose enough to classify failures at the first wrong stage:
- `MECHANIC_MODEL`
- `BOND_REPRESENTATION`
- `ROLE_DESCRIPTOR`
- `SEMANTIC_LINKING`
- `STRATEGY_FORMATION`
- `GOAL_PRESCRIPTION`
- `PROJECTED_TRANSITION`
- `CONSUMER_VALUATION`
- `FINAL_ARBITRATION`

Telemetry should show relevant pilot Bonds, candidate/commitment, goals, and the transition/preservation rationale used by the acting consumer.

# CONTROLLED LIVE PILOT VALIDATION — BLOCKED UNTIL P1–P4 GREEN

Once production integration is green:
1. run a small controlled Red Deck / White Stake batch using the current production agent;
2. do not introduce Tune G first;
3. collect traces for actual pilot opportunities;
4. measure wins and strategy recognition/pursuit/preservation/execution;
5. classify the first causal failure in each bad run;
6. fix semantics/authority before numbers;
7. repeat the same controlled batch.

Success is not "every run contains a pilot." Success is:
- when a pilot opportunity appears, the agent uses it coherently;
- pilot behavior does not cause avoidable deaths;
- the system begins converting some runs into wins instead of remaining 0/10 because it cannot construct or maintain an engine.

# EXACT NEXT ACTION

1. Pilot C real held-card production D1 integration is GREEN; do not reopen it without new evidence.
2. Continue **Pilot B Deck Thinning** at the first unproved production boundary.
3. Prove real Erosion strategy evidence reaches final `JokerAcquisitionPolicy.decide()` authority for Trading Card, not merely `_bond_transition_bonus`.
4. Use a controlled BUY/HOLD counterfactual with identical candidate/economics and only the existing Erosion strategy fact changed.
5. If D2 does not change for the intended reason, fix the first owning layer; do not tune arbitrary thresholds to hide a missing semantic transition.
6. Then audit Pilot B D4/D9 and D14 reachability only where those existing owners can act on thinning.
7. Perform the equivalent production-stack audit for Burnt.
8. Finish remaining Pilot C acquisition/shaping/D14 reachability.
9. Verify telemetry for all three.
10. Only then begin controlled live pilot games.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 — D1 survival expansion — COMPLETE
3. Phase 2 — simple shop survival — COMPLETE
4. Phase 3 — coherent build evidence — COMPLETE
5. Phase 4 — resource semantics — COMPLETE
6. Phase 5 — initial live validation — COMPLETE; exposed 0/10 competence failure
7. Phase 6A — strategy authority contract — COMPLETE / GREEN
8. Phase 6B — three-pilot deterministic architecture proofs — COMPLETE / GREEN
9. Phase 6C — three-pilot production integration — **ACTIVE**
10. Phase 6D — controlled live pilot validation — BLOCKED ON 6C
11. Phase 6E — pilot-driven semantic fixes / repeated live validation — BLOCKED
12. Phase 6F — full catalogue refurbishment/expansion — BLOCKED ON LIVE PILOT SUCCESS
13. Phase 6G — broader numerical/action-quality tuning — BLOCKED

Future stake/deck progression remains blocked until Red/White competence passes.
