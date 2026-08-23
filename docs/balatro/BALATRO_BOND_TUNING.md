# Balatro Bond Tuning

Status: **Implemented foundation / live baseline validation pending**

This document defines the automated numerical calibration layer for the canonical Balatro Bond/composition architecture.

The tuning subsystem is intentionally **offline**. It must never sit inside the live decision loop, call an LLM during gameplay, expose hidden RNG/future draw order, or change the semantic meaning of a Bond during a run.

## Purpose

The Bond catalogue is dynamic even though its evaluators, thresholds, weights, relationship values, realization rules, and policy coefficients are implemented in code. Those numbers require repeated empirical calibration until they reach stable sweet spots across many public-state runs.

Manual five-run batches remain useful for finding architecture and execution defects, but they are too expensive and noisy for systematic numerical tuning. The Optuna subsystem automates bounded search over approved parameter families while the deterministic Balatro agent remains the evaluated subject.

Optuna is an optimizer, not a strategy designer. It may tune approved numbers only. It must not invent Bonds, relationships, motifs, unlock semantics, execution rules, or hidden-information shortcuts.

## Separation of responsibilities

```text
Human / architecture review
    defines what each Bond means
    defines legal parameter families and safety bounds
    identifies policy/semantic bugs
              |
              v
Offline tuning harness
    proposes bounded parameter configurations
    runs reproducible evaluation batches
    aggregates outcome/behavior metrics
    stores trial history and provenance
              |
              v
Optuna study
    learns which numerical regions perform better
    prunes clearly poor trials where valid
    returns candidate Pareto/best configurations
              |
              v
Review + deterministic/live validation
    reject pathological exploitation
    verify behavior remains strategically coherent
    promote accepted constants into production code
```

No optimizer result is automatically promoted to production.

## Initial tunable families

Tuning must be staged. Do **not** expose the entire catalogue at once.

### Phase A — Composition calibration

The implemented first search space is deliberately smaller than the eventual family. It currently tunes:

- realization priority weight;
- generic synergy bonus;
- generic conflict penalty;
- monotonic R1-R5 pivot-resistance values.

Per-Bond thresholds/contributor weights and motif values remain locked until the first Phase-A study is validated.

### Phase B — Realization calibration

Candidate parameters include bounded thresholds used to classify `DORMANT`, `PARTIAL`, `ACTIVE`, and `MATURE` when those thresholds are empirical rather than mechanically exact.

Mechanically exact trigger requirements are **not tunable**.

### Phase C — Pivot / preservation calibration

Candidate parameters include:

- minimum structural gain required to abandon an established engine;
- power-engine protection margins;
- buildup/runway penalties;
- realized-motif disruption cost;
- health-mode-dependent pivot thresholds.

### Phase D — D1 Bond execution calibration

Candidate parameters include bounded preference strengths for already-legal/safe alternatives, such as:

- Bond hand-fit tie-break influence;
- first-discard engine opportunity value;
- preservation vs development trade-offs;
- safe-equivalent prescription preference strengths.

Survival legality and authoritative boss mechanics remain non-tunable constraints.

### Phase E — Shop / D2 / resource calibration

Candidate parameters include:

- Bond-transition acquisition bonus caps;
- replacement admission margins;
- formation/search reserve floors;
- speculative pack opportunity cost;
- late-game cash reserve thresholds;
- bounded reroll-search thresholds.

### Phase F — Cross-system calibration

Only after A-E are individually stable may a small selected set of cross-system parameters be tuned jointly.

## Evaluation protocol

Every trial must be reproducible and comparable.

Preferred protocol:

1. Load one immutable candidate parameter set.
2. Evaluate it on a fixed seed/batch schedule shared with competing trials when the environment supports seeded simulation.
3. When authoritative live Balatro cannot be perfectly seeded, use larger repeated batches and preserve exact run provenance.
4. Aggregate both competence and behavior metrics.
5. Store the trial parameters, code revision, seed/run IDs, metrics, and outcome.
6. Never modify production constants mid-trial.

A trial that crashes, violates legality, exposes hidden information, or produces invalid telemetry is failed rather than rewarded or silently skipped.

Authoritative live trials additionally require a fail-closed preflight before **every** trial: settled `BLIND_SELECT`, fresh Ante 1, expected deck/stake identity, compatible bridge protocol, and a non-disabled achievement gate. Lost batches are reset to a fresh run boundary and then preflighted again before the next candidate.

## Objective design

Win rate is the primary competence signal but must not be the sole objective. A win-only optimizer can overfit to brittle or degenerate behavior.

The tuning harness records:

- win rate;
- average and median Ante reached;
- blind-clear margin;
- boss clear rate;
- scoring/scaling trajectory signals;
- survival margin;
- power-engine activation/utilization rate;
- unused-active-engine rate;
- destructive-pivot rate;
- motif maturity;
- cash reserve failures;
- illegal-action count;
- D1 mean/max wall clock;
- build diversity.

The current Phase-A implementation uses one conservative scalar objective for the narrow composition family. Later studies may add multi-objective/Pareto analysis when the metrics and sample sizes justify it.

## Anti-overfitting requirements

- Keep training/tuning seed batches separate from holdout validation batches where seeded simulation is available.
- Re-evaluate promoted candidates on fresh seeds/runs.
- Prefer improvements that survive several batches rather than one lucky batch.
- Track variance and confidence, not only mean score.
- Reject configurations that improve the objective by exploiting logging gaps, pathological stalling, excessive rerolls, hidden information, or one degenerate forced build.
- Preserve build diversity; the Bond system exists to compose around RNG rather than force one route every run.

For authoritative unseeded live evidence, report deltas are descriptive only. The implemented live promotion comparator requires repeated evidence, checks Wilson win-rate intervals, sample count, objective improvement, Ante non-regression, D1 runtime, diversity, and illegal actions. It never writes candidate values into production automatically.

## Pruning policy

Pruning is permitted only when intermediate metrics are comparable and cannot hide late recovery behavior.

Safe examples may include repeated early catastrophic failure across a minimum number of completed episodes. Do not prune an episode itself merely because its early Ante score is weak; Balatro can recover through later shop RNG.

The initial live implementation uses no episode-level pruning. This remains deliberate until repeated study telemetry proves a conservative pruning rule is safe.

## Parameter ownership

Production code remains the source of semantic truth. Tunable values live behind a typed calibration/config layer so a trial can override values without source rewriting.

Requirements:

- explicit names and bounds;
- defaults equal current production behavior;
- immutable snapshot per trial;
- validation of monotonic relationships where required;
- no invalid combinations;
- serialized configuration for exact replay;
- no dependence on Optuna from the normal live-agent import path.

The current `BondCalibration` snapshot satisfies this boundary. Normal production imports see `DEFAULT_BOND_CALIBRATION`; offline evaluators use a context-local immutable override for one complete trial.

## Storage and reproducibility

Meaningful experiments use persistent Optuna SQLite storage. Each study records:

- study name and tuning phase;
- repository commit SHA;
- playbook/deck/stake;
- parameter schema version;
- objective version;
- run/seed schedule where applicable;
- exact live session/run IDs for authoritative trials;
- full calibration snapshot;
- trial metrics and outcome.

A resumed study rejects incompatible parameter/objective/repository/deck/stake/attempt contracts unless an explicit migration exists.

The production-default point is queued once and every completed trial is explicitly tagged `production_baseline=true/false`. `--baseline-only` exists for the first authoritative live validation of a fresh study.

## Promotion gate

An optimized parameter set is not production-ready until all of the following pass:

1. deterministic Balatro suite green;
2. candidate beats or materially improves the baseline on its tuning batch;
3. candidate improvement persists on a holdout/fresh batch;
4. no new architecture or execution defect is visible in logs;
5. no unacceptable collapse in build diversity;
6. no meaningful D1/runtime regression;
7. relevant Bond diagnostics remain interpretable;
8. manual review confirms that the optimizer improved numerical balance rather than changing intended semantics.

After promotion, accepted values become the reviewed production baseline for subsequent studies. Promotion remains an explicit code/documentation change; the tuner cannot edit production constants itself.

## LLM / higher-level analysis

An LLM may assist **offline** with experiment interpretation, anomaly classification, parameter-family selection, and code review. It should not directly decide trial outcomes or arbitrarily rewrite constants without empirical evidence.

Useful offline questions include:

- Why is a high-rank Bond remaining only PARTIAL?
- Is a repeated loss caused by parameter balance, execution wiring, or unavoidable RNG?
- Which parameter family best explains destructive pivots?
- Did an apparently better trial collapse build diversity?
- Is an optimizer exploiting a metric rather than improving play?

Numerical search belongs to the optimizer; semantic diagnosis remains an architecture/review task.

## Implementation order

1. [x] Document the subsystem and acceptance rules.
2. [x] Introduce a typed, immutable Bond calibration snapshot with current production defaults.
3. [x] Route a small, audited parameter family through that snapshot without changing defaults.
4. [x] Add deterministic tests proving default equivalence and invalid-config rejection.
5. [x] Build offline seeded and authoritative-live batch evaluator boundaries with structured trial metrics.
6. [x] Add Optuna as an optional development/tuning dependency only.
7. [x] Implement persistent studies, schema/revision compatibility, baseline queuing, and exact trial provenance.
8. [x] Implement the first low-dimensional Phase-A composition/pivot search space.
9. [x] Add holdout validation, baseline-aware reports, authoritative live preflight, and conservative live promotion comparison.
10. [ ] Execute and inspect the first production-default authoritative live baseline study.
11. [ ] Begin candidate Phase-A trials only after baseline telemetry is valid and no runtime defect is exposed.
12. [ ] Expand parameter families only after the preceding phase demonstrates stable improvement.

## Current status

As of 2026-08-23 the **tuning foundation is implemented**. The calibration layer, Optuna study machinery, persistent provenance, seeded/live evaluators, live log metrics, fresh-boundary preflight, production-baseline tagging, reports, and conservative promotion comparison are present. Broad catalogue tuning is still locked.

The next empirical gate is the first authoritative production-default live baseline. If that baseline exposes another semantic/runtime defect, fix the agent first and invalidate/restart the study at a new repository SHA. Only a clean baseline permits Phase-A candidate trials.

The standing rule remains:

> Correct semantics and execution first; automate numerical sweet-spot search second.
