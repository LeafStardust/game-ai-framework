# Balatro SHOP Runtime Blocker — 2026-08-26

## Latest live evidence

Run: `balatro-20260826T184550Z-cc9ccec7-attempt-001`

The final successful `END_ROUND` execution returned an authoritative snapshot already in `SHOP`, with `state_complete=True` and live observer sequence `242`. The visible shop contained Certificate, Jolly Joker, Arcana Pack, Celestial Pack, and Paint Brush.

Unlike the earlier expensive D8/D11/D14 stalls, the log contains no subsequent `observation` event. Therefore the next policy arbitration never began.

## Root cause

The production autonomous stack had two settlement systems with contradictory timing semantics:

1. `LiveMemoryInjectedAutonomousLoop` uses a semantic two-snapshot stability test with a soft timeout, intentionally allowing harmless presentation animation to continue.
2. `SupervisorLiveMemoryBalatroObserver._wait_for_full_state_quiet()` required the raw `LiveMemoryBalatroObserver.sequence` to remain unchanged for a full quiet window, with a 20-second timeout.

The raw observer sequence fingerprints the full public payload, including per-card `ui` geometry. Normal card/shop animation can therefore advance the raw sequence even while all planner-relevant public state is unchanged.

Because the outer loop calls `observer.observe()`, the inner 20-second raw-sequence barrier can block inside one observation call. The outer semantic soft timeout never gets control back and cannot apply its intended animation-tolerant behavior. Monitor telemetry remains `THINKING` even though no SHOP policy calculation has started.

## Repair

Commit `c4b8e8e` changes the production `DiscardHistorySupervisorLiveMemoryBalatroObserver` general quiescence gate to compare a recursively frozen semantic snapshot that excludes `ui` fields.

The repair deliberately preserves:

- strict native readiness checks for BLIND_SELECT, SELECTING_HAND, ROUND_EVAL, SHOP, and open packs;
- the dedicated pack-to-SHOP Joker visual-settle barrier, where card geometry is genuinely evidence that an asynchronous native transition is still completing;
- semantic changes such as money, card identity, forced selection, shop contents, phase, and `state_complete`, all of which still reset the quiet timer;
- the final stale-state guard before execution.

UI-only motion may now change the raw observer sequence without resetting ordinary supervisor semantic quiescence.

Commit `0c24479` adds deterministic regressions proving that UI-only geometry/sequence churn does not reset the semantic quiet timer while an actual public-state change does.

## Validation gate

No assistant-side tests were run. User validation command:

```powershell
python -m pytest tests/balatro -q
```

Only after the deterministic suite is green should the unchanged HEAD be retried through the three-run Red/White production baseline.
