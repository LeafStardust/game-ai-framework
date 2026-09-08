# Balatro SHOP Runtime Contract

Date: 2026-08-27

This document records the systemic runtime pass opened after repeated Red/White live stalls were traced to several different SHOP-side fan-out mechanisms. It supplements `BALATRO_LIVE_VALIDATION_GATE.md`.

No tests or live games were run by the assistant. Deterministic and live validation remain user-run gates.

## Triggering live attempt

Latest uploaded attempt used for the systemic pass:

- run: `balatro-20260826T193507Z-88c5b712-attempt-001`
- Red Deck / White Stake
- the final successful action is `END_ROUND` from `ROUND_EVAL`
- its authoritative after-state is `SHOP`, sequence 114
- money: $21
- Ante 2 / Round 5
- owned Jokers: 1 / 5

The JSONL ends before the next successful transition. Because run-experience JSONL observation/decision records are written only after a successful step is persisted, absence of the next event is not by itself proof that observation, policy, or execution was the blocking layer. The systemic pass therefore audited all SHOP-reachable expectation/search paths rather than patching only the final visible checkpoint.

## Global runtime rules

### 1. No D1 recursion beneath hypothetical D2/D14 Build Health

The real current SHOP may still run the bounded public-state D1 clear-probability projection. Internal Joker candidate/replacement/bundle states are marked with `_rw_internal_build_health_projection` and use the existing generic Build Health estimate instead.

This removes the previous multiplier where every hypothetical D2/D14 transition could launch four sampled opening hands, each with a bounded D1 expectimax search of up to 96 nodes.

Real D1 gameplay search is unchanged.

### 2. Retire the legacy named two-Joker bundle override

`PlaybookBuildHealthShopArbiter._bundle_decision` no longer re-opens a completed canonical SHOP decision through the historical hard-coded pair catalogue. Canonical Bond/composition and D14 arbitration remain authoritative.

The historical planner module remains in the repository for compatibility/history, but it is not a parallel production SHOP authority.

### 3. One expectation layer for unopened/future stochastic resources

Unopened D8 Arcana/Spectral and D14 held-consumable future-use value capture the base D9 stochastic/deferred classifications. Those hypothetical outcomes retain their real probability mass but contribute zero instead of recursively solving another generated-resource expectation.

Actual opened-pack/held-use D9 decisions retain their complete models once the outcome is genuinely visible.

Omitted probability mass is never renormalized, so this is a conservative lower bound rather than synthetic optimism.

### 4. Small deterministic SHOP future-hand budget

SHOP-side future-option models now use:

- exact combination limit: 16
- sampled-hand count: 8

This applies to held-consumable future-use and hand-size opportunity valuation. It does not change real D1 gameplay search.

Previously these models could enumerate up to 128 exact hands or 24 sampled hands and then enumerate legal plays/full D9 value inside each branch.

### 5. Same-state family expectation memoization

Arcana, Spectral and Standard unopened one-offer expectations are memoized for the same translated SHOP state object. Duplicate packs from the same family in one shop reuse the same family expectation rather than recomputing it.

Pack-specific price/resource accounting remains outside the memoized family expectation and is still evaluated independently by D8/D14.

### 6. Large public-Joker expectation remains bounded

Large future-Joker pools remain fully preflighted for modeling completeness, but expensive scoring uses:

- one deterministic public record per rarity
- at most 12 fully wrapped D2 evaluations
- omitted public probability mass contributes zero and is never renormalized

Those D2 calls are now substantially cheaper because hypothetical Build Health cannot recurse into D1.

## Remaining stochastic evaluator audit

The following opened-outcome models were reviewed for SHOP-reachable fan-out:

- Aura: at most visible hand size × 3 edition branches
- Sigil: exactly 4 suit branches across the visible hand
- Hex: at most owned Joker count branches, each using the fixed B3 probe set
- Wheel of Fortune: at most owned Joker count × 3 edition branches, each using the fixed B3 probe set
- Ankh: bounded by owned Joker count
- Ouija/Ectoplasm: their actual opened models may use hand-size/future-Joker value, but unopened D8/future held acquisition is stopped at the one-layer stochastic boundary; hand-size opportunity is under the shared 16/8 SHOP budget
- Standard: exact generator remains factorized to 64 contextual B6 graph evaluations, with same-state memoization for duplicate packs
- Celestial: impossible headroom/reserve states short-circuit before finite Planet expectation while preserving D8 resource accounting

No additional unbounded or recursively nested SHOP planner was found in this audited stochastic set.

## Validation gate

Run only the deterministic suite first:

```powershell
python -m pytest tests/balatro -q
```

Do not begin numerical tuning until this semantic/runtime HEAD is deterministic-green and a subsequent production baseline demonstrates interactive SHOP responsiveness without obvious semantic contradictions.
