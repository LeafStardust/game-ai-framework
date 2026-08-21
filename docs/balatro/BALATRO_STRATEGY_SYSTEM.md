# Balatro Strategy System

Canonical architecture contract for the Red/White Balatro strategy redesign.

## 1. Mental model

The intended abstraction is Currency Wars-like:

```text
Currency Wars character        = Balatro Joker/card/persistent state
Currency Wars Bond             = Balatro strategy track (Bond)
Bond quota/rank                = weighted contribution + Bond rank
Currency Wars player strategy  = Balatro composition motif / combined build
```

A component may advance multiple Bonds simultaneously. Bonds develop independently. Compatible Bonds compose into a run-specific build; known super-additive combinations may be represented as composition motifs. There is no Primary/Secondary/Third requirement.

Example: Baron is not a Bond. `Held Cards` is. Baron + Mime + Steel Kings is a composition motif built from Held Cards, Held Retrigger, Steel and relevant rank/card structure.

## 2. Bond admission

A Bond is a persistent, developable strategic axis. A candidate should normally satisfy most of:

- further investment can meaningfully develop it;
- multiple components or persistent state features can contribute;
- greater development materially improves the plan;
- greater development changes acquisition, deck shaping or execution.

A single defining Joker may establish a Bond when owning it creates a deep strategic axis that other components/state can develop. Burnt is the canonical example.

Do not make every Joker, famous build or mechanic a Bond. Exact packages such as PhotoChad or Baron-Mime-Steel belong above Bonds as motifs/compositions.

## 3. Weighted contribution — no G/S/B replacement

Gold/Silver/Bronze/Banned is legacy migration evidence only. Do not recreate categorical contribution tiers under new names.

Every contributor receives its own Bond-specific numerical contribution. One component may contribute different amounts to several Bonds:

```text
component -> Bond A +x
          -> Bond B +y
          -> Bond C +z
```

Contribution means `how much this component genuinely develops this Bond`, not global strategy commitment and not direct scoring power.

Sources may include Jokers, permanent deck composition, rank/suit density, enhancements, seals, hand levels, permanent card upgrades, accumulated scaler state, consumable infrastructure and other persistent public state. Current-hand accidents are tactical state, not Bond development.

State/density contribution should use mechanically appropriate bands/caps/conditions rather than unbounded per-card inflation.

Permanent additions remain permanent contribution while they remain in game state. Dynamic sources disappear when sold/destroyed. Eternal/otherwise locked components remain contribution while present. No artificial historical Bond decay exists; recalculate from actual state.

## 4. Five-rank framework

Use approximately five standardized development ranks:

```text
R1 Emerging
R2 Established
R3 Strong
R4 Power-engine capable
R5 Capstone / maximum strategic commitment
```

The names may be refined, but the progression meaning is shared.

Each Bond still defines its own:

- weighted contributors;
- numerical thresholds;
- mechanically necessary rank gates;
- effects/prescriptions unlocked or strengthened at each rank.

Threshold geometry does not need to be identical between Bonds. Density mechanics such as Steel can differ from defining-Joker mechanics such as Burnt. Mandatory gates are used only where allowing the rank without them would be mechanically nonsensical.

Generic rank authority increases with rank: R1 is opportunistic recognition; R2 begins meaningful reinforcement/basic prescriptions; R3 protects and actively develops the Bond; R4 may serve as a power engine and strongly influences decisions; R5 is capstone commitment. The Bond-specific rank definition says exactly what that authority means for that mechanic.

## 5. Development rank is not realization

Every Bond has two separate axes:

```text
Development = contribution total + R1..R5
Realization = DORMANT / PARTIAL / ACTIVE / MATURE
```

Development says what has been assembled/invested. Realization says whether that structure is actually functioning in the current environment.

Example: Steel may be R4 structurally but only PARTIAL until enough useful Steel cards are actually held/triggered by the current plan. Bosses temporarily suppress realization, not persistent development. After the boss, the underlying Bond rank remains unless actual build state changed.

## 6. Sparse Bond relationships

Do not build an exhaustive pair matrix.

```text
default relationship = NEUTRAL
explicit relationships = SYNERGY or CONFLICT only
```

Only store relationships that materially matter. Complex/super-additive combinations belong to motifs rather than adding more relationship tiers.

Canonical conflict example: Burnt x No-Discard.

A Bond-level mechanical contradiction should normally be represented as CONFLICT so contradictory Bonds are not composed into the same build.

## 7. Composition motifs

A motif is a known strategy/composition whose value cannot safely be represented by additive Bond development alone. It is analogous to a Currency Wars player strategy, not another Bond.

Motifs may be:

```text
POTENTIAL -> ACTIVE -> MATURE
```

They can define prerequisites, super-additive synergy, bridge components, missing-piece distance, special prescriptions and realized gates.

Canonical example:

```text
Baron + Mime + Steel Kings
  Held Cards
  Held Retrigger
  Steel
  relevant King/card concentration
        -> Baron-Mime-Steel motif
```

The motif can then value Steel/Red-Seal Kings, hand-size support and held retriggers appropriately and prescribe keeping payoff Kings held.

## 8. Prescription resolution

Do not create a second complicated prescription-conflict subsystem.

- Bond-level contradictions -> CONFLICT -> do not compose.
- Compatible Bond prescriptions -> combine.
- unusual/super-additive combination behavior -> motif prescription.
- immediate survival -> final authority and may override strategic prescriptions.

## 9. Multi-Bond contributors and slot efficiency

A component that advances several relevant Bonds is strategically valuable because one Joker slot can develop several parts of the combined build.

Its shop/build value should consider:

- progress added to currently relevant Bonds;
- useful rank thresholds crossed;
- motifs activated/advanced;
- synergy among those Bonds;
- slot efficiency;
- replacement/transition cost;
- actual immediate scoring/economic value separately.

Do not convert overlapping Bond contribution into imaginary scoring power. Bond ranks are structural information, not additive score estimates.

## 10. Pivot and transition

Potential high-ceiling Bonds/motifs must not automatically destroy a functioning build.

Track motif/composition distance roughly as:

```text
FAR -> DEVELOPING -> NEAR -> ACTIVE -> MATURE
```

Pivot evaluation considers current realized build power, new potential/realized power, useful thresholds crossed, motif synergy, deck compatibility, missing pieces, money/slots, abandoned value, reshaping/buildup time, remaining runway and survival risk.

Existing rank creates pivot resistance:

- R1/R2: cheap to abandon;
- R3: meaningful transition cost;
- R4: strong pivot resistance;
- R5: very strong pivot resistance.

This is a cost, never a lock. Survival or a clearly superior composition can justify abandoning even R5.

## 11. Build Health integration

Bond rank answers:

```text
What have I built?
What should I reinforce?
How should it be played?
```

Build Health / score projection answers:

```text
Does it actually clear?
Is it powerful enough now?
Is it scaling fast enough?
```

Never sum Bond ranks into build power.

Pipeline:

```text
components/state
  -> Bond contributions
  -> Bond ranks + realization
  -> combined build + motifs
  -> intended engine/prescriptions

actual Balatro mechanics + intended engine
  -> score projection

combined-build coherence + realization + score projection
  -> Build Health
```

A coherent R5 build may still be too weak to survive. Build Health must expose that rather than allowing strategic rank to hide mechanical failure.

## 12. Observability contract

Live monitor should show only relevant Bonds; full telemetry may retain all Bond states.

Per relevant Bond expose approximately:

```text
Held Cards
Rank         : R4
Contribution : 17.5 / 21.0 -> R5
Realization  : ACTIVE
```

Composition section:

```text
Power engine : ...
Bonds        : relevant rank + realization
Motifs       : POTENTIAL/ACTIVE/MATURE + distance/next requirement
Conflicts    : ...
Prescriptions: ...
```

Shop/action telemetry should explain threshold/motif effects, e.g. a Mime purchase crossing Held Cards R4 and Held Retrigger R3 while activating Baron-Mime-Steel. Do not flood the live monitor with every dormant R0 Bond.

## 13. Migration order

1. Freeze the Bond catalogue.
2. Define weighted component/state contributions.
3. Define per-Bond R1-R5 thresholds, gates and rank effects.
4. Define sparse SYNERGY/CONFLICT edges.
5. Define important composition motifs and activation/distance rules.
6. Implement all-Bond evaluation and realization.
7. Implement combined-build composer and power-engine selection.
8. Integrate score projection / Build Health.
9. Integrate rank/motif prescriptions into D1, shop, packs, deck shaping, economy, skips and bosses.
10. Migrate component roles and filler logic to combined-build participation.
11. Migrate telemetry/live monitor.
12. Retire legacy Primary/Secondary/Third and G/S/B assumptions after regression parity.
13. Calibrate weights/thresholds from unchanged-HEAD multi-run telemetry rather than arbitrary inflation.

The current runtime/tests remain migration evidence. Do not preserve obsolete conceptual behavior merely because an old test encodes it; remove/update tests when the architecture intentionally supersedes them.
