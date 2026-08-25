# Balatro Mechanical Strategy Formation

Status: **Canonical runtime architecture**

This document defines the strategy-formation layer between raw Bond development and Balatro decisions.

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

The canonical flow is:

```text
public Balatro state
  -> exact modeled Joker/component mechanics
  -> raw Bond contributions + mechanical roles
  -> behavior descriptors
     (produces / requires / scales_with / amplifies / transforms)
  -> semantic links between mechanics + explicit exceptional interactions
  -> candidate strategies
  -> EXPLORATORY / FORMING / PINNED / ESTABLISHED / DOMINANT
  -> one bounded strategy-development feedback pass
  -> Bond realization + composition recomputed once
  -> unmet feature goals + known motif prescriptions
  -> acquisition / preservation / execution preference
  -> future public state provides new direct evidence
```

## Closed-world knowledge rule

Balatro's Joker catalogue is a finite ruleset. Strategy formation must therefore start from **explicitly correct Joker mechanics**, not from an artificial requirement that the system infer everything without knowing Joker identities.

The intended split is:

```text
Joker-specific knowledge:
  exact effect
  activation/condition
  reset/consumption behavior
  persistent state
  unique execution constraints

Reusable strategy reasoning:
  producer satisfies requirement
  producer feeds scaling
  copy/transform feeds a required feature
  amplifier/retrigger targets a payoff
  conflict/preservation/pivot logic
```

Do not build an exhaustive table of every useful Joker pair/triple when the interaction follows correctly from those exact mechanics. Conversely, do not preserve a generic abstraction when it fails to represent a known stable interaction: explicit motifs or interaction rules are valid when necessary.

Important known combinations and anti-combinations require explicit regression tests even if their runtime relationship is inferred generically. Examples include DNA feeding rank-dependent engines, Green Joker/Delayed Gratification enforcing no-discard behavior, and Card Sharp enforcing hand repetition.

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

Strategy formation uses complementary channels.

### Explicit Bond-role semantics

Bond contributions may carry mechanical roles, targets and conditions such as held-rank payoff, held retrigger, held-card XMult, density infrastructure, enhancement feed/payoff, deck-thinning engine/payoff, economy engine/payoff, hand-level engine/payoff, copy engine, and scaler.

Compatible roles form semantic links. Example:

```text
Baron: HELD_RANK_PAYOFF targeting Kings
Mime: HELD_RETRIGGER targeting held effects

=> RETRIGGER_AMPLIFIES_HELD_PAYOFF
```

### Behavior-backed semantics

The build profiler and Joker behavior analyzer are canonical inputs. They expose reusable descriptors from the explicitly modeled Joker behavior:

```text
produces
requires
scales_with
amplifies
transforms
```

This lets the strategy machine compose known mechanics without requiring an exhaustive hand-written Joker-pair strategy table.

Generic links include:

```text
producer output satisfies consumer requirement
producer output feeds consumer scaling
copy/transform output satisfies a concrete required feature
amplifier targets another component's output
```

Public deck/build features may provide infrastructure evidence, but ambient feature nodes alone are not allowed to create rank authority or pin a strategy without concrete cooperating sources. Merely sharing a target does not prove synergy.

## Known motifs are accelerators, not prerequisites

Known super-additive packages remain useful. They provide a canonical strategy name, explicit component checks, missing-piece distance, specialized prescriptions, and stronger confidence when partially assembled.

They do not replace generic semantic reasoning, and generic reasoning does not prohibit explicit motifs.

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

## Strategy pinning

Pinning is evidence-based and reversible.

A strategy may become pinned when a strong mechanical relationship exists or a known motif is meaningfully partially complete. Pinning does not make a strategy immortal.

A pinned strategy gains three forms of authority:

1. **Construction** — safe/admitted acquisitions that satisfy unmet strategy features receive bounded preference.
2. **Preservation** — D2 does not casually sell a component if the projected state destroys the pinned strategy or an ACTIVE/MATURE engine it materially supports.
3. **Execution** — strategy mechanics must influence actual D1/D13/pack/shop behavior when survival and legality permit.

Recognition without downstream execution is a defect. Examples: an ACTIVE No-Discard engine that still discards casually, an ACTIVE Hand-Repetition engine that avoids repeatable hands, or a strategy-aware D13 path whose readiness/opportunity inputs remain constant zero.

A replacement may still pivot away when the projected alternative strategy is materially stronger. Survival, legality, boss mechanics and lower-level action admissibility remain final constraints.

## Strategy-development feedback

Raw Bond evaluators remain local and independently inspectable. They do not receive strategy bonuses during the first evaluation pass.

After raw developments are composed, the runtime may apply exactly one bounded coherence reinforcement pass if a strategy is already pinned from genuine evidence.

```text
FORMING      -> no rank reinforcement
PINNED       -> coherence authority capped at R2
ESTABLISHED  -> coherence authority capped at R3
DOMINANT     -> coherence authority capped at R4
R5           -> direct catalogue evidence only
```

Additional constraints:

- one evaluation may advance a Bond by at most one rank beyond its raw rank;
- the Bond itself must participate in a semantic link through a concrete non-ambient source;
- `feature:...` deck/profile nodes cannot supply coherence rank authority;
- reinforcement is recorded as an explicit `Pinned strategy coherence: <strategy>` contribution;
- after reinforcement, realization and composition are recomputed exactly once;
- there is no recursive reinforcement pass.

The first pass remains non-circular:

```text
raw public evidence
  -> raw Bond ranks
  -> strategy must pin from those facts
  -> only then may proven coherence add bounded development authority
```

## Unmet feature goals

Behavior-backed candidates expose missing mechanical needs as:

```text
seek_feature:<feature>
```

These are derived from unsatisfied requirements, scaling inputs and amplifier/copy targets of the current strategy components.

They are not commands to buy arbitrary items. A candidate must first pass normal child-policy admission. The parent layer may then add bounded value when the admitted candidate directly produces/transforms an unmet feature.

Feature goals must remain specific. A rank-dependent strategy should not degrade into an all-ranks demand set that makes every Standard Pack appear strategically necessary.

## D2 transition value

Canonical D2 transition value must recognize strategy formation itself.

The transition layer gives bounded value when a candidate:

- forms a new pinned strategy;
- advances PINNED -> ESTABLISHED or higher;
- materially strengthens the same pinned strategy;
- pivots to a materially stronger pinned strategy.

Projected candidate states use the same two-pass Bond composition evaluation. This value remains capped inside the existing canonical Bond-transition budget.

A first isolated Bond foothold receives only small scouting value. Once any Bond engine exists, opening another unrelated axis is structural diversification and receives a penalty; deepening the existing Bond, creating a semantic synergy, advancing a known motif, or progressing the selected strategy receives the material transition reward. This prevents the shop from collecting unrelated R1 labels instead of assembling a functioning Joker engine.

A fresh low-rank Bond label must not automatically outweigh an incumbent's already-realized engine state. `LOCKED -> R1` is one rank of development, not two, and raw composition-score growth is not itself proof of coherence. Replacement scoring must preserve the value of ACTIVE/MATURE Bonds and pinned strategy components unless the projected replacement is materially better.

## Observability

Diagnostics expose strategy formation separately from compact R1+ Bond diagnostics.

For each candidate the runtime can report strategy ID, commitment, confidence, strength, contributing Bonds, source components/features, semantic links, known motifs, prescriptions/unmet goals, and whether the candidate is pinned.

Reinforced Bond rows expose their explicit strategy-coherence contribution, so live logs can distinguish direct catalogue development from composition support.

## Acceptance examples

The implementation is not acceptable unless it can demonstrate both named and generic composition cases.

### Baron / Mime / Steel / Kings

1. Baron alone exposes a held-King payoff direction.
2. Baron + useful King infrastructure increases confidence.
3. Baron + Mime is recognized as a coherent held-effect engine before Steel is present.
4. The motif can become pinned while still `POTENTIAL`.
5. Once pinned, the agent seeks compatible Kings/Steel/Red-Seal/copy support through normal safe policies.
6. D2 does not sell Baron or Mime for an isolated local upgrade if that destroys the pinned engine.
7. A genuinely stronger projected strategy can still justify a pivot.

### Cross-layer execution

1. DNA + a rank-dependent payoff recognizes that duplication can feed the required rank(s), without requiring a bespoke pair rule for every payoff.
2. DNA first-hand execution prefers a strategically required rank only when the blind remains sufficiently safe.
3. Green Joker or another realized No-Discard engine causes D1 to avoid damaging discards when a viable play exists.
4. Card Sharp/Hand-Repetition causes D1 to prefer an already-played hand type when a viable repeat exists.
5. D13 receives actual translated state and non-placeholder readiness/opportunity evidence.
6. Important known interactions have direct regressions even when implemented through generic semantics.

## Tuning boundary

Optuna remains frozen while semantic/execution contradictions are known.

Numerical optimization must not compensate for missing understanding. The order is:

```text
explicit Joker mechanics correct
  -> semantic composition correct
  -> strategy formation/pinning correct
  -> development feedback correct
  -> execution/preservation correct
  -> rank reachability/calibration validated
  -> live behavior validated
  -> only then numerical optimization
```
