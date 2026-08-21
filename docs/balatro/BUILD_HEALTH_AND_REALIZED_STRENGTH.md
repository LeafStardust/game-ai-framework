# Balatro Build Health and Realized Strength

Build Health is the viability layer beneath the strategy-track system. Strategy contribution/rank says **what coherent mechanics the run has assembled**; Build Health says **whether the resulting combined build actually works, survives, and scales fast enough**.

See `BALATRO_STRATEGY_TREE_RULES.md` for the Bond-like strategy-track architecture and migration plan.

## 1. Core distinction

Do not confuse:

```text
structural contribution / track rank
with
realized engine strength / build viability
```

A highly developed track can still lose. Roguelike RNG, bosses, current scaling, economy, execution and runway matter. Conversely, a temporarily ugly survival board can be correct early even when it has weak strategic coherence.

The target decision hierarchy is:

1. Can the current run survive the current/next blind?
2. Which strategy tracks are materially developed?
3. Which developed tracks are mutually compatible?
4. What is the best combined build from them?
5. Which track is the principal power engine?
6. Is that combined build actually functioning now?
7. Is it scaling quickly enough for the next one to two Antes?
8. Which action/component most improves survival or the combined build?
9. Would changing composition/power engine beat transition cost?
10. Execute the best legal action.

## 2. Build Health dimensions

`BuildHealth` remains a normalized diagnostic composed from:

- **Survival** — projected clear ability.
- **Immediate** — present scoring relative to blind requirements.
- **Scaling** — growth/multiplicative capacity relative to future blind growth.
- **Coherence** — how much of the board contributes to the same **compatible combined build**, not a legacy Primary/top-three shortlist.
- **Runway** — whether engines needing buildup have time/resources to mature.

A critical survival failure must not be hidden by the aggregate.

## 3. Coherence under the new architecture

Legacy coherence logic based on `Primary + Relevant` is migration-only.

Target coherence should measure:

- fraction of occupied Joker slots contributing materially to at least one developed compatible track;
- multi-track contribution value;
- explicit conflicts;
- disconnected generic filler;
- whether the board has a credible power engine;
- whether support actually reinforces that engine/combined build.

A Joker that contributes to a developed compatible track is **not FILLER** simply because another track has a higher score. On-path does not mean irreplaceable: weak support can still be replaced when another component improves the combined build more.

## 4. Realized engine states

Retain the realized-state vocabulary:

```text
NOT_OWNED
OWNED_INACTIVE
ACTIVATED_WEAK
ACTIVATED_HEALTHY
MATURE
```

Examples:

- Hologram x1.0: structurally relevant, realized inactive.
- Throwback x1.0: structurally relevant, not yet a mature skip engine.
- Burnt owned but first-discard upgrades repeatedly unused: structurally strong but operationally under-realized.
- Green with negligible Mult: correct track membership but weak current engine.
- Castle with little accumulated chips: weak realized scaler.
- Bull/Bootstraps with high cash: can be immediately mature because the required state already exists.

## 5. Prescriptions are part of realized strength

An engine cannot be called healthy if the action policy repeatedly violates the mechanic that creates its power.

Required examples:

### Burnt

Realized strength depends on actually using safe first-discard hand upgrades. If the first scoring hand trivially clears the blind and a safe discard exists, a developed Burnt engine should normally activate Burnt first. Green and Burglar are conflicts; Burglar cannot coexist as Burnt support because it removes discards.

### Ride the Bus

Realized strength depends on preserving accumulated Mult. D1 should avoid playing face cards when a safe comparable non-face line exists. Repeatedly resetting Bus while calling the route healthy is a model error.

### Green + Burglar

Burglar is a strong no-discard partner for Green: no discards prevents Green reset while extra hands provide more opportunities to exploit/grow the engine. Burnt is incompatible.

### Aces / Scholar / DNA

Scholar should be valued as an Aces contribution inside a compatible combined build. DNA can become especially valuable by duplicating the target rank/card. Burnt + Aces + Pair/High Card is a composition, not three rival strategy candidates.

## 6. Survival adequacy

Antes 1–2 remain survival/flexibility stages. Immediate off-track scoring is legal when necessary. The opening policy may bank a near-pace scoring hand rather than exhaust all discards chasing a perfect hand.

A developed engine may intentionally spend a tactical resource when survival margin makes it safe and doing so creates permanent value—for example Burnt's first discard. Survival is the envelope; strategy chooses the best action inside it.

## 7. Scaling adequacy

From Ante 3 onward, detect when the current combined build cannot keep pace with the next one to two Antes.

Under scaling deficit pressure prefer:

- raising the rank/realized strength of an existing compatible power engine;
- activating an inactive scaler;
- buying a component that advances several developed tracks;
- replacing filler/conflict/weak support with stronger compatible scaling;
- rerolling when bankroll and survival permit;
- changing the combined build when new RNG creates a materially stronger composition.

Five occupied Joker slots are not evidence of health.

## 8. Component roles

Retain:

```text
CORE
ENGINE
SUPPORT
FILLER
CONFLICT
```

but derive them from the **combined build**.

- CORE: defining component of the power engine or a capstone developed track.
- ENGINE: materially creates/scales a developed track.
- SUPPORT: materially reinforces one or more compatible developed tracks.
- FILLER: generic positive value with no material contribution to the current combined build.
- CONFLICT: mechanically damages a developed track/composition.

Replacement priority remains broadly conflict -> filler -> weak support -> weak engine -> core only during explicit composition change, subject to whole-build value and survival.

## 9. Composition change / pivot cost

The target system does not pivot between single strategy IDs. It changes the **combined build and/or power engine**.

Evaluate:

```text
new combined realized strength
+ useful rank thresholds crossed
+ multi-track synergy
+ deck/resource compatibility
+ short-horizon growth
- sold/abandoned track value
- slot/economy transition cost
- required future buildup
- survival risk
```

Late theoretical ceiling without runway is insufficient.

## 10. Short-horizon shop planning

Retain bounded multi-action planning for sequences such as:

- sell filler/conflict -> buy stronger compatible component;
- buy generator -> activate Hologram/Blue growth;
- sell expendables -> Ankh;
- buy Bull/Bootstraps pair when jointly strong at current cash;
- buy component -> re-evaluate all track meters -> buy complementary component.

Add target support for `component crosses useful track rank` and `one component advances multiple developed tracks`.

## 11. Phase behavior

### Ante 1–2 — foundation

Survive, collect useful contribution, remain flexible. Do not force a predetermined build.

### Ante 3–5 — composition formation

Identify developed compatible tracks, select/strengthen a power engine, replace disconnected filler, and converge resource use around the emergent combined build.

### Ante 6+ — execution

Strongly reinforce the best realized combined build. Do not discard compatible developed tracks merely because they are not the single highest-scoring node. Composition changes require decisive realized advantage and acceptable transition risk. Survival remains final authority.

## 12. Observability target

Migrate logs/live monitor toward:

```text
Build Health  : ...
Survival      : ...
Immediate     : ...
Scaling       : ...
Coherence     : ...
Runway        : ...

Combined build: Burnt + Aces + Pair + DNA support
Power engine  : Burnt

Track meters:
Burnt          contribution/rank/realized state
Aces           contribution/rank/realized state
Pair           contribution/rank/realized state
...

Components:
Burnt Joker    CORE
Scholar        ENGINE/SUPPORT (Aces)
DNA            multi-track SUPPORT
...

Conflicts      : Green, Burglar
Prescriptions  : activate first discard; favor Ace target; reinforce Pair
Warnings       : scaling deficit / inactive engine / prescription violation
```

Legacy Primary/Relevant fields may remain during migration but should be visibly marked compatibility fields once the new meters exist.

## 13. Implementation sequence

Current Build Health/runtime work already exists. Next architecture work should proceed without a flag-day rewrite:

1. Add strategy-track meter/rank model over the existing relationship catalogue.
2. Evaluate **all** tracks from state rather than truncating to top three.
3. Add explicit compatibility/synergy/conflict composition graph.
4. Build a combined-build resolver and power-engine selector.
5. Make component-role classification consume the combined build.
6. Make realized-engine analysis detect prescription compliance/violations where measurable.
7. Feed combined prescriptions into D1, shop, packs/consumables, deck shaping, ordering, economy, skips and bosses.
8. Update monitor/log schema.
9. Retire legacy Primary/Secondary/Third assumptions after regression parity.
10. Run unchanged-HEAD five-run batches and calibrate contribution/rank geometry from telemetry.

Do not solve this by indiscriminately increasing per-Joker scores. The purpose is coherent composition reasoning.

## 14. Regression targets carried from telemetry

- early Red/White should not routinely exhaust all discards and die just below ordinary Ante 1–2 targets;
- Burnt + Green and Burnt + Burglar are conflicts;
- Green + Burglar synergize;
- developed Burnt should actually use safe first-discard upgrades;
- Scholar/Aces/DNA should be recognized as compatible reinforcement around a Burnt + cheap-hand build when offered;
- developed Ride the Bus should avoid face-card plays when safely possible;
- on-path components must not be logged FILLER due to legacy shortlist plumbing;
- Build Health must distinguish structural coherence from realized underperformance.

## 15. Release scope

This remains Red/White competence work. Complete and validate the strategy-track migration before treating the strategy model as frozen for subsequent stakes.
