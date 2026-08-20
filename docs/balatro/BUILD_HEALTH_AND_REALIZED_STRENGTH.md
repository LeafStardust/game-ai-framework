# Balatro Build Health and Realized Strength

This document defines the next decision-quality layer for the Red Deck / White Stake agent. It complements the strategy topology in `BALATRO_STRATEGY_TREE.md` and the strategy/evidence rules in `BALATRO_STRATEGY_TREE_RULES.md`.

The problem this layer solves is simple: **owning five individually useful Jokers is not the same as owning a functioning build**. Strategy evidence says what a run is trying to become; Build Health says whether that build is actually surviving, functioning, and scaling quickly enough to finish the run.

## 1. Decision hierarchy

The agent should reason in this order:

1. **Can the current run survive the next blind?**
2. **Is the current build actually functioning?**
3. **Is it scaling quickly enough for the next one to two Antes?**
4. **Which strategy is currently the best realized route?**
5. **Which action or missing component most improves that realized build?**
6. **Would an alternative route be stronger after transition cost and required buildup?**
7. Execute the best legal action.

Strategy purity never overrides survival. A strategy is useful only if the run lives long enough to realize it.

## 2. Build Health

`BuildHealth` is a normalized 0–100 diagnostic and decision input composed from five independently auditable dimensions:

- **Survival** — projected ability to clear the next blind/boss from the current state.
- **Immediate scoring** — current scoring output relative to present blind requirements.
- **Scaling** — realized growth rate and multiplicative/scaling capacity relative to future blind growth.
- **Coherence** — how much of the current Joker/card/consumable board reinforces the same Primary/Secondary build instead of acting as disconnected filler.
- **Runway** — whether engines that still require buildup have enough remaining time/resources to become useful before the run outgrows them.

The initial aggregate may be weighted, but every component must remain visible in logs and the live monitor. The aggregate must never hide a critical zero/near-zero survival state.

Example diagnostic:

```text
Build Health : 58
Survival     : 82
Immediate    : 74
Scaling      : 31
Coherence    : 67
Runway       : 40

Warnings:
- Hologram x1.0 — inactive scaler
- Ante 5 scaling deficit
```

## 3. Survival adequacy

Antes 1–2 are primarily survival/flexibility stages.

A Joker is not an adequate survival purchase merely because its immediate scoring contribution is positive. The agent must ask whether the purchase materially improves the projected probability of clearing the next blind or boss.

Rules:

- Off-route immediate scorers may be purchased in Antes 1–2 when survival needs them.
- Strategy alignment is a preference/tiebreaker during this phase, not a veto.
- If one weak scorer does not make the next blind sufficiently survivable and another affordable scorer is available, the agent may continue strengthening immediate survival.
- Reserve/economy constraints still matter, but preserving cash must not knowingly walk the run into a likely loss.
- A non-scoring utility Joker does not satisfy the survival requirement merely by occupying a Joker slot.

The exact survival threshold should be derived from the existing whole-blind clear-probability model rather than from a separate arbitrary scoring scale.

## 4. Realized engine strength

Every strategy-relevant engine has two separate concepts:

- **Catalogue relationship** — how strongly the item belongs to a strategy in principle.
- **Realized engine strength** — how much that engine is actually contributing now and how quickly it is progressing.

The runtime must distinguish at least:

```text
NOT_OWNED
OWNED_INACTIVE
ACTIVATED_WEAK
ACTIVATED_HEALTHY
MATURE
```

An engine may be Gold/Silver catalogue evidence while still being `OWNED_INACTIVE` in realized state.

Examples:

- **Hologram x1.0**: owned but inactive; should create pressure to add playing cards or eventually replace/pivot if no realistic activation path exists.
- **Blue Joker**: realized strength depends on actual remaining deck size; card generation can strengthen it immediately.
- **Burnt Joker**: realized development depends on useful first-discard hand upgrades actually occurring without sabotaging survival.
- **Castle**: realized development depends on accumulated chips and safe opportunities to discard the current suit.
- **Green Joker**: realized strength depends on current Mult and whether the current tactical plan can preserve/grow it without sacrificing survival.
- **Red Card**: realized scaling depends on packs actually being skipped when the skip value beats the pack contents.
- **Runner**: a nominally strong Straight scaler may have low realized strength when acquired late with no historical buildup.
- **Bull/Bootstraps**: can have high realized strength immediately when current cash already makes the engine strong; it does not require historical buildup in the same way as Runner.

## 5. Scaling adequacy

From Ante 3 onward, the agent must judge whether the current build is keeping pace with blind growth.

A scaling deficit exists when the current board can still clear some present blinds but its projected scoring trajectory is unlikely to keep pace with the next one to two Antes.

Under scaling deficit pressure, the shop system should prefer actions that materially improve the build's future scoring trajectory, including:

- activating an owned inactive scaler;
- buying a multiplicative/scaling engine compatible with the current route;
- replacing filler or weak additive support with a stronger realized engine;
- rerolling when the current board lacks adequate scaling and the bankroll can safely support search;
- pivoting to a mature alternative route whose current-state strength exceeds the existing build after transition cost.

A full 5/5 Joker roster is not evidence of a healthy build.

## 6. Build component roles

Every owned Joker should be classified relative to the active build as one of:

- **CORE** — defining scoring/win-condition component.
- **ENGINE** — component that materially scales or activates the route.
- **SUPPORT** — consistency/economy/deck-shaping component that materially reinforces the route.
- **FILLER** — positive generic value but not important to the realized route.
- **CONFLICT** — mechanically harmful to the realized route.

Replacement priority is structural:

1. CONFLICT
2. FILLER
3. weaker same-route SUPPORT
4. weaker same-route ENGINE when a stronger immediate same-route upgrade exists
5. CORE only as part of an explicit, sufficiently mature pivot

Committed Gold/Silver components remain protected unless the replacement is an immediate stronger same-route upgrade or the whole build is explicitly pivoting.

## 7. Realized strategy maturity and pivot cost

Strategy commitment must consider both catalogue evidence and realized strength.

A strategy with strong theoretical relationships but weak current activation must not automatically beat a route that is already producing sufficient score.

Pivot evaluation should compare:

```text
realized candidate strength
+ immediate synergy
+ current deck/resource compatibility
+ short-horizon growth
- transition cost
- required future buildup
- risk to current blind survival
```

Examples:

- **Bull + Bootstraps with high current cash** can be an easy late pivot because most of the power is realized immediately.
- **Runner acquired late with no Straight buildup** should pay a large runway/buildup penalty even though Runner is a strong Straight engine in principle.
- A new Gold same-route Joker may replace a Silver same-route component only when the resulting current build is already stronger and does not jeopardize survival through required buildup.

## 8. Short-horizon transition planning

The shop/pack planner should support bounded multi-action reasoning where a sequence materially changes build quality.

Initial supported patterns should include:

- `sell filler -> buy stronger same-route Joker`;
- `buy card generator -> activate Hologram/Blue growth`;
- `sell expendable Jokers -> use Ankh`;
- `buy Bull -> buy Bootstraps` or the reverse when the pair is jointly strong at current cash;
- `buy component -> re-observe -> buy complementary component` within the same shop when legal and affordable.

This is not unrestricted combinatorial search. Use a small public-information horizon and reuse existing affordability/reserve/survival guards.

## 9. Interaction with strategy phases

### Antes 1–2: Foundation

Priority: **survive and remain flexible**.

- survival adequacy dominates strategy purity;
- immediate scoring purchases may be off-route;
- early evidence may guide choices but should not cause the agent to reject necessary survival strength;
- inactive long-horizon engines should not be treated as sufficient immediate defense.

### Antes 3–5: Convergence

Priority: **turn survival pieces into a coherent scaling build**.

- Build Health and scaling adequacy become strong shop inputs;
- inactive engines create activation pressure;
- filler should be replaced as stronger aligned engines appear;
- reroll/search pressure increases when scaling is behind schedule;
- pivots remain legal when the new route is materially stronger after buildup/runway cost.

### Ante 6+: Commitment

Priority: **execute and strengthen the realized Primary build**.

- committed build structure is protected;
- incompatible route-bound filler is aggressively deprioritized;
- pivots require decisive realized advantage and acceptable transition risk;
- theoretical ceiling without enough runway is not sufficient;
- survival remains the final override.

## 10. Observability requirements

The live monitor and structured logs should expose:

- Build Health aggregate;
- Survival;
- Immediate scoring;
- Scaling;
- Coherence;
- Runway;
- Primary realized strategy;
- owned CORE/ENGINE/SUPPORT/FILLER/CONFLICT components;
- inactive/underperforming engine warnings;
- scaling-deficit warning;
- pivot reason and transition-cost rationale when a pivot is selected.

This is necessary so five-run calibration can distinguish:

- the model correctly detecting a weak build but failing to act;
- the model incorrectly believing the build is healthy;
- ordinary RNG losses after otherwise sound decisions.

## 11. Implementation sequence

Implement in this order, with regression tests before each behavior change:

1. `BuildHealth` data model and pure evaluator.
2. Realized engine-strength descriptors for a small initial engine set: Hologram/Blue growth, Burnt Joker, Castle, Green Joker, Red Card, Runner, Bull/Bootstraps.
3. Survival-adequacy calculation for early Joker acquisition using existing whole-blind clear probability.
4. Scaling-deficit detection and diagnostics.
5. Shop acquisition/replacement/reroll integration using Build Health deltas.
6. Realized-maturity-aware pivot evaluation with buildup/runway cost.
7. Bounded short-horizon bundle/transition planner.
8. Live monitor and structured-log fields.
9. Deterministic regression suite.
10. Fresh unchanged-HEAD five-run Red/White validation batch.

Do not start with per-Joker score inflation. The point of this layer is to make the permanent decision system reason about whether the current build works, rather than to accumulate more isolated exceptions.

## 12. Release criterion impact

This work remains part of the Red/White `1.0.x` calibration line because it corrects the competence model used by the already-released Red/White agent. It is not Red Stake-specific functionality and should be complete and validated before Red/Red `1.1.0` development begins.
