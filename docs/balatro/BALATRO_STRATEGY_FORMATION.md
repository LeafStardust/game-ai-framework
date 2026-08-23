# Balatro Mechanical Strategy Formation

Status: **Canonical runtime architecture**

This document defines the missing strategy-formation layer between raw Bond development and Balatro decisions.

## Why this layer exists

Bond rank is a measurement of development. It is not permission to notice a strategy.

The previous implementation made strategy recognition too dependent on R1+ Bond selection and ACTIVE/MATURE motifs. That created a circular failure:

```text
engine pieces appear
  -> Bonds have not ranked/realized enough
  -> motif has no authority
  -> agent does not pursue missing pieces
  -> engine never develops enough
```

A competent Currency-Wars-style agent must recognize what mechanics imply before the package is complete.

The canonical flow is now:

```text
public Balatro state
  -> Bond contributions + mechanical roles
  -> behavior-backed effect descriptors
     (produces / requires / scales_with / amplifies / transforms)
  -> semantic links between mechanics
  -> candidate strategies
  -> EXPLORATORY / FORMING / PINNED / ESTABLISHED / DOMINANT
  -> unmet feature goals + known motif prescriptions
  -> acquisition / preservation / execution preference
  -> Bond development and realization continue to measure how far the engine has progressed
```

## Rank and strategy commitment are separate

The axes are deliberately independent:

```text
Bond rank
R0 -> R1 -> R2 -> R3 -> R4 -> R5
    measures development of one strategic axis

Strategy commitment
EXPLORATORY -> FORMING -> PINNED -> ESTABLISHED -> DOMINANT
    measures confidence/commitment to a coherent multi-mechanic plan

Realization
DORMANT -> PARTIAL -> ACTIVE -> MATURE
    measures whether a developed mechanic is currently functioning
```

Positive R0 evidence is allowed to participate in strategy formation. R0 must not be strategically invisible.

R1+ remains relevant for established Bond authority, rank prescriptions and pivot resistance. It is no longer a prerequisite for understanding what the pieces can become.

## Semantic evidence channels

Strategy formation uses two complementary channels.

### Explicit Bond-role semantics

Bond contributions may carry mechanical roles, targets and conditions such as:

- held-rank payoff;
- held retrigger;
- held-card XMult;
- density infrastructure;
- enhancement feed/payoff;
- deck-thinning engine/payoff;
- economy engine/payoff;
- hand-level engine/payoff;
- copy engine;
- scaler.

Compatible roles form semantic links. Example:

```text
Baron: HELD_RANK_PAYOFF targeting Kings
Mime: HELD_RETRIGGER targeting held effects

=> RETRIGGER_AMPLIFIES_HELD_PAYOFF
```

### Behavior-backed semantics

The existing build profiler and Joker behavior analyzer are also canonical inputs. They infer reusable descriptors from modeled Joker behavior:

```text
produces
requires
scales_with
amplifies
transforms
```

This lets the strategy machine infer relationships without an exhaustive hand-written Joker-pair table.

Examples of generic links include:

```text
producer output satisfies consumer requirement
producer output feeds consumer scaling
amplifier targets another component's output
```

Public deck/build features are also infrastructure nodes, so a payoff Joker can form a strategy with useful rank/suit/enhancement/hand-level state before a second Joker appears.

## Known motifs are accelerators, not prerequisites

Known super-additive packages remain useful. They provide:

- a canonical strategy name;
- explicit component checks;
- missing-piece distance;
- specialized prescriptions;
- stronger confidence when partially assembled.

They do not replace generic semantic reasoning.

A motif may be only `POTENTIAL` while the corresponding strategy is already `PINNED`.

Canonical example:

```text
Baron + Mime
  -> Baron-Mime-Steel motif is POTENTIAL
  -> 2/4 defining components are already present
  -> semantic Baron/Mime link exists
  -> strategy may be PINNED
  -> agent may already seek Kings, Steel, Red Seal and compatible copy/held-effect support
```

The agent no longer waits for the held-card, held-retrigger, Steel and King Bonds all to become ACTIVE before deciding that the package is strategically meaningful.

## Strategy pinning

Pinning is evidence-based and reversible.

A strategy may become pinned when a strong mechanical relationship exists or a known motif is meaningfully partially complete. Pinning does not make a strategy immortal.

A pinned strategy gains three forms of authority:

1. **Construction** — safe/admitted acquisitions that satisfy unmet strategy features receive bounded preference.
2. **Preservation** — D2 does not casually sell a component if the projected state destroys the pinned strategy.
3. **Execution** — known motif prescriptions associated with the pinned strategy may steer already-safe pack/shop choices before the motif is fully ACTIVE.

A replacement may still pivot away when the projected pinned strategy is materially stronger. Survival, legality, boss mechanics and lower-level action admissibility remain final constraints.

## Unmet feature goals

Behavior-backed candidates expose missing mechanical needs as:

```text
seek_feature:<feature>
```

These are derived from unsatisfied requirements, scaling inputs and amplifier targets of the current strategy components.

They are not commands to buy arbitrary items. A candidate Joker must first pass normal D2 admission. The parent shop layer may then add only bounded value when that admitted candidate directly produces/transforms an unmet feature.

This keeps the strategy layer proactive without bypassing affordability, resource, replacement or survival rules.

## D2 transition value

Canonical D2 transition value must recognize strategy formation itself.

The old transition bonus looked mainly at Bond rank/progress and composition coherence. That could undervalue a Joker which completed a mechanically coherent pair without crossing a rank threshold.

The transition layer now also gives bounded value when a candidate:

- forms a new pinned strategy;
- advances PINNED -> ESTABLISHED or higher;
- materially strengthens the same pinned strategy;
- pivots to a materially stronger pinned strategy.

This value remains capped inside the existing canonical Bond-transition budget.

## Observability

Diagnostics expose strategy formation separately from compact R1+ Bond diagnostics.

For each candidate the runtime can report:

- strategy ID;
- commitment state;
- confidence;
- strength;
- contributing Bonds;
- source components/features;
- semantic links and their relation types;
- known motif IDs;
- prescriptions/unmet feature goals;
- whether the candidate is currently pinned.

This separation is intentional: R0 evidence can explain why a strategy is forming without pretending the corresponding Bond has already reached R1.

## Baron / Mime / Steel / Kings acceptance example

The implementation is not acceptable unless it can demonstrate all of the following:

1. Baron alone exposes a held-King payoff direction.
2. Baron + useful King infrastructure increases confidence in that direction.
3. Baron + Mime is recognized as a coherent held-effect engine even before Steel is present.
4. The known Baron-Mime-Steel package can become pinned while still `POTENTIAL`.
5. Once pinned, the agent seeks compatible Kings/Steel/Red-Seal/copy support through normal safe policies.
6. D2 does not sell Baron or Mime for an isolated local upgrade if that sale destroys the pinned engine.
7. A genuinely stronger projected strategy can still justify a pivot.
8. As infrastructure accumulates, Bond ranks and realization rise independently and describe development/function rather than gate recognition.

## Tuning boundary

Optuna remains frozen until this semantic machine is validated.

Numerical optimization must not compensate for missing understanding. The correct order is:

```text
mechanical semantics correct
  -> strategy formation/pinning correct
  -> execution/preservation correct
  -> rank reachability/calibration validated
  -> only then numerical optimization
```
