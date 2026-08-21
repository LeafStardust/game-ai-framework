# Balatro Strategy System

Canonical architecture contract for the Balatro strategy system.

## Core model

Balatro strategy tracks are analogous to Currency Wars **Bonds**. A Joker/card/state component may contribute to multiple tracks simultaneously. Tracks develop independently.

A **composition motif** is analogous to a Currency Wars player strategy: a known, useful combination of multiple tracks/components that becomes super-additive when assembled. Motifs are NOT additional Bonds and must not receive independent quota merely for existing.

Example:

```text
Currency Wars                         Balatro
character                             Joker/card/state
Bond                                  strategy track
Bond quota/rank                       track contribution/rank
pinned/player strategy                composition motif / combined build

Baron + Mime + Steel Kings is therefore a composition motif:
  Held Cards + Held Retrigger + Steel + King concentration
```

The runtime target is:

```text
components
   ↓ contribute to one or more
strategy tracks (Bonds)
   ↓ independent ranks
compatibility / synergy / conflict graph
   ↓
composition motifs + emergent combinations
   ↓
combined build
   ↓
power engine + supporting tracks
   ↓
merged rank-aware prescriptions
   ↓
D1 / shop / packs / deck shaping / economy / bosses
```

The old Primary/Secondary/Third candidate-build model is legacy migration infrastructure and must not define the final architecture.

## Strategy tracks vs composition motifs

A strategy track must be independently developable by accumulating multiple meaningful contributions. It represents one coherent mechanic or axis of power.

A composition motif describes a particularly important combination of tracks/components whose value is greater than treating them independently.

Do NOT create a new track for every famous build. Examples such as PhotoChad, Baron-Mime-Steel, Midas-Vampire, Marble-Stone, etc. should normally emerge as motifs/combinations of underlying tracks.

Motifs exist so the agent can recognize super-additive packages and their prescriptions without polluting the Bond catalogue.

A motif should define only what cannot be derived safely from additive track ranks alone:

- activation/prerequisite conditions;
- super-additive synergy value;
- bridge components that advance several required tracks;
- targetable missing pieces;
- realized-strength gates;
- special prescriptions;
- transition/pivot cost.

Motifs may be `POTENTIAL`, `ACTIVE`, or `MATURE` based on actual owned/deck state. Seeing one component must not pretend the full motif exists.

## Canonical example: Baron-Mime-Steel

Baron-Mime-Steel must be understandable without a `Baron-Mime-Steel Bond`.

Conceptually:

```text
Baron          -> Held Cards / King-held payoff
Mime           -> Held Retrigger
Steel Kings    -> Steel + Held Cards + King concentration
Red Seal Kings -> Held Retrigger + King concentration
hand size      -> Held Cards support

when sufficient pieces/density coexist:
  motif = Baron-Mime-Steel
  synergy = strongly super-additive
```

The motif then increases acquisition/deck-shaping value for Steel Kings, Mime/Baron-compatible held effects, Red Seal Kings and hand-size support, while prescribing that payoff Kings remain held rather than being unnecessarily played.

## Design order

1. Define the strategy-track catalogue from first principles.
2. Define component -> track contribution matrix.
3. Define track ranks/thresholds.
4. Define track-to-track compatibility, synergy and conflicts.
5. Define important composition motifs and activation conditions.
6. Define rank/motif-aware prescriptions.
7. Evaluate all tracks from public state.
8. Detect potential/active/mature motifs.
9. Compose the best viable combined build and identify its power engine.
10. Derive component roles and realized strength from that combined build.
11. Feed prescriptions into every relevant decision layer.
12. Replace legacy Primary/Secondary/Third telemetry and assumptions once parity/regression coverage exists.
13. Calibrate from unchanged-HEAD run telemetry.

Do not implement new legacy ranking patches while the catalogue is being reformulated unless necessary to fix a proven runtime regression.

## Contribution

Contribution answers: `how much does this component genuinely advance this track?`

The old Gold/Silver/Bronze/Banned relationship data is migration evidence, not a final quota system. Do not mechanically translate old tiers into new ranks. Re-audit every component after the catalogue is defined.

A component can contribute to multiple tracks. Multi-track contributors are strategically valuable because one Joker slot can advance several parts of the combined build.

Do not double-count one component as several independent engines merely because it contributes to several tracks. Structural quota and realized scoring power are separate axes.

## Track rank

A track rank represents how developed that strategy is. Exact thresholds and names are not frozen until the catalogue and contribution distribution are known.

Higher rank must increasingly affect behavior. A rank that only changes telemetry is useless.

Thresholds do not have to be globally identical. Some tracks require density; some become useful from a defining component. Per-track threshold geometry is permitted when mechanically justified.

## Combined build

The agent does not demand a predetermined strategy. It assembles the best compatible composition that RNG makes available.

A combined build may contain:

- one highly developed power engine plus support tracks;
- several medium-strength mutually reinforcing tracks;
- one or more active composition motifs;
- an early flexible board with no committed engine;
- a temporary survival board awaiting better components.

There is no fixed top-three requirement.

## Compatibility and synergy

Track interactions are explicit and conditional where necessary:

- `CONFLICT` — mechanics materially contradict one another;
- `COMPATIBLE` — can coexist without meaningful super-additive benefit;
- `SYNERGY` — materially reinforce each other;
- `STRONG_SYNERGY` — super-additive enough to influence composition/pivot decisions.

Known authoritative examples:

```text
Burnt <X> Green
Burnt <X> Burglar
Green <-> Burglar : strong synergy
Held Cards + Held Retrigger + Steel + King density : Baron-Mime-Steel motif
```

Conflict must affect acquisition, retention/replacement and execution regardless of which poker-hand track currently has the largest score.

Compatibility alone must not be scored as if it were synergy.

## Dependencies and realized gates

Some tracks/motifs depend on deck state or other tracks. A high structural rank cannot bypass a missing mechanical prerequisite.

Examples:

- Steel requires useful Steel cards and an execution plan that holds/triggers them.
- Baron alone with negligible King density is only a potential held-King route, not a mature engine.
- Hologram x1.0 can be structurally relevant while realized inactive.
- Throwback x1.0 is not a mature skip engine.

The system must distinguish `targetable potential` from `realized engine`.

## Prescription resolution

Developed tracks and active motifs change actions. Prescriptions may affect:

- hand selection;
- discarding;
- card holding/order;
- Joker purchase/sale/replacement/order;
- Planet/Tarot/Spectral/pack decisions;
- deck manipulation;
- economy and rerolls;
- skips;
- boss adaptation.

Prescriptions can conflict. They must not simply be concatenated. Resolve them using:

1. immediate survival;
2. active power-engine importance;
3. realized motif/track strength;
4. track rank;
5. transition cost and future value.

Examples carried as regression targets:

- developed Burnt should use a safe first-discard hand-level upgrade even if the first scoring hand would already clear;
- Burnt cannot coexist with Burglar or Green as one combined build;
- developed Ride the Bus/no-face should avoid playing face cards when a safe comparable non-face line exists;
- Scholar/Aces/DNA should be allowed to reinforce a compatible Burnt + cheap-hand composition rather than being treated as rival global strategies;
- active Baron-Mime-Steel should preserve payoff Kings in hand, favor Steel/Red-Seal King shaping, and value hand-size/held retrigger support.

Survival remains authoritative: strategy chooses the highest-value compliant action inside the safe survival envelope.

## Card/deck state is first-class evidence

The system must not derive tracks only from owned Jokers. Contributions and motif gates may come from:

- rank density;
- suit density;
- enhancements;
- seals;
- editions where strategically relevant;
- hand levels;
- deck size/concentration;
- accumulated Joker scaler state;
- available hands/discards;
- consumable state.

This is required for Steel, Glass, seals, exact-card concentration, rank/suit builds, DNA targets and similar plans.

## Structural contribution vs realized strength

A track can be highly developed structurally while currently weak in practice. Build Health and realized-engine analysis remain separate from track rank.

High rank improves the power plan; it never guarantees a win.

## Component roles

`CORE`, `ENGINE`, `SUPPORT`, `FILLER`, and `CONFLICT` remain useful, but must eventually derive from combined-build participation rather than a legacy top-three shortlist.

A component contributing materially to a developed compatible track is not filler merely because another track is stronger. On-path components can still be replaced when their realized value is poor and a better component improves the whole build.

## Transition / pivot

A new component must not trigger a pivot merely because it starts a high-ceiling motif.

Composition change should consider:

```text
current realized build power
vs
new realized/potential composition power
+ useful track thresholds crossed
+ active motif synergy
+ existing deck compatibility
- missing-piece distance
- sold/abandoned value
- slot/economy cost
- buildup time
- survival risk
```

Baron alone with two Kings should not destroy a functioning build. Baron + Mime + substantial King/Steel infrastructure may justify aggressive completion.

## Migration discipline

The runtime contains substantial useful strategy knowledge and tests. Preserve it as migration input. Do not perform a flag-day rewrite.

Target implementation sequence after catalogue formulation:

1. explicit track data model;
2. all-track meter evaluation;
3. compatibility/synergy/conflict graph;
4. composition-motif model;
5. motif detector and distance-to-activation evaluation;
6. combined-build composer;
7. power-engine selector;
8. combined-build component roles;
9. rank/motif-aware prescription resolver;
10. D1/shop/consumable/deck/economy integration;
11. telemetry/live-monitor migration;
12. removal of legacy ranking assumptions;
13. telemetry-driven calibration.
