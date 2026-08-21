# Balatro Strategy System

Canonical architecture contract for the Balatro strategy system. This document supersedes `BALATRO_STRATEGY_TREE_RULES.md`.

## Core model

Balatro strategies are independent **strategy tracks**, analogous to Bonds in a composition-building roguelike/autobattler.

A Joker or other component may contribute to multiple tracks simultaneously. Track contribution accumulates independently. Compatible developed tracks compose an emergent build. One track may be the principal power engine while other tracks reinforce hand shape, ranks/suits, retriggers, deck shaping, economy, consumables, etc.

```text
component -> track contribution(s) -> track ranks
          -> compatibility/synergy/conflict composition
          -> combined build
          -> power engine + merged prescriptions
          -> D1/shop/packs/deck/economy/boss behavior
```

The old Primary/Secondary/Third candidate-build model is legacy migration infrastructure and must not define the final architecture.

## Design order

1. Define the strategy catalogue from first principles.
2. Define component -> track contribution matrix.
3. Define track ranks/thresholds.
4. Define track-to-track compatibility, synergy and conflicts.
5. Define rank-aware prescriptions.
6. Evaluate all tracks from public state.
7. Compose the best viable combined build and identify its power engine.
8. Derive component roles and realized strength from that combined build.
9. Feed prescriptions into every relevant decision layer.
10. Replace legacy Primary/Secondary/Third telemetry and assumptions once parity/regression coverage exists.
11. Calibrate from unchanged-HEAD run telemetry.

Do not implement new legacy ranking patches while the catalogue is being reformulated unless necessary to fix a proven runtime regression.

## Contribution

Contribution answers: `how much does this component genuinely advance this track?`

The old Gold/Silver/Bronze/Banned relationship data is migration evidence, not a final quota system. Do not mechanically translate old tiers into new ranks. Re-audit every component after the catalogue is defined.

A component can contribute to multiple tracks. Multi-track contributors are strategically valuable because one Joker slot can advance several parts of the combined build.

## Track rank

A track rank represents how developed that strategy is. Exact thresholds and names are not frozen until the catalogue and contribution distribution are known.

Higher rank must increasingly affect behavior. A rank that only changes telemetry is useless.

## Combined build

The agent does not demand a predetermined strategy. It assembles the best compatible composition that RNG makes available.

A combined build may contain:

- one highly developed power engine plus support tracks;
- several medium-strength mutually reinforcing tracks;
- an early flexible board with no committed engine;
- a temporary survival board awaiting better components.

There is no fixed top-three requirement.

## Compatibility

Track interactions are explicit:

- compatible — can coexist without special benefit;
- synergistic — one materially increases the other's value;
- conflicting — mechanics materially contradict one another.

Known authoritative examples:

```text
Burnt <X> Green
Burnt <X> Burglar
Green <-> Burglar : synergy
```

Conflict must affect acquisition, retention/replacement and execution regardless of which poker-hand track currently has the largest score.

## Prescriptions

Developed tracks must change actions. Prescriptions may affect:

- hand selection;
- discarding;
- card ordering;
- Joker purchase/sale/replacement/order;
- Planet/Tarot/Spectral/pack decisions;
- deck manipulation;
- economy and rerolls;
- skips;
- boss adaptation.

Examples carried as regression targets:

- developed Burnt should use a safe first-discard hand-level upgrade even if the first scoring hand would already clear;
- Burnt cannot coexist with Burglar or Green as one combined build;
- developed Ride the Bus/no-face should avoid playing face cards when a safe comparable non-face line exists;
- Scholar/Aces/DNA should be allowed to reinforce a compatible Burnt + cheap-hand composition rather than being treated as rival global strategies.

Survival remains authoritative: strategy chooses the highest-value compliant action inside the safe survival envelope.

## Structural contribution vs realized strength

A track can be highly developed structurally while currently weak in practice. Build Health and realized-engine analysis remain separate from track rank.

Examples include inactive Hologram, unscaled Throwback, unused Burnt activation, weak Green scaling, or any engine whose required prescription is repeatedly violated.

High rank improves the power plan; it never guarantees a win.

## Component roles

`CORE`, `ENGINE`, `SUPPORT`, `FILLER`, and `CONFLICT` remain useful, but must eventually derive from combined-build participation rather than a legacy top-three shortlist.

A component contributing materially to a developed compatible track is not filler merely because another track is stronger. On-path components can still be replaced when their realized value is poor and a better component improves the whole build.

## Migration discipline

The runtime contains substantial useful strategy knowledge and tests. Preserve it as migration input. Do not perform a flag-day rewrite.

Target implementation sequence after catalogue formulation:

1. explicit track data model;
2. all-track meter evaluation;
3. compatibility/synergy/conflict graph;
4. combined-build composer;
5. power-engine selector;
6. combined-build component roles;
7. rank-aware prescription merger;
8. D1/shop/consumable/deck/economy integration;
9. telemetry/live-monitor migration;
10. removal of legacy ranking assumptions;
11. telemetry-driven calibration.
