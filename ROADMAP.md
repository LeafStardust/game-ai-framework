# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative development roadmap for the Balatro Red Deck / White Stake competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests and live games locally. **Do not run tests or live games from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Every focused pytest command must use `-q`.
- Commands shown to the user must be PowerShell-compatible: use separate command lines rather than `&&`.
- Every command block shown to the user must contain a blank line after its final command before the closing fence.
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
- FORMING/PINNED/etc. as required action states;
- mandatory persistent `StrategyPlan` propagation;
- `seek_feature:*`, `seek_bond:*`, `preserve_feature:*`, `commit_*`, or pivot-prescription plumbing as the foundation;
- manual 46-Bond wiring into every decision owner;
- one execution tree per Bond;
- generic pivot FSM/resistance;
- motif explosion;
- duplicate Bond/build evaluators.

# Migration contract

```text
new canonical path implemented
→ production consumer migrated
→ deterministic tests prove replacement
→ dependency search confirms old path unnecessary
→ obsolete code/tests/docs deleted
```

Required end state:

```text
ONE mechanics → Bonds → BuildValue → StrategyDelta path
ONE set of production integrations
NO parallel legacy Bond planner/controller path
NO dead prescription plumbing
NO obsolete compatibility wrappers/tests/docs
```

# CURRENT DEVELOPMENT PATH

## Phase A — Freeze Bond vocabulary — COMPLETE

Validated green. 46 canonical Bonds; canonical renames are `burnt → hand_leveling`, `gold_economy → gold_cards`, and `vampire → enhancement_consumption`.

## Phase B — Mechanical descriptors — COMPLETE

Validated green. `games/balatro/mechanics.py` is the canonical public mechanics surface and production Bond evaluators use mechanics/direct public state rather than local strategy-name tables.

## Phase C — Mechanics → Bond contributions — COMPLETE

Validated green across all 46 Bonds. `games/balatro/bonds/contributions.py` owns keyed contribution normalization; the same source counts at most once within a Bond but may support multiple Bonds.

## Phase D — Bond strategic value — COMPLETE

Validated green. `games/balatro/bonds/strategic_value.py` owns nonlinear per-Bond value with exponent `1.35`, realization factors `0 / 0.35 / 0.75 / 1.0`, ranks as diagnostics only, and optional calibration weights.

## Phase E — Sparse relationships and exceptional motifs — COMPLETE

Validated green.

Positive relationships:
- Held Cards + Steel
- Held Cards + Held Retrigger
- Steel + Held Retrigger
- Card Destruction + Deck Thinning

Conflicts:
- Discard + No Discard
- Face Cards + No Face Cards
- Enhancement Consumption + Enhanced Cards

Unlisted pairs are neutral. Canonical exceptional motif scope currently contains only Baron + Mime + at least two Steel Kings.

## Phase F — Canonical `BuildValue(state)` — COMPLETE

Validated green. `games/balatro/bonds/build_value.py` is the single whole-build evaluator and exposes Bond, relationship, motif, and total diagnostics without choosing actions.

## Phase G — Projected-state `StrategyDelta(candidate)` — COMPLETE

Validated green after correcting disappeared projected Bonds to count as fully removed realized structure.

- `strategy_delta_from_states(current_state, projected_state)` is the canonical state-comparison boundary.
- `strategy_delta(candidate, state, projector=...)` delegates candidate simulation to the caller-owned domain projector.
- Default transition inertia is `5%` of removed realized Bond value.
- Relationship/motif losses are not charged twice as inertia.
- No strategy identity, commitment state, pivot FSM, or prescription fields exist in `StrategyDelta`.

## Phase H — Integrate canonical strategic decision owners — COMPLETE

### H1 — Joker acquisition/replacement — COMPLETE

Validated green.

- The old Joker transition bonus based on Bond ranks, composition coherence, pinned strategy, `StrategyPlan`, legacy motifs, and pivot state has been removed from the production Joker policy.
- The installed post-transaction D2 authority combines post-transaction native mechanical gain, `0.10 × canonical StrategyDelta`, and existing transaction economics.
- Affordability, slot handling, early-run safety, and mechanically negative replacement rejection remain authoritative.

### H2 — Booster/pack persistent choices — COMPLETE

Validated green.

- Historical StrategyPlan/Bond-goal pack bonuses were replaced by projected canonical StrategyDelta for exact persistent PLAYING_CARD and PLANET pack outcomes.
- Playing-card projection appends the materialized card to persistent deck state; Planet projection increments the relevant public hand level.
- Base pack legality, literal value, stochastic expectation, and Skip remain authoritative.
- `_goal_ids` / `_playing_card_matches` remain temporarily as compatibility helpers only and are cleanup candidates for Phase K.

### H3 — Tarot/Spectral persistent deck transformations — COMPLETE

Validated green.

- Deterministic Tarot/Spectral target legality and literal/contextual target quality remain owned by `ContextualConsumableTargetEvaluator`.
- Real consumable `can_use/use` semantics are projected on deep-copied public state and exact persistent deck changes feed canonical StrategyDelta.
- Hanged Man uses shared permanent playing-card destruction semantics.
- Only already-positive deterministic target evaluations receive the conservative `0.10 × StrategyDelta` adjustment.

### H4 — Planet / hand-development owners — COMPLETE

Validated green.

- Shop Planet acquisition uses exact projected Planet semantics and `0.10 × canonical StrategyDelta` in the existing acquisition owner.
- Held-Planet timing remains tactical and cannot be overridden by StrategyDelta.
- Historical Bond-rank Planet relevance was retired from D4 production authority.

### H5 — Legacy acquisition-controller authority cleanup — COMPLETE

Validated green.

- D8 unopened Standard/Arcana/Spectral demand no longer reads strategy candidates, commitments, or prescriptions; hidden contents are valued from public BuildProfile expectation.
- Celestial retained direct observed-hand specialization.
- The generic D3 zero-fit Voucher cash reserve remains as an economic safety rule.
- D14 Joker utility no longer adds pinned-strategy goal bonuses after H1's D2 build gain has already incorporated canonical StrategyDelta.

### H6 — Manual Bond prescription execution wrapper — COMPLETE

Validated green.

- Manual motif-specific D9/D14 prescription bonuses were retired from production.
- Exact persistent outcomes remain owned by the H2/H3/H4 canonical StrategyDelta integrations.
- `_active_motif_ids` remains only as a temporary compatibility observer for stale non-authoritative callers.

### H7 — Legacy D2 strategy controllers — COMPLETE

Validated green.

- Production no longer installs R0/FORMING transition bonuses, pinned transition bonuses, PINNED retention, or FORMING StrategyPlan retention controllers.
- Native D2 `_bond_transition_bonus` now remains the canonical weighted whole-build StrategyDelta term without legacy wrappers.

### H8 — Pinned pack execution overlay — COMPLETE

Validated green.

- Production no longer adds `seek_feature:*`/pinned-strategy execution bonuses after D9 canonical pack scoring.
- The compatibility module remains only for later cleanup.

### H9 — Strategy authority correction wrapper — COMPLETE

Validated green.

- Production no longer mutates composition into FORMING/PINNED action authority or adds FORMING missing-piece bonuses to D9/D14.
- Canonical D9 StrategyDelta and H1/D14 value flow remain authoritative.

### H10 — Generic Bond pivot authority — COMPLETE

Validated green.

- The generic pivot/resistance FSM-style controller was removed from production.
- D2 replacement decisions rely on native mechanics/economics plus canonical projected StrategyDelta instead of named pivot thresholds.

### H11 — Bond power-engine retention wrapper — COMPLETE

Validated green.

- ACTIVE/MATURE/R2 Bond-rank retention vetoes were retired from production.
- Mechanical replacement eligibility remains native; projected BuildValue loss and transition inertia remain canonical StrategyDelta concerns.

### H12 — Planet relevance public-evidence cleanup — COMPLETE

Validated green.

- D9 exotic-Planet relevance no longer accepts StrategyPlan/pinned-strategy escape hatches.
- The legitimate anti-bootstrap guard remains based on public hand-play evidence/development state.

### H13 — Stateful Joker admission public-evidence cleanup — COMPLETE

Validated green.

- Stateful Joker admission no longer uses `StrategyPlan`, `pinned_strategy_id`, strategy candidates, planned Bond goals, or “creates strategy” bypasses.
- Mechanical guards for Mime, Madness, Obelisk, Joker Stencil, conditional hand payoffs, and To Do List remain intact and use public mechanics/evidence.

### H14 — Retired-controller production registration audit — COMPLETE

Validated green.

- Consolidated regression coverage proves the retired H7–H13 strategy-controller installers are not reintroduced into the production stack.

### H15 — Celestial direction public-evidence cleanup — COMPLETE

Validated green.

- Celestial D8/D9 direction/headroom no longer reads `StrategyPlan`, commitment, or pinned hand goals.
- Direction comes from observed public hand usage; Constellation retains independent Planet-use-scaler authority.
- Finite Planet-pool expectation, literal score projection, duplicate/Showman handling, affordability, reserve protection, and unrelated loose-Tarot behavior remain intact.

Phase H exit condition is satisfied: remaining installed strategy-named resource logic uses public evidence/mechanics rather than named-strategy action authority. Compatibility-only legacy modules may remain until the Phase K cleanup gate.

## Phase I — Verify tactical exploitation — ACTIVE

Verify canonical tactical owners actually exploit the engines Phase H can now construct.

Required tactical paths:
1. Hand Leveling / Discard / Hand Development — especially Burnt Joker first-discard leveling.
2. Card Destruction / Deck Thinning — especially Hanged Man target quality and permanent-deck exploitation.
3. Held Cards / Steel / Held Retrigger — especially preserving and exploiting Steel/Baron/Mime held-card value during play/discard selection.

Do not create new Bond-specific tactical controllers unless a real mechanical owner is missing. Prefer extending the existing tactical evaluator with exact public mechanical value.

## Phase J — Deterministic end-to-end proofs

Minimum representative paths:
1. Hand Leveling / Discard / Hand Development
2. Card Destruction / Deck Thinning
3. Held Cards / Steel / Held Retrigger

Prove compatible candidates gain strategic value, destructive replacement loses dependent value, materially stronger alternatives can still win, and tactical owners exploit resulting mechanics.

## Phase K — Migration cleanup gate

Repository-wide audit must confirm no production dependency on rejected commitment/prescription authority, no duplicate Bond/build evaluator, no obsolete compatibility wrapper after its final consumer, and no stale tests/docs enforcing rejected architecture.

## Phase L — Targeted live validation and tuning

Only after deterministic proofs and cleanup are green: run Red Deck / White Stake locally, inspect coherent build emergence/bait rejection/preservation/justified pivots, then tune contribution weights, curve, realization, relationships, motif payoff, transition cost, and integration weights.

## Phase M — Broader competence

After Bond-guided Red/White competence is demonstrated, address broader gameplay failures, consistency, stakes, and decks.

# Exact next action

**Complete Phase I tactical-exploitation verification across the three required engine families.**

1. Fresh-fetch the canonical live hand/discard owner and verify Burnt Joker's first-discard hand-leveling trigger is represented in action selection rather than only in strategic construction value.
2. Verify Hanged Man/card-destruction target selection rewards permanent deck thinning through the existing consumable target owner without adding a parallel destruction controller.
3. Verify hand/discard selection values held-card mechanics strongly enough to preserve and exploit Steel cards, Baron-held Kings, and Mime retriggers when tactically appropriate.
4. For each confirmed gap, patch the existing tactical owner with public mechanical value only; preserve legality, survival, hand-clear probability, and boss constraints.
5. Add focused deterministic Phase I regressions covering all changed tactical paths and ask the user to run one combined local validation command.
6. When all three tactical paths are proven green, advance to Phase J end-to-end proofs.

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
