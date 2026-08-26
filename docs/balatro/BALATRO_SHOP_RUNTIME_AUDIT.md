# Balatro SHOP Runtime Audit

Date: 2026-08-27

Status: implementation complete; pending user local deterministic validation and fresh Red/White live baseline.

No tests or live games were run by the assistant.

## Why SHOP appeared stuck

The observed live cases are consistent with finite but catastrophically expensive policy computation rather than a bridge deadlock. A SHOP checkpoint can be fully settled and the supervisor can remain `THINKING` while D8/D11/D14 waits for nested expectation work to return. Operationally this is still a runtime defect because a live shop decision must complete interactively.

## Observed runtime blowups

### Celestial

A finite Planet expectation ran before an authoritative no-headroom/reserve veto that already forced HOLD. The final Red/White Celestial fast path now preserves ordinary D8 resource accounting while skipping the finite Planet enumeration when it cannot affect the decision.

### Buffoon / future Joker expectation

A live White-Stake catalogue exposed 116 eligible public Jokers. The original future-Joker model expanded records, public initial-state branches, and editions through the fully wrapped D2/D14 acquisition path. A first large-pool repair made this conservative and bounded, but the initial 48-D2-call budget was still too expensive beside other shop expectations.

Large pools now retain the same full preflight and zero-mass conservative semantics but use one deterministic public record per rarity and at most 12 fully wrapped D2 calls. Pools of at most 24 records remain exact. Unevaluated probability mass is not renormalized.

### Standard

One unopened Standard Pack integrated 52 ranks/suits × 9 enhancement states × 4 edition states × 5 seal states = 9,360 public probability branches and previously reran the contextual B6 graph for every branch. Exact factorization preserves all 9,360 branches and final positive-value clipping while reducing contextual graph evaluations to 64.

### Arcana / Spectral pool-of-pools recursion

Latest uploaded production attempt:

- log: `balatro-20260826T181633Z-13624626-attempt-001.jsonl`
- Red Deck / White Stake
- Ante 1 / Round 1
- The Hermit was bought successfully through D14
- The Hermit was then used successfully through the held-consumable improvement path
- the next same-shop arbitration recomputation did not emit another decision before the user stopped the run
- remaining visible boosters were Buffoon Pack and Arcana Pack

This isolated a broader structural issue. Unopened D8 Arcana and Spectral value creates hypothetical opened-pack states and sends each public outcome through installed D9. Some of those hypothetical outcomes themselves generate another random public option pool:

Arcana nested generated-resource outcomes:

- The Emperor → Tarot generation expectation
- The High Priestess → Planet generation expectation
- Judgement → Joker generation expectation

Spectral nested generated-resource outcomes:

- Familiar
- Grim
- Incantation
- Wraith
- The Soul

Actual opened-pack D9 needs those complete public-state models. Unopened D8 does not need to recursively synthesize a second random option space merely to obtain its already-conservative one-offer lower bound.

## Systemic one-step expectation rule

`shop_expectation_runtime_bound_policy.py` installs at the final Red/White correction boundary.

For an unopened Arcana/Spectral expectation:

1. The immediate public offer pool is still integrated.
2. Ordinary deterministic/contextual outcomes are still scored through installed D9.
3. A hypothetical outcome whose mechanic generates another random resource pool contributes zero at D8 instead of recursively expanding that second pool.
4. Its real probability mass remains in the denominator; it is never renormalized away.
5. Therefore the shortcut can only understate unopened booster value; it cannot invent optimism.
6. Once the pack is actually opened, normal D9 receives the real visible outcome and retains the full Emperor/High Priestess/Judgement/Wraith/Soul/etc. model.

This establishes a common runtime boundary: SHOP lookahead may evaluate one immediate public reveal layer, but hypothetical generated resources do not recursively create a pool-of-pools inside the same D8 decision.

## Commits

- `ace91f6` exact Standard contextual factorization
- `6bae6d8` Standard runtime-bound regression
- `caee192` systemic one-step Arcana/Spectral expectation and tighter public-Joker runtime policy
- `645f1f2` final Red/White installation wiring
- `afb2351` focused runtime-bound regressions

## Validation gate

Run locally:

```powershell
python -m pytest tests/balatro -q
```

Only after the deterministic suite is green, restart the Python agent process and run:

```powershell
.\BalatroAgentToggle.bat --three
```

Do not begin numerical calibration/Optuna until the live three-attempt baseline completes SHOP arbitration without these runtime stalls and the resulting decisions are semantically reviewed.
