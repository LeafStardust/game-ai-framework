# Balatro Strategy System

Canonical architecture contract for the Red/White Balatro strategy redesign.

## 1. Mental model — Currency Wars analogue

The intended abstraction deliberately mirrors Honkai: Star Rail Currency Wars closely enough that future maintainers should use it as the primary mental model:

```text
Currency Wars character        = Balatro Joker/card/persistent state
Currency Wars Bond             = Balatro strategy track (Bond)
Bond quota/rank                = weighted contribution + Bond rank
Currency Wars player strategy  = Balatro candidate engine / pinned composition
```

In Currency Wars, one character can add quota to multiple Bonds; the player assembles whatever Bond mixture RNG permits, tries to raise useful Bonds as high as practical, and may pin/follow a strategy that combines several Bonds into a coherent power plan. Balatro does not expose Bond labels or quota itself, so this system infers them from actual Balatro mechanics.

The same principles apply here:

- one Joker/card/state source may contribute to several Bonds;
- contributions are Bond-specific and weighted rather than uniform;
- Bonds develop independently and have ranks;
- RNG means the agent cannot demand one predetermined build;
- a high-rank useful Bond is a strong strategic foundation but not a guaranteed win;
- several compatible Bonds may be combined when no single Bond can be maximized;
- strategy recognition must happen from mechanics before an engine is already complete;
- known super-additive combinations are represented as motifs above the Bond layer, but motifs are accelerators/templates rather than the only source of strategy understanding.

Example: Baron is not a Bond. `Held Cards` is. Baron + Mime + Steel Kings is a candidate/pinned composition built from Held Cards, Held Retrigger, Steel and relevant King/card structure.

The final architecture is therefore:

```text
Balatro public components/state
      ↓
Bond contributions + mechanical roles
      + behavior-backed produces/requires/scales/amplifies/transforms
      ↓
semantic links between mechanics
      ↓
candidate strategies
      ↓ EXPLORATORY / FORMING / PINNED / ESTABLISHED / DOMINANT
pinned composition + unmet feature goals / motif prescriptions
      ↓
acquisition + preservation + execution preferences

in parallel:
Bond contribution
      ↓ independent R0-R5 development
Bond realization
      ↓ DORMANT / PARTIAL / ACTIVE / MATURE
      ↓
rank/realization authority + pivot resistance + Build Health
```

No categorical primary/secondary hierarchy exists in the canonical architecture.

The detailed strategy-formation contract is [`BALATRO_STRATEGY_FORMATION.md`](BALATRO_STRATEGY_FORMATION.md).

## 2. Bond admission

A Bond is a persistent, developable strategic axis. A candidate should normally satisfy most of:

- further investment can meaningfully develop it;
- multiple components or persistent state features can contribute;
- greater development materially improves the plan;
- greater development changes acquisition, deck shaping or execution.

A single defining Joker may establish a Bond when owning it creates a deep strategic axis that other components/state can develop. Burnt is the canonical example.

Do not make every Joker, famous build or mechanic a Bond. Exact packages such as PhotoChad or Baron-Mime-Steel belong above Bonds as motifs/compositions. Support-only mechanics such as generic hand size or a card enhancement type should remain contributors/state unless they have an independent developable power plan.

## 3. Bond unlock vs Bond rank

A Bond may have a **hard unlock prerequisite** when the strategic axis literally does not exist without a defining component.

Canonical example:

```text
Burnt Joker absent  -> Burnt Bond LOCKED
Burnt Joker owned   -> Burnt Bond unlocked and eligible for R1+
```

`LOCKED` and `R0` are distinct:

```text
LOCKED = defining prerequisite absent; support/history cannot create the Bond
R0     = Bond is valid/unlocked but contribution has not reached R1
```

Once a Bond is unlocked, higher ranks are reached through weighted contribution. Do not turn individual contributors into sequential rank keys.

Wrong:

```text
R1 requires Burnt
R2 requires Telescope
R3 requires Blueprint
```

Correct:

```text
Burnt unlock prerequisite satisfied
        ↓
all legitimate Burnt contributors add weighted contribution
        ↓
contribution thresholds determine R1-R5
```

Therefore Telescope may strongly advance Burnt without becoming a gate that prevents a different Burnt build from reaching R2/R3 through Blueprint, Brainstorm, Blue Seal infrastructure, permanent target-hand development, or another legitimate route.

Hard unlock prerequisites should be rare and mechanically defining. Many Bonds may need no special unlock at all because their underlying strategic axis can emerge gradually from ordinary state.

Do not use rank-specific hard conditions merely to prove that a Bond is functioning. Functional conditions belong primarily to **Realization**. Rank measures development.

**R0 is not strategically invisible.** Positive R0 mechanical evidence may participate in candidate-strategy formation. R1 remains the threshold for established Bond-level authority; it is not permission to notice what a component does.

## 4. Weighted contribution

Every contributor receives its own Bond-specific numerical contribution. One component may contribute different amounts to several Bonds:

```text
component -> Bond A +x
          -> Bond B +y
          -> Bond C +z
```

Contribution means `how much this component genuinely develops this Bond`, not global strategy commitment and not direct scoring power.

Sources may include Jokers, permanent deck composition, rank/suit density, enhancements, seals, hand levels, permanent card upgrades, accumulated scaler state, consumable infrastructure and other persistent public state. Current-hand accidents are tactical state, not Bond development.

State/density contribution should use mechanically appropriate bands/caps/conditions rather than unbounded per-card inflation.

Permanent additions remain permanent contribution while they remain in game state. Dynamic sources disappear when sold/destroyed. Eternal/otherwise locked components remain contribution while present. No artificial historical Bond decay exists; recalculate from actual state. Historical counters may deepen an unlocked scaler when the current payoff still exists, but history alone must not keep a defining-payoff Bond alive after that payoff disappears.

## 5. Five-rank framework

Use approximately five standardized development ranks:

```text
R1 Emerging
R2 Established
R3 Strong
R4 Power-engine capable
R5 Capstone / maximum strategic commitment
```

Each Bond defines its own optional hard unlock prerequisite(s), weighted contributors, numerical R1-R5 thresholds, and effects/prescriptions strengthened at each rank.

Threshold geometry does not need to be identical between Bonds. Density mechanics such as Steel can differ from defining-Joker mechanics such as Burnt.

Generic rank authority increases with rank: R1 is opportunistic recognition; R2 begins meaningful reinforcement/basic prescriptions; R3 protects and actively develops the Bond; R4 may serve as a power engine and strongly influences decisions; R5 is capstone commitment. The Bond-specific rank definition says exactly what that authority means for that mechanic.

Rank is intentionally numerical/developmental. Do not smuggle execution tests back into R2-R5 as arbitrary gates.

Rank thresholds must also be demonstrably reachable under realistic states. R1-R5 calibration is invalid until reachability is measured from the actual contributor economy of each Bond.

## 6. Development rank is not realization or strategy commitment

There are three independent axes:

```text
Development = weighted contribution total + R0..R5
Realization = DORMANT / PARTIAL / ACTIVE / MATURE
Strategy commitment = EXPLORATORY / FORMING / PINNED / ESTABLISHED / DOMINANT
```

Development says what has been assembled/invested in one Bond. Realization says whether that developed mechanic is actually functioning in the current environment. Strategy commitment says whether several mechanics already form a coherent plan worth pursuing/preserving.

Example: Steel may be R4 structurally but only PARTIAL until enough useful Steel cards are actually held/triggered by the current plan. Conversely, Baron + Mime may already create a PINNED candidate held engine while some supporting Bonds are still R0/R1 and the full Baron-Mime-Steel motif is only POTENTIAL.

```text
UNLOCK       Does this Bond exist for this run?
RANK         How developed is one Bond?
REALIZATION  Is that developed mechanic functioning now?
COMMITMENT   Is the combined mechanical plan worth pursuing/preserving?
BUILD HEALTH Is the resulting run strong enough to survive/scale?
```

These axes must not gate each other circularly.

## 7. Mechanical strategy formation

The canonical composer must reason from what components **do**, not only from their Bond point totals.

Two semantic channels are authoritative:

1. explicit enriched Bond contribution roles/targets/conditions;
2. behavior-backed build descriptors: `produces`, `requires`, `scales_with`, `amplifies`, `transforms`.

Generic relationships such as output-satisfies-requirement, output-feeds-scaling, and amplifier-targets-output create semantic links. Connected evidence forms candidate engines. Known motifs may label/accelerate those candidates.

Candidate strategy formation deliberately evaluates all positive mechanical evidence, including R0. It must be possible to recognize a useful direction before the corresponding Bond ranks are high.

A PINNED candidate gains bounded authority to:

- seek currently unmet mechanical features through already-legal/admitted shop and pack choices;
- protect current components from destructive local replacements;
- apply known motif prescriptions before the motif is fully ACTIVE;
- preserve held engine cards in D1 among safe/near-equivalent actions.

Pinning never overrides legality, affordability, boss correctness, exact survival constraints, or a materially stronger scoring line. A materially stronger projected pinned strategy may justify a pivot.

## 8. Sparse Bond relationships

Do not build an exhaustive pair matrix.

```text
default relationship = NEUTRAL
explicit relationships = SYNERGY or CONFLICT only
```

Only store relationships that materially matter. Complex/super-additive combinations belong to motifs rather than adding more relationship tiers. A Bond-level mechanical contradiction should normally be represented as CONFLICT so contradictory Bonds are not composed into the same build.

Generic strategy understanding should come from semantic roles/behavior descriptors, not an exhaustive hand-written Joker-pair table.

## 9. Composition motifs

A motif is a known strategy/composition whose value cannot safely be represented by additive Bond development alone. It is analogous to a named Currency Wars player strategy, not another Bond.

Motifs may be `POTENTIAL -> ACTIVE -> MATURE` and can define prerequisites, super-additive synergy, bridge components, missing-piece distance, special prescriptions and realized gates.

Canonical example:

```text
Baron + Mime + Steel Kings
  Held Cards
  Held Retrigger
  Steel
  relevant King/card concentration
        -> Baron-Mime-Steel motif
```

A motif is no longer required to be ACTIVE before it can matter strategically. Meaningfully partial motif evidence may help a semantic candidate become PINNED. For example, Baron + Mime is already 2/4 of the named package and a direct held-payoff/retrigger semantic match; it may therefore pin while Steel/King infrastructure is still missing.

## 10. Prescription resolution

Do not create a second complicated prescription-conflict subsystem.

- Bond-level contradictions -> CONFLICT -> do not compose.
- Compatible Bond prescriptions -> combine.
- unusual/super-additive combination behavior -> motif prescription.
- generic unmet needs -> `seek_feature:<feature>` from behavior semantics.
- immediate survival -> final authority and may override strategic prescriptions.

Runtime prescription authority is **bounded preference beneath existing child-policy legality/safety**. It may increase the score of an already-admitted pack/shop option, but it must never make an unsupported, deferred, unaffordable, illegal, or child-policy-rejected action autonomous-safe.

Prescription matching must use canonical semantics rather than fragile display spelling. Equivalent live representations of consumable names, Planet target-hand labels, face-rank aliases, Steel enhancements, and Red/Blue Seals should resolve to the same prescription.

## 11. Multi-Bond contributors and slot efficiency

A component that advances several relevant Bonds is strategically valuable because one Joker slot can develop several parts of the combined build.

Its shop/build value should consider progress added to relevant Bonds, useful thresholds crossed, candidate-strategy formation/commitment, motifs activated/advanced, synergy, slot efficiency, replacement/transition cost, and actual immediate scoring/economic value separately.

Do not convert overlapping Bond contribution into imaginary scoring power. Bond ranks are structural information, not additive score estimates.

A D2 candidate that forms or materially advances a pinned strategy must receive bounded transition value even when no Bond rank crosses on that exact transaction.

## 12. Pivot and transition

Potential high-ceiling Bonds/motifs must not automatically destroy a functioning build.

Track strategy/motif development roughly as:

```text
EXPLORATORY -> FORMING -> PINNED -> ESTABLISHED -> DOMINANT
POTENTIAL -> ACTIVE -> MATURE
```

Pivot evaluation considers current realized build power, current pinned strategy, new potential/realized power, useful thresholds crossed, motif synergy, deck compatibility, missing pieces, money/slots, abandoned value, reshaping/buildup time, remaining runway and survival risk.

Existing rank creates pivot resistance: R1/R2 cheap to abandon; R3 meaningful transition cost; R4 strong resistance; R5 very strong resistance. This is a cost, never a lock.

A pinned strategy also creates structural retention authority before R4/R5. D2 must project the post-replacement composition. If an isolated upgrade destroys the pinned engine and does not form a materially stronger pinned strategy, hold the incumbent.

The canonical runtime pivot authority compares projected combined-build coherence/distance against explicit realized-structure disruption and applies a Strategy-Health-dependent minimum net gain. SURVIVE/REPAIR permit lower-gain pivots than HOLD/REINFORCE/EXPLOIT; stronger functioning builds therefore require materially better replacements before disruption is accepted.

Do not double-count motif state outside composition coherence. Explicit disruption may still penalize loss of active/mature motifs and pivot resistance because dismantling already-realized machinery carries transition risk not captured by a symmetric coherence delta.

Pivot authority only overrides the lower-level acquisition decision when the public live state proves the Joker roster is full and the candidate transition is already an eligible positive D2 option. Missing, zero, negative, or invalid Joker-slot telemetry is unknown state, not evidence of a full roster; the lower-level policy remains authoritative in that case.

## 13. Build Health integration

Bond rank answers what has been built. Candidate strategy/commitment answers what coherent plan is being pursued. Build Health / score projection answers whether it actually clears, is powerful enough now, and is scaling fast enough.

Never sum Bond ranks or strategy commitment into build power.

```text
components/state
  -> Bond contributions + behavior semantics
  -> Bond ranks + realization
  -> candidate/pinned strategy + motifs
  -> intended engine/prescriptions

actual Balatro mechanics + intended engine
  -> score / whole-blind clear projection

combined-build coherence + realization + score projection
  -> Build Health
```

D1 and production SHOP Build Health should share the same **whole-blind clear-probability semantics** rather than two incompatible definitions of survival. D1 begins from the actual visible hand. SHOP has no next opening hand, so it constructs only bounded possibilities from the unordered public owned-deck composition and runs narrow node-capped D1 planning from those hypothetical openings. Serialized future draw order and hidden RNG remain prohibited.

The SHOP projection is advisory and bounded. Failure to complete all sampled openings falls back to the generic Build Health capacity estimator rather than renormalizing partial samples or blocking SHOP. Custom/injected scorers remain on the generic path. This keeps the permanent live agent probability-aware without coupling offline evaluator contracts to production D1 infrastructure.

## 14. D1 execution authority

Survival and pace remain above strategy shaping.

A pinned held-oriented strategy may assign preservation value to cards such as held Kings/Queens/Steel and additional Red-Seal retrigger infrastructure. This value is a tie-break/safe-equivalent preference only.

The final safe-pace chooser must not bypass strategy-aware ranking entirely. Current implementation permits the pinned strategy to choose among pace-qualified plays only when their projected score is within a narrow 98% equivalence band of the strongest pace-qualified play. A materially stronger scoring line remains mandatory. Under-pace plays never enter the strategy equivalence pool.

This prevents both failure modes:

```text
wrong: play away Baron/Mime held-engine cards when an essentially equal safe play exists
wrong: preserve engine cards so greedily that the current blind is lost
```

## 15. Observability contract

Live monitor should show only relevant Bonds; full telemetry may retain all Bond states.

Per relevant Bond expose approximately:

```text
Held Cards
Rank         : R4
Contribution : 17.5 / 21.0 -> R5
Realization  : ACTIVE
```

Locked defining-component Bonds should not clutter normal output; full telemetry may retain their locked state.

Strategy diagnostics are separate from compact R1+ Bond diagnostics because candidate formation may use R0 evidence. Expose approximately:

```text
Pinned strategy : baron_mime_steel
Commitment      : PINNED
Confidence      : 0.xx
Sources         : Baron, Mime, ...
Links           : RETRIGGER_AMPLIFIES_HELD_PAYOFF, ...
Missing goals   : seek_feature:..., ...
```

Composition telemetry should also expose motifs, synergies, conflicts and prescriptions. Shop/action telemetry should explain bounded strategy-transition, unmet-feature, retention and D1 preservation effects without flooding the monitor with dormant R0/locked Bonds.

## 16. Architecture maintenance order

1. Freeze and audit the Bond catalogue, including hard unlock prerequisites.
2. Define/audit weighted component/state contributions and explicit mechanical roles.
3. Validate behavior-backed `produces/requires/scales_with/amplifies/transforms` coverage.
4. Form candidate strategies from positive mechanical evidence, including R0.
5. Validate pinning/commitment and important known motifs such as Baron-Mime-Steel.
6. Wire pinned strategy authority through D1, D2, shop, packs, deck shaping and replacement preservation beneath survival/legality.
7. Define/audit per-Bond R1-R5 thresholds and prove rank reachability against realistic contributor ranges.
8. Define realization rules separately from rank progression and strategy commitment.
9. Define sparse SYNERGY/CONFLICT edges only where mechanically necessary.
10. Integrate score projection / Build Health.
11. Expose canonical strategy and Bond telemetry through logs/monitor.
12. Run focused deterministic strategy-machine tests.
13. Run unchanged-HEAD live validation only after the machine is structurally complete.
14. Calibrate weights/thresholds from that evidence.
15. Only then resume offline Optuna numerical tuning defined in [`BALATRO_BOND_TUNING.md`](BALATRO_BOND_TUNING.md).

Do not preserve obsolete conceptual behavior merely because an old test encodes it; remove or update tests when the architecture intentionally supersedes them.

## 17. Automated numerical tuning contract

The Bond catalogue is intentionally dynamic and its numerical sweet spots are empirical. Contribution weights, rank thresholds, realization cutoffs, pivot resistance, motif values, bounded prescription strengths, and shop/D1 calibration coefficients may require repeated adjustment as live evidence accumulates.

This does **not** make Bond semantics optimizer-defined. The architecture defines what a Bond means; an optimizer may only tune explicitly approved numerical parameters inside validated bounds.

The canonical automation plan is documented in [`BALATRO_BOND_TUNING.md`](BALATRO_BOND_TUNING.md). Its key constraints are:

- Optuna runs offline, never inside the live decision loop;
- Optuna remains **frozen** while strategy semantics, pinning/execution, or rank reachability are known to be incomplete;
- production defaults remain authoritative unless an optimized candidate passes promotion gates;
- tunable families are staged rather than exposing the entire catalogue simultaneously;
- every trial records repository revision, parameter schema, objective version, seeds/run IDs, and metrics;
- win rate is primary competence evidence but not the only signal;
- optimizer results are validated on holdout/fresh batches before promotion;
- no optimizer may weaken legality, boss correctness, hidden-information restrictions, or survival authority;
- known semantic/execution bugs are fixed before numerical tuning so optimization cannot learn around broken behavior.

The intended long-term loop is:

```text
mechanical semantics + strategy formation validated
      ↓
rank reachability validated
      ↓
approved parameter family + bounds
      ↓
Optuna study over reproducible Balatro batches
      ↓
metrics / best candidates
      ↓
manual + deterministic + holdout validation
      ↓
accepted production calibration
```

Constant fine-tuning is a repeatable experiment only after the machine being tuned actually understands the strategies it is evaluating.
