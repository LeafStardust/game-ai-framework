# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative roadmap/handoff for the Balatro Red/White competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests/live games locally. **Do not run tests or live games from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Every focused pytest validation command must use `-q`.
- Every command block shown must end with a trailing blank after the final command.
- Preserve exact Balatro mechanics, public-state legality, boss rules, and hidden-information boundaries.
- Never use hidden RNG state, seeds, future pool order/identities, or inaccessible information.
- Prefer canonical ownership over late wrappers/rescues.
- Bond/composition and Build Health are evidence/planning layers, never direct score/action authorities.
- Numerical tuning must not compensate for missing or malformed strategy semantics.
- Before Bond/strategy work, read `docs/balatro/BALATRO_STRATEGY_SYSTEM.md` and `docs/balatro/BALATRO_RELATIONSHIPS_MOTIFS.md`, then inspect the current implementation.
- Use scoped Conventional Commit messages.

# Objective

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

The Bond system exists only if it helps the production agent make better run-winning decisions.

Canonical flow:

```text
public game state
    ↓
literal Balatro mechanics
    ↓
Bond contributions + semantic mechanics
    ↓
coherent candidate/pinned strategy
    ↓
bounded construction / preservation / execution preferences
    ↓
canonical D1/D2/D3/D4/D9/D11/D14 consumer
    ↓
final legal/survival-aware action
    ↓
better run outcome
```

A Bond regression passing in isolation is not sufficient. The production agent must be able to observe the strategy, pursue it, preserve it, execute it, and abandon it when survival or a materially stronger alternative requires that.

# Current state — 2026-09-02

Phase 5 live semantic validation completed at **74/74 green**, but the original baseline and Tunes A–F repeatedly produced **0/10 wins**. This demonstrated that local semantic correctness alone was not enough to make the agent competent.

The response was to stop broad numerical tuning and reengineer the Bond/strategy system around a deliberately small pilot before touching the full 46-Bond catalogue.

## THREE-BOND PILOT — AUTHORITATIVE SCOPE

Only three strategic verticals are the current implementation target:

### Pilot A — Burnt / persistent hand-level development

Purpose:
- recognize Burnt as a persistent development engine;
- choose safe first discards that develop the intended hand;
- value supporting target-hand development;
- exploit the resulting persistent hand level later;
- stop development greed when current-blind survival requires scoring immediately.

### Pilot B — Deck shaping / deck thinning

Purpose:
- recognize deck thinning/destruction as a coherent construction direction;
- value Trading Card/Erosion-style development for actual strategy reasons;
- prefer compatible deck-shaping acquisitions over unrelated Bond collection;
- carry the strategy into relevant shop/pack/consumable decisions when those consumers already own the choice;
- never destroy immediate survival/economy for speculative thinning.

### Pilot C — Held-card / Steel-style persistent-card preservation

Purpose:
- recognize held-card payoff/retrigger/persistent-card mechanics before a full Baron-Mime-Steel package exists;
- remain construction-only while FORMING;
- graduate to PINNED+ when the public engine is coherent enough;
- preserve relevant Kings/Steel/held-engine cards among otherwise safe/near-equivalent D1 choices;
- value compatible construction pieces through canonical acquisition consumers;
- spend engine cards when survival or a materially stronger line requires it.

These three pilots are intentionally different:
- Burnt proves persistent development + D1 execution.
- Deck thinning proves construction/acquisition authority.
- Held-card/Steel proves strategy graduation + preservation authority.

Together they are the testbed for whether the Bond architecture can actually help win games.

# Validated architecture contracts

## Development / realization / commitment remain separate

```text
Development = Bond R0–R5
Realization = DORMANT / PARTIAL / ACTIVE / MATURE
Commitment  = EXPLORATORY / FORMING / PINNED / ESTABLISHED / DOMINANT
```

- Rank measures persistent investment in one Bond.
- Realization measures whether that mechanic functions now.
- Commitment measures whether connected mechanics form a coherent plan worth pursuing/preserving.
- Build Health separately answers whether the run is actually strong enough.

## FORMING = construction authority only

FORMING may:
- expose bounded strategy plans;
- emit `seek_feature:*` and `seek_component:*` goals;
- influence admitted acquisition/development choices.

FORMING may not merely by existing:
- protect components from replacement;
- dictate D1 execution;
- impose held-card preservation;
- create fake pivot resistance;
- be internally promoted to PINNED.

## PINNED+ = preservation/execution authority

PINNED / ESTABLISHED / DOMINANT may add bounded preservation/execution preferences, still below:
- legality;
- exact survival;
- affordability/economy;
- boss correctness;
- materially stronger projected alternatives.

# Pilot proof status

The following deterministic regressions are useful architecture evidence and remain closed unless contradicted by new evidence.

## Burnt proof — GREEN

Validated locally:
- Burnt recognition and target-hand evidence;
- D1 first-discard valuation;
- final D1 arbitration counterfactual;
- persistent `hand_levels` gain;
- later exploitation of developed High Card;
- survival override.

Relevant tests include:
- `test_balatro_d1_burnt_native_evidence.py`
- `test_balatro_d1_burnt_final_arbitration.py`
- `test_balatro_d1_burnt_controlled_sequence.py`

## Deck-thinning proof — GREEN

Validated locally:
- Erosion can form a low-authority deck-thinning direction;
- Trading Card deepens it;
- Card Destruction ↔ Deck Thinning synergy is recognized;
- unrelated positive Bond development does not receive equivalent D2 transition value.

Relevant test:
- `test_balatro_deck_thinning_strategy_transition.py`

## Held-card preservation proof — GREEN AT CONSUMER BOUNDARY

Validated locally:
- FORMING does not receive categorical preservation;
- PINNED held-card evidence changes an otherwise safe/equivalent D1 discard;
- deterministic survival overrides preservation.

Relevant tests:
- `test_balatro_d1_pinned_held_card_preservation.py`
- `test_balatro_d1_pinned_held_card_final_action.py`

Important limitation: these consumer-boundary tests do **not by themselves prove that an ordinary production state naturally forms the intended held-card candidate and reaches PINNED+ at the right time.** Production semantic formation must be checked before declaring Pilot C game-ready.

## Contradiction proof — GREEN

Burnt × No-Discard proves conflicting axes cannot both collect positive structural reward indiscriminately. The D2 conflict-valuation defect was fixed in `9027577`.

This is a supporting architecture test, not a fourth pilot Bond.

# Accidental catalogue detour — RETAIN BUT DEFER

After the pilot proofs, work drifted into catalogue-wide validation. The following commits uncovered legitimate structural defects and should remain unless they cause regressions:
- catalogue audit documentation;
- hard-unlock regressions;
- suit-density and rare-hand authority regressions;
- resource-Bond direct-scoring boundary;
- broad-payoff overlap / Vampire-Midas defining-core correction;
- Batch-5 rank-reachability corrections.

However, **none of this work is a prerequisite for the three-Bond pilot live test.**

From this point:
- no further 46-Bond catalogue audit;
- no catalogue-wide threshold reachability sweep;
- no broad relationship/motif expansion;
- no new Bond families;
- no tuning the remaining catalogue for completeness.

The existing 46-Bond catalogue may remain registered, but only the three pilot verticals are allowed to drive the current strategy reengineering effort.

# ACTIVE PHASE — PILOT PRODUCTION INTEGRATION

The current task is to determine whether the three pilot strategies actually travel through the **real production agent**, not merely isolated helper tests.

For each pilot, trace:

```text
real public state
→ evaluate_bond_composition()
→ real StrategyCandidate / commitment
→ strategy plan / goals / prescriptions
→ canonical consumer(s)
→ final production decision
```

## Gate P1 — production strategy formation

For each pilot, construct a realistic public state using real Jokers/cards/state fields and verify:
- correct Bond evidence exists;
- intended StrategyCandidate exists naturally;
- commitment is appropriate;
- no fake test-only `SimpleNamespace` candidate is required;
- removing the relevant public mechanic removes or weakens the candidate.

Pilot C is the highest-priority uncertainty because existing D1 preservation tests inject the candidate manually.

## Gate P2 — production consumer reachability

Audit whether each pilot's real strategy reaches every consumer needed for useful play.

### Burnt
Required production consumers:
- D1 discard/execution;
- D2 relevant Joker construction/replacement where applicable;
- D3/D4/D9 target-hand development choices only if those owners already support semantic strategy goals.

### Deck thinning
Required production consumers:
- D2 Joker acquisition/replacement;
- D4/D9 deck-removal/deck-transform consumables/packs where already admitted;
- D14 shop arbitration must not erase the child-policy strategy preference.

### Held-card / Steel
Required production consumers:
- D1 preservation/execution;
- D2 compatible Joker construction/replacement;
- D4/D9 relevant Steel/Seal/card-shaping choices where already admitted;
- D14 must preserve child-policy authority.

Do not add a second final arbiter. Feed missing strategy evidence into the existing canonical owner.

## Gate P3 — controlled production counterfactuals

For each pilot, use the production stack and real game objects:

```text
same public state
same legal candidates
remove only relevant strategy mechanic
→ ordinary decision

restore relevant strategy mechanic
→ strategically correct decision
```

The change must disappear when the strategy fact disappears.

## Gate P4 — telemetry / diagnosability

Before live testing, confirm telemetry can show:
- relevant pilot Bonds;
- candidate/pinned strategy and commitment;
- missing goals;
- strategy transition/preservation rationale in the consumer that acted.

If a live loss occurs, we must be able to tell whether the failure was:
`MECHANIC_MODEL`, `BOND_REPRESENTATION`, `ROLE_DESCRIPTOR`, `SEMANTIC_LINKING`, `STRATEGY_FORMATION`, `GOAL_PRESCRIPTION`, `PROJECTED_TRANSITION`, `CONSUMER_VALUATION`, or `FINAL_ARBITRATION`.

# NEXT PHASE — CONTROLLED LIVE PILOT VALIDATION

Only after P1–P4 are green:

1. run a small controlled Red Deck / White Stake batch using the current production agent;
2. do **not** introduce Tune G first;
3. collect run traces for pilot-strategy opportunities and failures;
4. measure wins, but also measure whether the agent correctly pursued/preserved/executed available pilot strategies;
5. classify the first causal failure in each bad run;
6. fix semantic/authority defects before changing numbers;
7. repeat the same controlled batch.

The immediate success criterion is not that every run contains one of the three pilots. It is:
- when a pilot opportunity exists, the agent recognizes and uses it coherently;
- strategy behavior does not cause avoidable deaths;
- the system begins converting some runs into wins rather than remaining 0/10 because it cannot build or maintain an engine.

# Catalogue expansion gate

Only after the three-Bond pilot demonstrates real production usefulness and live improvement do we generalize the architecture to the remaining Bond catalogue.

Then, and only then:
- classify/merge/remove malformed Bonds;
- calibrate rank reachability catalogue-wide;
- expand semantic links/motifs where mechanics justify it;
- perform broader action-quality tuning.

# Failure ownership

Always fix the first incorrect stage:
- `MECHANIC_MODEL`
- `BOND_REPRESENTATION`
- `ROLE_DESCRIPTOR`
- `SEMANTIC_LINKING`
- `STRATEGY_FORMATION`
- `GOAL_PRESCRIPTION`
- `PROJECTED_TRANSITION`
- `CONSUMER_VALUATION`
- `FINAL_ARBITRATION`

Never patch a later consumer to compensate for a missing upstream fact.

# EXACT NEXT ACTION

1. Treat the catalogue-wide Phase 6F work as deferred.
2. Treat the three pilot proof regressions as architecture evidence, not final live proof.
3. Start with **Pilot C held-card/Steel**, because its existing final-D1 test uses a manually injected candidate and therefore leaves the largest production-integration uncertainty.
4. Build the shortest realistic state with actual held-card/Steel/Baron/Mime-style mechanics that naturally yields FORMING first and PINNED+ once coherent enough.
5. Feed that real composition into `StrategyAwareLiveHandActionPolicy` and prove the final safe-equivalent D1 choice changes only at PINNED+.
6. If natural formation fails, fix the first upstream semantic/formation layer; do not modify D1 preservation unless its existing consumer behavior is actually wrong.
7. Then perform the equivalent production-stack audit for Deck Thinning and Burnt.
8. Verify telemetry for all three.
9. User runs focused regressions locally.
10. Once P1–P4 are green, begin the controlled live pilot batch before any further catalogue or numerical tuning.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 — D1 survival expansion — COMPLETE
3. Phase 2 — simple shop survival — COMPLETE
4. Phase 3 — coherent build evidence — COMPLETE
5. Phase 4 — resource semantics — COMPLETE
6. Phase 5 — initial live validation — COMPLETE; outcome exposed 0/10 competence failure
7. Phase 6A — strategy authority contract — COMPLETE / GREEN
8. Phase 6B — three-pilot deterministic architecture proofs — COMPLETE / GREEN
9. Phase 6C — three-pilot **production integration** — **ACTIVE**
10. Phase 6D — controlled live pilot validation — BLOCKED ON 6C
11. Phase 6E — pilot-driven semantic fixes / repeated live validation — BLOCKED
12. Phase 6F — full catalogue refurbishment/expansion — BLOCKED ON LIVE PILOT SUCCESS
13. Phase 6G — broader numerical/action-quality tuning — BLOCKED

Future stake/deck progression remains blocked until Red/White competence passes.
