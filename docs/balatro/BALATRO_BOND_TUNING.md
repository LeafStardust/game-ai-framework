# Balatro Bond Tuning

Status: **Planned / documentation-first**

This document defines the automated numerical calibration layer for the canonical Balatro Bond/composition architecture.

The tuning subsystem is intentionally **offline**. It must never sit inside the live decision loop, call an LLM during gameplay, expose hidden RNG/future draw order, or change the semantic meaning of a Bond during a run.

## Purpose

The Bond catalogue is dynamic even though its evaluators, thresholds, weights, relationship values, realization rules, and policy coefficients are implemented in code. Those numbers require repeated empirical calibration until they reach stable sweet spots across many public-state runs.

Manual five-run batches remain useful for finding architecture and execution defects, but they are too expensive and noisy for systematic numerical tuning. The planned Optuna subsystem will automate bounded search over approved parameter families while the deterministic Balatro agent remains the evaluated subject.

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

Candidate parameters include:

- per-Bond R1-R5 contribution thresholds;
- approved contributor weights;
- realization priority weights;
- generic synergy bonus;
- generic conflict penalty;
- R1-R5 pivot-resistance values;
- motif potential/active/mature structural values where those values are genuinely numerical policy parameters.

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

## Objective design

Win rate is the primary competence signal but must not be the sole objective. A win-only optimizer can overfit to brittle or degenerate behavior.

The tuning harness should record at least:

- win rate;
- average and median Ante reached;
- blind-clear margin;
- boss clear rate;
- scoring/scaling trajectory by Ante;
- survival margin entering the next blind;
- relevant Bond ranks and realization states by Ante;
- power-engine activation/utilization rate;
- unused-active-engine rate;
- destructive-pivot rate;
- motif activation/maturity rate;
- economy efficiency and cash reserve failures;
- Joker formation quality;
- illegal/failed-action count;
- D1 wall-clock and timeout statistics;
- build diversity across the batch.

The first implementation may use a scalar objective for one narrowly scoped parameter family. Later studies should support multi-objective/Pareto analysis where appropriate, especially for competence vs diversity vs runtime.

## Anti-overfitting requirements

- Keep training/tuning seed batches separate from holdout validation batches where seeded simulation is available.
- Re-evaluate promoted candidates on fresh seeds/runs.
- Prefer improvements that survive several batches rather than one lucky batch.
- Track variance and confidence, not only mean score.
- Reject configurations that improve the objective by exploiting logging gaps, pathological stalling, excessive rerolls, hidden information, or one degenerate forced build.
- Preserve build diversity; the Bond system exists to compose around RNG rather than force one route every run.

## Pruning policy

Pruning is permitted only when intermediate metrics are comparable and cannot hide late recovery behavior.

Safe examples may include repeated early catastrophic failure across a minimum number of completed episodes. Do not prune an episode itself merely because its early Ante score is weak; Balatro can recover through later shop RNG.

The harness should initially use conservative pruning or no pruning until trial metrics are validated.

## Parameter ownership

Production code remains the source of semantic truth. Tunable values should gradually move behind a typed calibration/config layer so a trial can override values without source rewriting.

Requirements:

- explicit names and bounds;
- defaults equal current production behavior;
- immutable snapshot per trial;
- validation of monotonic threshold relationships where required (for example `R1 < R2 < R3 < R4 < R5`);
- no invalid combinations;
- serialized configuration for exact replay;
- no dependence on Optuna from the normal live-agent import path.

## Storage and reproducibility

Use persistent Optuna study storage rather than ephemeral in-memory studies for meaningful experiments. Each study should record:

- study name and tuning phase;
- repository commit SHA;
- playbook/deck/stake;
- parameter schema version;
- objective version;
- run/seed schedule;
- trial metrics and artifacts;
- accepted/rejected promotion status.

A resumed study must reject incompatible parameter/objective schema versions unless an explicit migration exists.

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

After promotion, the accepted values become the new baseline for subsequent studies.

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

1. Document the subsystem and acceptance rules. **(this document)**
2. Introduce a typed, immutable Bond calibration snapshot with current production defaults.
3. Route a small, audited parameter family through that snapshot without changing behavior.
4. Add deterministic tests proving default equivalence and invalid-config rejection.
5. Build an offline batch evaluator that returns structured trial metrics.
6. Add Optuna as an optional development/tuning dependency only.
7. Implement persistent studies and reproducible trial provenance.
8. Start with one low-dimensional study (composition/pivot calibration), not the full catalogue.
9. Add holdout validation and promotion reports.
10. Expand parameter families only after the preceding phase demonstrates stable improvement.

## Current status

As of 2026-08-23 the canonical Bond/composition runtime remains under Red/White live calibration. Recent live batches exposed execution/pivot/resource-policy defects that must be corrected before broad numerical optimization is trustworthy. Therefore the Optuna subsystem is **approved/planned but not yet allowed to tune around known runtime bugs**.

The immediate rule is:

> Correct semantics and execution first; automate numerical sweet-spot search second.
