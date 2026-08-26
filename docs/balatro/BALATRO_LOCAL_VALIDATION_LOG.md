# Balatro Local Validation Log

Status: **Current HEAD awaiting user-local deterministic validation**

This log records regression-suite defects and contract corrections discovered after the semantic/runtime Red/White audit. The assistant does not run the suite; the user executes `tests/balatro` locally and reports failures.

## 2026-08-27 — five-failure full-suite batch

The uncapped local suite reached five remaining failures. Static inspection classified them as regression-fixture contract drift rather than reasons to weaken current production semantics:

- D9/D10 targeted Chariot production-boundary fixture still used the retired opened-pack `skip_bias=0.35`. Opened pack cost is sunk, so D9/D10 target value is compared against Skip=0.
- the raw replacement-delta regression used bare `object()` identity through `deepcopy`; the fake evaluator therefore assigned the same value to the copied incumbent and candidate. The fixture now uses a deepcopy-stable semantic marker while continuing to verify that Bond-transition bonus is excluded from the mechanical replacement delta.
- the early first-engine regression required the late Red/White bootstrap rationale even when ordinary D2 already admitted the positive literal scorer. The behavioral contract is BUY with positive grounded build gain; bootstrap text is required only when that wrapper actually converts HOLD to BUY.
- the D14 deterministic-voucher regression compared `BalatroAction` wrapper identity. The executable semantic identity is action type plus the exact visible target; policy wrappers may reconstruct the action container.
- the saturated paid-reroll regression assumed a full ordinary Joker roster makes future Joker option EV exactly equal to HOLD. A generated Negative Joker is slot-neutral, so the public eligible-Joker expectation may remain slightly positive; the required behavior is still HOLD once paid-reroll resource cost is applied.

No production threshold, hidden-information assumption, or win-first authority was relaxed for this batch.

## Local command

Run from repository root:

```powershell
python -m pytest tests/balatro -q
```

Do not start live calibration until this deterministic gate is green.
