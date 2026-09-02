# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative development roadmap for the Balatro Red Deck / White Stake competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- The user runs actual Balatro gameplay and validation requiring the Windows/game environment.
- Validation commands shown to the user must begin with `git pull`, use `pytest -q` when applicable, and be PowerShell-compatible.
- Preserve exact mechanics, legality, boss rules, affordability, survival, and hidden-information boundaries.
- Prefer canonical ownership over wrappers/rescue layers.
- Cleanup is part of migration completion.

# Objective

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

Canonical architecture:

```text
PUBLIC GAME STATE
→ MECHANICAL DESCRIPTORS
→ WEIGHTED BOND CONTRIBUTIONS
→ BOND DEVELOPMENT + REALIZATION
→ SPARSE RELATIONSHIPS + EXCEPTIONAL MOTIFS
→ BuildValue(state)
→ PROJECTED STATE AFTER CANDIDATE
→ StrategyDelta(candidate)
→ EXISTING CANONICAL DECISION OWNER
```

Bonds provide strategic value/guidance only. Tactical/gameplay owners remain authoritative for mechanics and hard constraints.

## Canonical formulas

```python
def bond_strength(points: float) -> float:
    return points ** 1.35
```

```text
BondValue = bond_strength(points) × realization × optional calibration weight
RelationshipValue = coefficient × min(BondValueA, BondValueB)
MotifValue = completion × estimated_payoff
BuildValue(state) = Σ BondValue + Σ RelationshipValue + Σ MotifValue
StrategyDelta(candidate) = BuildValue(projected) - BuildValue(current) - transition_cost
```

Transition cost is small inertia against near-equal thrashing, not a strategy state machine.

# Explicitly obsolete architecture

Do not rebuild or preserve as production authority:

- giant persistent strategy controller/state machine;
- named strategy identity as primary action authority;
- FORMING/PINNED/etc. action states;
- persistent `StrategyPlan` propagation;
- `seek_feature:*`, `seek_bond:*`, `preserve_feature:*`, `commit_*`, or pivot-prescription plumbing;
- one execution tree per Bond;
- generic pivot FSM/resistance;
- duplicate Bond/build evaluators.

# Required end state

```text
ONE mechanics → Bonds → BuildValue → StrategyDelta path
ONE set of production integrations
NO parallel legacy Bond planner/controller path
NO dead prescription plumbing
NO obsolete compatibility wrappers/tests/docs
```

# CURRENT DEVELOPMENT PATH

## Phase A — Freeze Bond vocabulary — COMPLETE

Validated green. 46 canonical Bonds. Canonical renames include `burnt → hand_leveling`, `gold_economy → gold_cards`, and `vampire → enhancement_consumption`.

## Phase B — Mechanical descriptors — COMPLETE

Validated green. `games/balatro/mechanics.py` is the canonical public mechanics surface.

## Phase C — Mechanics → Bond contributions — COMPLETE

Validated green across all 46 Bonds. `games/balatro/bonds/contributions.py` owns keyed contribution normalization.

## Phase D — Bond strategic value — COMPLETE

Validated green. `games/balatro/bonds/strategic_value.py` owns nonlinear per-Bond value; Bond rank is diagnostic rather than action authority.

## Phase E — Sparse relationships and exceptional motifs — COMPLETE

Validated green. Relationships and motifs remain deliberately sparse; unlisted pairs are neutral.

## Phase F — Canonical `BuildValue(state)` — COMPLETE

Validated green. `games/balatro/bonds/build_value.py` is the single whole-build evaluator.

## Phase G — Projected-state `StrategyDelta(candidate)` — COMPLETE

Validated green. `strategy_delta_from_states(...)` is the canonical comparison boundary. No strategy identity, commitment state, pivot FSM, or prescription fields exist in `StrategyDelta`.

## Phase H — Integrate canonical strategic decision owners — COMPLETE

Validated green across Joker acquisition/replacement, pack choices, deterministic Tarot/Spectral transforms, Planet development, resource arbitration, and stateful Joker admission.

Production no longer installs retired R0/FORMING/PINNED controllers, generic pivot/resistance authority, manual prescription execution, pinned pack execution, strategy-authority correction, or Bond-rank retention vetoes.

Public mechanics/evidence remain authoritative for legitimate guards such as exotic-Planet anti-bootstrap behavior, Stateful Joker admission, affordability, resource reserve, legality, and hidden-information boundaries.

## Phase I — Verify tactical exploitation — COMPLETE

Validated green.

Representative canonical tactical proofs cover:

1. Burnt Joker first-discard hand leveling.
2. Hanged Man / permanent deck thinning.
3. Steel / Baron / Mime held-card preservation and exploitation.

Tactical owners remain subordinate to survival, clear probability, boss constraints, and legality.

## Phase J — Deterministic end-to-end proofs — COMPLETE

Validated green in representative end-to-end paths for hand leveling, deck thinning, and held-card engines.

Compatible candidates gain canonical BuildValue/StrategyDelta, destructive dependency removal loses value, materially stronger alternatives can still win, and D1/D2/D9/D14 tactical owners exploit the constructed engine.

## Phase K — Migration cleanup gate — COMPLETE

Completed repository-wide migration cleanup.

### Production cleanup

- removed the retired R0/PINNED/FORMING transition and retention controllers;
- removed generic pivot FSM/resistance and pivot calibration/telemetry;
- removed Bond-rank power-engine/tactical retention vetoes;
- removed manual prescriptions, pinned execution, strategy authority correction, and obsolete Build Health HOLD→BUY wrappers;
- removed the `StrategyPlan`, behavior-strategy, and strategy-semantics subsystems;
- collapsed `Composition` to structural Bond/motif/synergy/conflict evidence only;
- removed `evaluate_bond_composition(...)` and migrated production consumers to structural/canonical boundaries;
- migrated canonical Bond IDs/realizers from retired `vampire` / `gold_economy` identities to `enhancement_consumption` / `gold_cards`;
- migrated offline Bond tuning away from deleted pivot-resistance parameters;
- preserved valid mechanics, economics, health, D1/D2/D9/D14, boss, hidden-information, and runtime constraints.

### Semantic corrections discovered during cleanup

Full-suite classification exposed and fixed real mechanics regressions rather than masking them:

- Midas → Vampire same-hand feed respects Joker trigger order;
- persistent enhancement feed remains a run-level Vampire axis even when temporarily debuffed;
- Midas renewable future feed distinguishes current scoring order from future feed availability;
- Gold-card realization ignores debuffed immediate Gold effects;
- Midas Gold generation requires a live scoring face route;
- Stone cards hide ordinary rank identity from Midas/Vampire unless Pareidolia/all-cards-face semantics apply;
- Planet observed-hand ranking and exotic-hand public-evidence behavior remain canonical.

### Validation

- collection is green;
- focused Phase K regression groups are green;
- the complete `tests/balatro` suite is green after the final stale `strategy_candidates` / `evaluate_bond_composition` Build Health test was removed.

Phase K exit condition is satisfied: no rejected commitment/prescription architecture is required by production, and the deterministic Balatro suite is green.

## Phase L — Targeted live validation and tuning — ACTIVE

Run authoritative Red Deck / White Stake gameplay only after deterministic cleanup is green. It is now green.

### L1 — Fresh production baseline — COMPLETE

Fresh three-attempt production batch: `balatro-20260902T200815Z-dba5db6f`.

Outcomes:

- attempt 001: lost Ante 7 boss The House, 49,834 / 70,000;
- attempt 002: lost Ante 3 boss The Needle, 770 / 2,000;
- attempt 003: lost Ante 2 boss The Club, 1,404 / 1,600.

Runtime findings:

- no permanent SHOP stall;
- no SHOP decision exceeded 5 seconds in this batch;
- maximum observed SHOP decision latency was approximately 3.829 seconds;
- maximum observed D1 decision latency was approximately 2.519 seconds;
- D1's previous 20–25 second `nodes=0` failure is absent after bounded root admission;
- D14 timing still contains non-trivial unclassified residual around standalone Joker evaluation in some states, but it is no longer the dominant interactive blocker in this batch.

Decision-quality findings:

- attempt 003 bought Baron for $8 in Ante 1 from an untouched 52-card deck and no established held-King engine;
- canonical evaluation incorrectly treated the ordinary four starting Kings as `KING_INFRASTRUCTURE`, making `baron_mime_steel` POTENTIAL from Baron + baseline deck alone and inflating StrategyDelta;
- production fix: exceptional Baron motif King infrastructure now requires increased King density (at least five Kings), while ordinary Kings and held-card Bonds remain available to value Baron normally;
- attempt 002 bought Flash Card even though canonical D2 explicitly returned HOLD (`buy advantage=0.100` versus threshold `0.350`); a later live Build Health rescue converted that rejected candidate back into BUY.

### L2 — Classify live failures — ACTIVE

For every suspicious live decision, classify it before changing numbers:

1. **mechanics/model bug** — fix semantics first;
2. **runtime/latency bug** — bound or factorize computation without changing decision meaning;
3. **integration/authority bug** — repair ownership/order instead of adding a rescue wrapper;
4. **calibration issue** — only then tune contribution weights, realization, relationships, motif payoff, transition inertia, or integration weights.

Current classified work:

- Baron + untouched four-King deck false exceptional-motif potential: **mechanics/model bug — FIXED and focused validation GREEN**;
- Flash Card D2 HOLD resurrected by `live_competence_guard_policy`: **integration/authority bug — FIXED, validation pending**;
- the live competence guard no longer wraps Joker acquisition at all; D2 HOLD/BUY admission is final, while the independent D1 liveness guards and one bounded D14 scaling-deficit reroll guard remain;
- remaining attempt 001/002 build quality and terminal boss decisions: **inspection pending**;
- D14 standalone-Joker timing residual: **runtime attribution/possible optimization issue, non-blocking but still to classify**.

### L3 — Numerical tuning gate

Do not start Optuna/numerical calibration until the fresh baseline completes SHOP decisions without semantic/runtime stalls or excessive interactive latency and the identified live semantic defects are fixed.

When tuning begins, preserve the canonical architecture and compare against the production baseline using authoritative unseeded live runs with run provenance.

## Phase M — Broader competence

After Bond-guided Red/White competence is demonstrated, address broader gameplay failures, consistency, higher stakes, and additional decks.

# Exact next action

**Validate canonical D2 HOLD authority, then continue Phase L2 classification from the same three-run batch.**

1. Run the focused live-competence/D2 authority regression and relevant Joker/D14 authority tests.
2. If green, inspect attempt 001 and remaining attempt 002 material purchases/replacements and terminal boss choices for additional semantic/integration defects.
3. Keep D14 residual timing under observation; optimize only if the expensive owner is identified without changing decision semantics.
4. Do not begin numerical calibration until live semantic defects are exhausted.

# Progress criterion

```text
mechanical semantics
→ canonical Bond contributions
→ Bond/relationship/motif value
→ BuildValue
→ StrategyDelta
→ canonical decision-owner integration
→ legacy-path removal
→ tactical exploitation
→ deterministic E2E proof
→ cleanup gate
→ live validation/tuning
```

Controlling question:

> **Does this candidate leave the run with a stronger coherent Balatro engine, and can the rest of the agent actually exploit that engine to win?**
