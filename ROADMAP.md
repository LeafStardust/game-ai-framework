# ROADMAP — SINGLE SOURCE OF TRUTH

This is the authoritative roadmap/handoff for the Balatro Red/White competence branch.

## Repository contract

- Repository: `LeafStardust/game-ai-framework`
- Branch: `feat/v1.0-red-white-competence`
- User runs tests/live games locally. **Do not run tests or live games from ChatGPT.**
- Every validation command shown to the user must begin with `git pull`.
- Every command block shown must end with a trailing blank after the final command.
- Preserve exact Balatro mechanics, public-state legality, boss rules, and hidden-information boundaries.
- Never use hidden RNG state, seeds, future pool order/identities, or inaccessible information.
- Prefer canonical ownership over late wrappers/rescues.
- Bond/composition and Build Health are evidence/planning layers, never immediate score/action authorities.
- Numerical tuning must not compensate for missing or malformed strategy semantics.
- **Before Bond/strategy work, read `docs/balatro/BALATRO_STRATEGY_SYSTEM.md` and `docs/balatro/BALATRO_RELATIONSHIPS_MOTIFS.md`, then inspect the current implementation.** These documents preserve the Currency-Wars-derived intent of Bonds and motifs; they are historical/design context, not immutable implementation requirements.

## Objective

**Red Deck / White Stake, normal mode: maximize probability of winning the current run.**

Canonical authority:

```text
Authoritative public state
        ↓
Literal Balatro mechanics
        ↓
Legal candidates
        ↓
Bounded projection
        ↓
One run-winning evaluator
        ↓
One final arbiter
        ↓
Action
```

Canonical owners remain:
- D1 search/projection: `LiveBlindClearPlanner` / `D1LiveBlindClearPlanner`
- D1 arbitration: `StrategyAwareLiveHandActionPolicy`
- D1 orchestration/final return: `LiveHandActionDecisionEngine` / `PathAwareLiveHandActionDecisionEngine`
- D14 SHOP: `BuildAwareShopArbiter`
- D11 reroll: `BuildAwareShopRerollPolicy`
- D9 opened pack: `BalatroPackPolicy`
- D4 consumable acquisition: `ConsumableAcquisitionPolicy`
- D3 voucher acquisition: `VoucherAcquisitionPolicy`

# Current state — 2026-09-01

Phase 5 live semantic validation is complete at **74/74 green**. The original baseline and Tunes A–F repeatedly produced **0/10 wins**. Tune A is provisionally retained; B–F were rejected/reverted. The D9 Buffoon ownership correction `c1f8422` is retained as semantically correct but did not improve the controlled live result.

The D1–D14 decision-authority audit is not the current primary target. The observed competence failure is that the agent can have an apparent run direction yet still fail to buy useful pieces, buy unrelated/contradictory pieces, or fail to preserve the machinery of that direction.

This means the next task is **not** a Bond-by-Bond numerical audit and **not** another broad decision-layer audit. We must first locate where strategic understanding is lost in the full causal path.

Validated checkpoints that remain closed absent fresh reproducible evidence:
- Phase 0 authority consolidation: complete
- Phase 1 D1 survival expansion: complete
- Phase 2 simple shop survival: complete
- Phase 3 coherent build evidence: complete
- Phase 4 resource semantics: complete
- Phase 5 live D1/D2 semantics: complete
- full deterministic Balatro suite green at the latest checkpoint
- sticky GAME_OVER restart semantics validated
- supervisor telemetry resilience validated

Do not stage Tune G or another live batch while this architecture diagnosis is active.

# Phase 6 — STRATEGY/BOND CAUSAL DIAGNOSIS — ACTIVE

## Historical architecture that must be understood first

The intended Bond system mirrors Honkai: Star Rail Currency Wars:

```text
Balatro component/state
  → weighted Bond development
  → mechanical roles / behavior descriptors
  → semantic links
  → candidate strategy / pinned composition
  → acquisition + preservation + execution preferences
```

Separate axes:

```text
Development = Bond R0–R5
Realization = DORMANT / PARTIAL / ACTIVE / MATURE
Commitment  = EXPLORATORY / FORMING / PINNED / ESTABLISHED / DOMINANT
```

A Bond is intended to be a persistent developable strategic axis, not an individual Joker and not necessarily a complete build. Named super-additive packages belong to motifs/compositions. Example: Baron is not a Bond; `Held Cards` is a Bond, while Baron + Mime + Steel Kings is a composition using several Bonds and exact component semantics.

This intent is useful context, but the current implementation may still fail to realize it correctly.

## Primary diagnostic question

For a real strategic state, **where is the first point at which the agent stops knowing what a competent Balatro player should know?**

Trace vertically:

```text
public state
→ exact Joker/card mechanics
→ Bond contributions
→ roles / produces / requires / scales_with / amplifies / transforms
→ semantic links
→ candidate strategies
→ commitment / pinned strategy
→ unmet feature goals / prescriptions
→ projected acquisition or replacement state
→ shop/pack/preservation valuation
→ final bounded decision
```

At each stage ask:
1. Is the relevant fact present?
2. Is it mechanically correct?
3. Is its directionality/condition preserved?
4. Does it create the right positive, negative, or neutral strategic consequence?
5. Is that consequence still present downstream?

The **first incorrect or missing stage owns the defect**. Do not patch a later consumer to compensate for missing upstream semantics.

## Representative trace suite — NEXT

Trace these before redesigning individual Bonds:

1. **Baron + Mime**
   - should recognize held-King payoff + held-effect retrigger interaction before Steel is present;
   - should seek useful King/Steel/Red-Seal/copy infrastructure through admitted choices;
   - should preserve Baron/Mime absent a materially stronger pivot;
   - should not reward unrelated axes merely because they produce fresh Bond ranks.

2. **Green Joker / No-Discard**
   - should recognize discard as engine damage;
   - should value compatible no-discard support;
   - should reject contradictory discard engines unless pivot benefit is materially stronger.

3. **Card Sharp / Hand Repetition**
   - should understand repeated-hand requirement;
   - shop/deck choices should support repeatability rather than merely add generic hand-type strength;
   - D1 should honor repetition when sufficiently safe.

4. **Vampire + enhancement feed**
   - should value renewable enhancement production as feed;
   - should distinguish feeding Vampire from preserving an incompatible Driver's License enhanced-card population;
   - conflict must survive composition and acquisition valuation.

5. **DNA + rank-dependent payoff**
   - duplication should satisfy the concrete required rank(s), not become generic deck-growth value only;
   - generated unmet goals must stay specific rather than broaden into arbitrary rank/card acquisition.

6. **Contradictory Frankenstein board**
   - construct a state containing individually positive but strategically incompatible axes;
   - verify the system penalizes/removes incoherent composition instead of rewarding aggregate Bond collection.

## Diagnostic verdict categories

For each trace, classify the first break as one of:

- `MECHANIC_MODEL` — exact component behavior is absent/wrong.
- `BOND_REPRESENTATION` — Bond identity/contribution loses essential strategic information.
- `ROLE_DESCRIPTOR` — roles/targets/conditions or behavior descriptors are absent/too weak.
- `SEMANTIC_LINKING` — compatible or conflicting mechanics fail to connect correctly.
- `STRATEGY_FORMATION` — correct links exist but candidate/commitment formation is wrong.
- `GOAL_PRESCRIPTION` — strategy exists but unmet needs/prescriptions are wrong or too generic.
- `PROJECTED_TRANSITION` — candidate post-buy/post-replacement state is evaluated incorrectly.
- `CONSUMER_VALUATION` — correct strategy evidence reaches D2/D4/D9/D14 but valuation ignores/misweights it.
- `FINAL_ARBITRATION` — correct upstream valuation is overridden incorrectly at the final authority.

This classification determines whether the next phase is Bond redesign, semantic-graph redesign, or a narrow consumer fix.

## Important non-conclusions

- `held_retrigger` is **not declared correct**.
- `held_retrigger` is **not declared invalid** merely because retriggering is mechanically an amplifier.
- The current 46-Bond catalogue, rank thresholds, relationships, motifs, and data model are not protected.
- Conversely, do not replace the Currency-Wars-derived architecture merely because live play is poor until the causal trace shows where it fails.

## Implementation freeze during diagnosis

Until the representative traces establish the first systematic break:
- do not tune Bond thresholds;
- do not redesign Bonds one-by-one;
- do not add late shop/preservation rescues;
- do not run another live tuning batch;
- do not stage Tune G;
- do not alter D1–D14 ownership without fresh trace evidence.

Small instrumentation or regression-only changes are allowed if required to expose the causal path, but prefer static code tracing first.

# EXACT NEXT ACTION

1. Read the strategy-system and relationships/motifs documents.
2. Trace **Baron + Mime** end-to-end through the current code.
3. Record the exact information present at every stage from component mechanics through D14/D9/D4/D2 consumption.
4. Identify the **first** stage that loses or distorts the strategically relevant causal information.
5. Repeat for No-Discard, Hand-Repetition, Vampire, DNA/rank payoff, and one contradictory-board case.
6. Compare failures. If they cluster at the same architectural layer, redesign that layer before individual Bond auditing.
7. Only after the architecture diagnosis is complete decide whether to KEEP/SPLIT/MERGE/REPLACE/DELETE individual Bonds such as `held_retrigger`.

# Phase order

1. Phase 0 — authority consolidation — COMPLETE
2. Phase 1 — D1 survival semantic expansion — COMPLETE
3. Phase 2 — simple shop survival — COMPLETE
4. Phase 3 — coherent build evidence/authority quality — COMPLETE
5. Phase 4 — complex packs/consumables/vouchers/economy audit — COMPLETE
6. Phase 5 — live validation — COMPLETE
7. Phase 6A — vertical strategy/Bond causal diagnosis — ACTIVE
8. Phase 6B — architecture correction based on diagnosis — BLOCKED
9. Phase 6C — action-quality validation/tuning — BLOCKED

Future stake/deck progression remains blocked until Red/White competence passes.
