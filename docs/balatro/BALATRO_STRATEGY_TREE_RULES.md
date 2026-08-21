# Balatro Strategy System Rules

Development contract for the Red/White strategy system. Topology is in `BALATRO_STRATEGY_TREE.md`; contribution data is in `BALATRO_STRATEGY_RELATIONSHIPS.md`; realized viability is in `BUILD_HEALTH_AND_REALIZED_STRENGTH.md`.

## 0. Architectural decision — strategy tracks are Bond-like

The strategy system is being migrated from **competing Primary/Secondary/Third candidate builds** to **independent strategy tracks that combine into one emergent build**.

Mental model:

```text
Joker -> contribution(s) -> independent strategy tracks -> track ranks
      -> compatibility/synergy composition -> combined build plan
      -> power-engine selection + prescriptions -> actions
```

A Joker may contribute to several strategy tracks simultaneously. This is intentional and is the Balatro equivalent of one unit contributing quota to several Bonds in an autobattler. A strategy track is not a complete build by itself. The complete build is the compatible combination of developed tracks.

Example:

```text
Burnt Joker + Scholar + DNA
    Burnt hand-level engine  -> high development
    Aces                     -> high development
    High Card / Pair         -> compatible hand plan
    DNA/card duplication     -> supporting deck plan

Combined build: Burnt + Aces + chosen cheap repeatable hand + DNA support.
```

The strongest developed track may be the principal **power engine**, but other tracks are not competitors merely because they have lower scores.

### Migration status

The current runtime still contains legacy Primary/Secondary/Relevant/commitment machinery. Treat it as compatibility infrastructure while migrating. **Do not extend that abstraction with new special cases unless required to preserve behavior during migration.** New strategic work should target independent track contribution, rank, compatibility, and prescriptions.

Existing Gold/Silver/Bronze/Banned data is retained as useful curated domain knowledge and migration input. It is not the final architecture.

## 1. Vocabulary

Preferred terms going forward:

- **Strategy track** — one independently developed mechanic/plan (Burnt, Pair, Aces, Green, Red Seal, etc.). Existing docs/code may still call this a strategy/node.
- **Contribution** — how much a Joker/card/consumable/state feature advances a track. Existing Gold/Silver/Bronze values are the current coarse contribution encoding.
- **Track rank** — development threshold reached by accumulated contribution. Final thresholds must be calibrated from the catalogue and telemetry; do not invent them ad hoc.
- **Combined build** — mutually compatible set of developed tracks currently being executed.
- **Power engine** — the track supplying the main scaling/win-condition power and normally deserving the strongest reinforcement.
- **Prescription** — behavioral consequence of a developed track: hand/discard choice, acquisition, retention, deck shaping, ordering, economy, pack/consumable use, etc.
- **Conflict** — mechanical incompatibility. Conflict is stronger than ordinary opportunity cost.

Legacy `Primary`, `Secondary`, `Support`, `Highlighted`, `Committed`, and `Mature` names describe the current implementation, not the target conceptual model.

## 2. Contribution semantics

A component contributes to every track it genuinely advances. Multi-track contribution is desirable when mechanics justify it.

Gold/Silver/Bronze currently encode coarse contribution strength:

- Gold: defining/very strong contribution after prerequisites are satisfied;
- Silver: material support;
- Bronze: weak/conditional support;
- Banned: explicit mechanical conflict.

Red/White runtime currently uses Gold `+10`, Silver `+3`, Bronze `+1`, Banned `-12`. These values are **migration-era contribution weights**, not sacred final Bond-rank geometry.

Do not inflate a relationship merely to force legacy commitment. Under the target model, contribution should describe actual mechanical contribution; rank emerges from accumulated quota.

Non-Joker evidence (hand levels, deck composition, consumable investment, realized scaler state) may also advance a track where mechanically justified. Generic hand play counts are not evidence unless the mechanic itself depends on repetition/history; observed use may, however, be used by tactical/resource systems to detect actual hand specialization.

## 3. Topology and inheritance

`[I]` remains an indexed/generic strategy track with specialized descendants. `[L]` remains a leaf/specialization. Parent-child factoring exists to avoid duplicate evidence, not to force a single winning branch.

An indexed row contains only evidence genuinely shared by every specialization below it. A child contains only distinguishing evidence. Child evidence may inherit compatible parent contribution once materially established, but must not be double-counted.

Do not create fake parent edges for cross-cutting synergy. Cross-track synergy belongs in the compatibility/synergy graph.

## 4. Combined-build composition

Developed tracks are composed rather than globally ranked against one another.

The composer must eventually answer:

1. Which tracks are materially developed from current public state?
2. Which tracks are mutually compatible?
3. Which combination has the best realized short/medium-horizon power after transition cost?
4. Which track is the principal power engine?
5. Which prescriptions follow from the entire combination?
6. Which missing components most efficiently raise useful track ranks?

A run may have one dominant capstone engine plus several supporting tracks, several medium tracks when RNG does not provide a capstone, or a temporary survival board with little strategic development. All are valid roguelike states.

There is no requirement that exactly three tracks survive.

## 5. Compatibility and conflicts

Positive tracks normally coexist. Banned/conflict means genuine mechanical contradiction, not merely that two routes compete for slots.

Known authoritative examples:

```text
Burnt <X> Green
Burnt <X> Burglar
Green <-> Burglar : strong synergy
Burnt <-> cheap repeatable hand plans (High Card/Pair etc.) : compatible
Scholar/Aces <-> DNA : strong synergy when duplication is usable
```

Burnt needs a usable first discard. Green loses scaling when discarding. Burglar removes discards. Therefore Green/Burglar cannot be part of a Burnt combined build unless the run explicitly abandons Burnt; Green and Burglar reinforce each other.

Conflicts must affect acquisition, retention/replacement, and prescriptions even when a different poker-hand track has the largest raw score.

## 6. Track rank must change behavior

A strategy score/status that only appears in telemetry is insufficient. Higher development must increase the authority of the track's prescriptions.

Conceptual progression (names/thresholds TBD from calibration):

```text
emerging -> established -> strong -> engine -> capstone
```

The exact thresholds are not frozen yet. Required behavior is monotonic: stronger development means stronger reinforcement and stronger protection, subject to survival.

Examples:

### Burnt

- low development: value safe first-discard opportunities;
- developed: preserve a discard opportunity and prefer compatible repeatable hands;
- strong engine: when a blind is already safely clearable, activate Burnt before scoring instead of wasting the permanent level gain;
- any meaningful Burnt build: Burglar and Green are conflicts;
- survival may override Burnt activation when discarding would materially risk the blind.

### Ride the Bus / no-face

- developed Bus route: playing face cards is strategically harmful because it resets accumulated Mult;
- D1 should avoid face-card scoring lines when a comparable legal non-face line exists;
- deck shaping should increasingly remove/avoid face cards;
- survival remains authoritative if face cards are required to clear.

### Green + Burglar

- Burglar is a strong Green/no-discard partner because it removes discards and adds hands;
- the combined build should exploit extra hands while preserving Green scaling;
- Burnt is excluded.

### Aces / Scholar / DNA

- Scholar materially advances Aces;
- DNA becomes especially valuable when it can duplicate the rank/card the developed build wants;
- a Burnt + Aces + cheap-hand composition should value Scholar/DNA as multi-track reinforcement rather than asking whether Aces should replace Burnt as the single Primary.

## 7. Tactical survival

Strategy is subordinate to winning the blind.

Existing pace/clear-probability rules remain authoritative. Opening survival may bank near-pace hands rather than exhaust every discard chasing perfection. Conversely, a developed engine may intentionally spend a resource (for example Burnt's first discard) when survival margin is sufficient and the permanent gain is valuable.

The correct question is not `strategy or survival`; it is `what is the highest-value strategy-compliant action inside the safe survival envelope?`

## 8. Realized strength is separate from contribution

Contribution answers whether a component belongs to a track. Realized strength answers whether the engine is actually working now.

Examples: Hologram x1.0, unscaled Throwback, unused Burnt, unscaled Castle, or Green with negligible current Mult may have correct structural membership but poor realized power.

The combined-build composer and Build Health must use both axes. High quota cannot guarantee a win; it merely means the build has assembled a strong strategic package. Roguelike state, realized scaling, bosses, economy, and execution still decide survival.

## 9. Component roles

`CORE/ENGINE/SUPPORT/FILLER/CONFLICT` remains useful, but roles must be derived from the **combined build**, not membership in a legacy top-three shortlist.

A Joker contributing materially to any developed compatible track is not filler. A multi-track Joker may be especially valuable because one slot advances several tracks. A Joker can still be replaceable despite being on-path if its realized contribution is weak and a better component raises the combined build more.

## 10. Acquisition, pivoting, and RNG

The agent cannot demand a predetermined build. It must build from what the run offers.

Acquisition should value:

- contribution to already-developed compatible tracks;
- components that cross a useful rank threshold;
- multi-track contribution;
- creation of a new high-ceiling compatible engine;
- immediate survival and realized score;
- transition/slot/economy cost;
- conflicts with developed engines.

A `pivot` is best understood as changing the combined build/power engine because new RNG makes another compatible composition materially stronger, not switching a single global strategy ID.

## 11. Observability target

Logs/live monitor should migrate toward:

```text
Combined build : Burnt + Aces + Pair + DNA support
Power engine   : Burnt

Track          Contribution/Rank   Realized
Burnt          ...                 healthy
Aces           ...                 developing
Pair           ...                 healthy
Deck copy      ...                 developing

Conflicts      : Burglar, Green
Prescriptions  : activate first discard; favor Aces; reinforce Pair; copy target card
```

Legacy Primary/Relevant fields may remain during migration but must not be treated as the final truth.

## 12. Migration plan

Implement incrementally with deterministic tests:

1. Introduce explicit strategy-track contribution/rank data model while preserving current relationship catalogue.
2. Produce all track meters from one state; do not truncate to top three.
3. Add compatibility/conflict/synergy graph.
4. Compose a combined build and select a power engine from compatible developed tracks.
5. Derive component roles from combined-build membership.
6. Convert existing prescriptions to rank-aware combined prescriptions.
7. Wire prescriptions into D1 play/discard, Joker shop/replacement, packs, Tarot/Planet/Spectral, deck shaping, ordering, economy, skips, and bosses.
8. Migrate telemetry/live monitor to track meters + combined build.
9. Remove legacy Primary/Secondary/Third assumptions only after parity/regression coverage exists.
10. Recalibrate contribution weights/rank thresholds from unchanged-HEAD five-run telemetry.

Do not perform a flag-day rewrite and do not delete useful existing relationship data. The current catalogue is the seed dataset for the new system.

## 13. Immediate regression cases for migration

Preserve these as concrete behavioral targets from observed runs/user review:

- Burnt + Green must conflict.
- Burnt + Burglar must conflict; Burglar must not appear as Burnt support.
- Green + Burglar must synergize.
- With Burnt active and a safely clearable blind, do not skip the first-discard level gain merely because the first scoring hand can already clear.
- Scholar must receive strong value in a compatible Burnt + Aces/cheap-hand composition; DNA should further reinforce that composition when usable.
- Developed Ride the Bus/no-face play should avoid playing face cards when a safe comparable non-face line exists.
- A Joker structurally contributing to any developed compatible track must not be labelled FILLER solely because it is outside a legacy top-three shortlist.

## 14. Existing operational rules retained

Joker ordering, Negative retention, boss/survival overrides, edition handling, and bounded shop transition planning remain valid. They should consume the combined-build prescriptions as migration proceeds rather than being rewritten as independent strategy catalogues.
