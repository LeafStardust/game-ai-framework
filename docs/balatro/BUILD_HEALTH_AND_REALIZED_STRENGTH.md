# Balatro Build Health and Realized Strength

Build Health is the reality-check layer beneath `BALATRO_STRATEGY_SYSTEM.md`.

The Bond system says **what has been built, what is worth reinforcing, and how it should be played**. Build Health and score projection say **whether it actually works, clears, and scales quickly enough**.

## 1. Hard separation

Never equate or sum Bond rank with mechanical power.

```text
Bond development -> strategic structure
Bond realization -> whether that structure is functioning
Score projection -> actual expected Balatro output
Build Health     -> current/future viability diagnosis
```

An R5 coherent build can still be too weak to survive. A disconnected temporary board can still have excellent immediate survival.

## 2. Integration pipeline

```text
components / persistent state
  -> weighted Bond contributions
  -> Bond ranks + realization
  -> compatible combined build + motifs
  -> intended power engine + prescriptions

actual Balatro mechanics + intended lines
  -> score / clear projection

projection + realization + combined-build coherence + runway
  -> Build Health
```

The Bond system helps the projector know which intended engines/lines deserve evaluation, but actual cards, hand levels, Joker effects, Chips/Mult/XMult, retriggers, scaler values, blind/boss state and consistency determine projected output.

## 3. Build Health dimensions

Retain normalized diagnostics approximately as:

- **Survival** — projected ability to clear current/next blind;
- **Immediate Power** — current scoring relative to blind requirement;
- **Scaling** — realized growth/multiplicative capacity versus future blind growth;
- **Coherence** — how much of the board/state participates in one compatible combined build/motifs;
- **Runway** — whether developing engines/motifs can mature before they are needed.

Critical survival failure must not be hidden by a good aggregate or high Bond ranks.

### SHOP survival contract

During live hand play, D1 already evaluates whole-blind clear probability from the visible hand and public redraw composition. SHOP has no visible next opening hand, so production Build Health must not pretend that one representative best hand can be repeated for every remaining hand.

Production SHOP Survival therefore uses a bounded public-state projection:

1. take the authoritative permanent/owned playing-card composition when available;
2. discard serialized card order and represent it as an unordered public multiset;
3. deterministically sample a small set of possible opening hands from that multiset;
4. for each opening, create an isolated next-blind state with round score/history reset;
5. run the same `LiveBlindClearPlanner` used by D1 with narrow action beams, deterministic public redraw sampling, full round hand horizon, and a hard node cap;
6. probability-weight the resulting whole-blind clear probabilities.

The projection may use only ordinary public state. It must never inspect hidden future draw order, RNG state, run seed, or future shop contents.

If any sampled opening cannot complete inside the bounded planner contract, partial coverage is not renormalized because that would bias Survival. The SHOP adapter instead falls back to the generic Build Health capacity estimate. Custom/injected scorers also retain the generic estimator so offline/unit-test contracts are not silently converted into live D1 semantics.

Immediate Power remains a separate diagnostic. Replacing SHOP Survival with P(clear) must not overwrite scaling, coherence, runway, or mid-blind survival behavior.

## 4. Realization

Canonical Bond realization states:

```text
DORMANT
PARTIAL
ACTIVE
MATURE
```

Realization is Bond-specific and may depend on actual density, execution, compatible support, accumulated scaler state, current boss/environment and prescription compliance.

Examples:

- Steel R4 can remain PARTIAL if useful Steel density/held triggering is inadequate.
- Burnt can be highly developed but under-realized if safe first-discard upgrades are repeatedly skipped.
- Throwback can be structurally relevant while x1.0 and therefore weakly realized.
- Bull/Bootstraps-style cash scoring may become immediately mature when the required bankroll already exists.

Temporary bosses/environment change realization and score projection, not persistent Bond rank. Example: a Face Cards Bond remains structurally developed under The Plant while its realization may collapse for that blind.

## 5. Coherence

Coherence is based on the **combined build**, not legacy Primary/Secondary/Third.

Measure approximately:

- occupied slots materially advancing relevant compatible Bonds;
- active/mature motifs;
- useful multi-Bond bridge components;
- explicit conflicts;
- disconnected filler;
- presence of a credible realized power engine;
- whether support reinforces that engine/composition.

A component is not filler merely because another Bond is higher rank.

## 6. Diagnosing unrealized investment

The separation of rank, realization and projection should produce actionable diagnoses.

Example:

```text
Steel: R4 PARTIAL
Held Cards: R3 ACTIVE
Projected clear: poor
```

Interpretation: substantial Steel investment exists but is not producing enough power. Acquisition should prefer components that activate/realize the existing investment (for example held retrigger/motif completion where applicable) over blindly adding more structural Steel quota.

Conversely, high immediate power with poor coherence/scaling means the run may need to consolidate into an emerging compatible composition before future blinds outgrow it.

## 7. Survival and prescriptions

Immediate survival is the final authority. Strategy chooses the highest-value compliant action inside the survival envelope.

Compatible Bond prescriptions combine. Bond-level contradictions should already be excluded by explicit CONFLICT relationships. Special combined behavior belongs to motifs.

Prescription authority is **preference-only beneath child-policy legality and safety**. A motif bonus may reorder already-admitted shop or pack options, but it must not convert an unsupported, unaffordable, deferred, unsafe, or otherwise rejected choice into an autonomous action. Runtime prescription bonuses are bounded for this reason.

Live matching must normalize equivalent public telemetry rather than depend on one display spelling. Current contracts normalize consumable labels, Planet target-hand naming, rank aliases, Steel enhancement naming, and Red/Blue Seal naming before motif preference is applied.

A developed engine cannot be called healthy if the agent repeatedly violates the action that creates its power when a safe compliant line exists.

Carried regression examples:

- developed Burnt should use a safe first-discard upgrade before a trivial clear;
- developed Ride the Bus/no-face should avoid face-card plays when a safe comparable non-face line exists;
- active Baron-Mime-Steel should preserve payoff held cards and exploit appropriate held/retrigger shaping;
- Green/no-discard and Burnt must not be composed together;
- Baron/Mime/Steel should prefer safe Steel creation, Red Seal support, and King engine targets without bypassing pack/shop safety;
- Burnt target leveling should value the Planet matching the actual evaluated target hand rather than a hard-coded default;
- Photograph/Hanging Chad and Hack retrigger motifs may both value Red Seal creation while targeting their own mechanically relevant card bodies.

## 8. Scaling and emergency power

When Survival/Immediate Power is poor despite high coherence, stop spending solely to perfect already-developed Bonds. Prefer immediate compatible scoring, activation of under-realized investment, or another action that materially raises clear probability.

When Survival is healthy but Scaling/Coherence is poor, the agent can spend runway consolidating/advancing useful Bonds and motifs.

Five occupied Joker slots and high Bond ranks are not evidence of health by themselves.

## 9. Pivot cost

Composition change evaluates actual expected improvement against transition cost:

```text
new realized/potential power
+ useful rank thresholds crossed
+ motif activation/synergy
+ existing deck compatibility
+ short-horizon growth
- missing-piece distance
- money/slot cost
- abandoned component/Bond value
- deck reshaping/buildup time
- survival risk
```

R1/R2 Bonds are cheap to abandon; R3 creates meaningful resistance; R4 strong resistance; R5 very strong resistance. Rank resistance is a cost, not a lock.

Canonical runtime pivot authority uses the current same-run/same-round Strategy Health mode to set how much net structural gain is required before an eligible positive D2 replacement may be promoted, and how much realized disruption is tolerated before an existing replacement is vetoed. Stronger modes require larger structural gains than SURVIVE/REPAIR.

Pivot scoring must not double-count motif state already represented inside composition coherence. Explicit disruption remains asymmetric: losing realized motifs or pivot resistance is penalized because dismantling functioning machinery carries practical risk even when a projected composition has higher raw coherence.

The authority only applies when the live state proves the Joker roster is full. Missing, zero, negative, or otherwise invalid Joker-slot telemetry is treated as unknown rather than as evidence that replacement is required; in that case the underlying Joker acquisition policy remains authoritative.

## 10. Component roles

Retain:

```text
CORE
ENGINE
SUPPORT
FILLER
CONFLICT
```

but derive them from combined-build participation and realized value.

- CORE: defining/capstone component of the current power plan;
- ENGINE: materially creates/scales a developed Bond or active motif;
- SUPPORT: materially reinforces relevant compatible Bonds/motifs;
- FILLER: generic positive value with no material participation in the current combined build;
- CONFLICT: mechanically damages the chosen composition.

Replacement normally trends conflict -> filler -> weak support -> weak engine -> core only during explicit composition change, subject to survival and whole-build value.

## 11. Shop/build-health interaction

Strategic acquisition value may include multi-Bond progress, threshold crossings, motif activation and slot efficiency. These are not direct scoring points.

Shop decisions should combine:

- immediate mechanical value;
- Build Health deficits;
- Bond/motif structural progress;
- realization improvement;
- transition cost;
- economy/runway.

A component that crosses two useful Bond thresholds and activates a motif may be strategically exceptional even before its raw immediate score is exceptional.

Motif prescriptions may add bounded preference to already-positive admitted consumable/shop utility. D4 admission, resource guards, affordability, slot legality, and the underlying child utility remain authoritative.

For production SHOP hypothetical states, Survival should use the bounded next-blind D1 clear-probability adapter described above. This makes acquisition/replacement comparison sensitive to whether the candidate actually improves a plausible full-round clear path rather than whether it merely raises one synthetic best-hand score.

## 12. Observability

The production live monitor is observational: it renders the structured diagnostics emitted by the decision pipeline rather than recomputing Build Health in the UI. The desktop `BalatroAgentMonitor.bat` path displays one canonical health block alongside the existing strategy `Has` / `Seeking` evidence.

Current monitor contract:

```text
BUILD HEALTH / REALIZED STRENGTH
Health total    : ...%
Survival        : ...%
Immediate       : ...%
Scaling         : ...%
Coherence       : ...%
Runway          : ...%
Critical        : True/False
Scaling deficit : True/False
Engines         : engine=OWNED_INACTIVE / ACTIVATED_WEAK / ACTIVATED_HEALTHY / MATURE ...
Component roles : Joker=CORE / ENGINE / SUPPORT / FILLER / CONFLICT ...
Warnings         : inactive-engine / scaling-deficit / survival warnings ...
```

The renderer accepts the canonical top-level postmortem diagnostics and the nested realized-strength diagnostic shape used by structured producers. Missing diagnostics degrade to explicit `-`/`NONE` values rather than being inferred from UI state.

Full telemetry may retain all Bond states. Do not flood the live monitor with dormant R0 Bonds.

Decision logs should state when a purchase/action crosses useful thresholds, changes realization, activates a motif, addresses a Build Health deficit, receives a bounded canonical prescription bonus, or is promoted/vetoed by canonical pivot authority.

## 13. Migration/regression targets

- remove legacy Primary/Relevant/top-three assumptions from coherence/component roles once new combined-build plumbing exists;
- remove Gold/Silver/Bronze as strategic truth;
- preserve proven useful runtime behavior while migrating architecture;
- update/remove tests that intentionally encode superseded architecture;
- calibrate contribution/rank geometry and Build Health thresholds from unchanged-HEAD multi-run telemetry;
- keep structural coherence distinct from realized underperformance;
- retain regression coverage for unknown Joker-slot telemetry, motif-state non-double-counting, bounded prescription authority, normalized public naming/telemetry variants, SHOP planner fallback, custom-scorer isolation, owned-deck order invariance, and live-monitor rendering.

The Bond pivot/prescription boundary subsystem, bounded SHOP clear-probability survival subsystem, and live Build Health monitor contract are deterministic-test green as of 2026-08-22. The next calibration gate is a fresh unchanged-HEAD five-run Red/White validation batch. This remains Red/White competence scope until the broader Bond migration and unchanged-HEAD validation gate are complete.
