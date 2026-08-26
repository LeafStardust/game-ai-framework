# Balatro SHOP Runtime Audit — 2026-08-27

This note records the live-runtime defects found while validating Red Deck / White Stake competence. It is specifically about interactive SHOP responsiveness, not numerical tuning.

## Important logging correction

The run-experience JSONL is transition-oriented. Observation and decision records for a step are persisted as part of a successful transition. Therefore, the absence of the next `observation` event after a previous `action_result` does **not** by itself prove that the observer is blocked; the next transition may still be inside observation, policy computation, execution, or postcondition settlement.

The monitor telemetry and elapsed timestamps across completed transitions must be used together with the log when classifying stalls.

## Observed slow SHOP in `balatro-20260826T191557Z-afcb5484-attempt-001`

After buying the Base Joker, the next visible shop contained:

- DNA
- Standard Pack
- Spectral Pack
- Magic Trick

The purchase transition was logged at `2026-08-26T19:17:33.943984Z`. The next observation/decision transition completed at `2026-08-26T19:18:00.962963Z`, approximately 27 seconds later. This demonstrates a finite but operationally unacceptable SHOP computation path.

The same run later reached another SHOP after cash-out with a complete public snapshot but no subsequent successful transition before the user stopped the agent.

## Root runtime class

D8 unopened booster valuation can accidentally solve second-order planning problems. A hypothetical Spectral outcome is first selected from the public eligible pool, then D9 may invoke a detailed outcome model for that hypothetical card. Some of those models themselves branch over additional public future states or expensive whole-build mechanics.

This is appropriate when the card is actually visible in an opened pack, but not when it appears only as one branch inside an unopened-pack lower-bound expectation.

`BalatroPackPolicy` already owns the semantic distinction through `DEFERRED_SPECTRALS`. The D8 runtime boundary now reuses that classification instead of maintaining an independent Joker-style tier list.

## Repair

Commit `dbdc561` changes the final Red/White runtime-bound layer so that:

- all `BalatroPackPolicy.DEFERRED_SPECTRALS` contribute their real outer probability mass but zero option value inside unopened D8 Spectral/Arcana expectations;
- The Soul remains omitted from nested unopened expectation for the same second-order reason;
- actual opened-pack D9 decisions retain the full explicit Spectral models;
- omitted mass is never renormalized, so the D8 value remains a conservative lower bound;
- Arcana, Spectral, and Standard one-offer expectation results are memoized by translated state-object identity, so duplicate packs of the same family in one D14 arbitration do not recompute the same family expectation.

Commit `4a01068` adds deterministic regressions for the deferred-Spectral boundary and same-state expectation memoization.

## Existing runtime protections retained

- Celestial hard-veto fast path avoids finite Planet work that cannot change HOLD.
- Standard exact one-offer generator remains exact but factorizes contextual B6 graph calls.
- large public future-Joker expectations remain capped at 12 fully wrapped D2 evaluations with omitted mass contributing zero.
- nested Tarot resource generators such as Emperor, High Priestess, and Judgement remain omitted from outer unopened D8 expectation.
- native action readiness remains strict.
- post-pack Joker visual settlement remains strict where geometry reflects an unfinished asynchronous callback.
- the duplicate general supervisor quiet barrier has been removed; semantic stability is owned by the bounded autonomous loop plus final stale-state verification.

## Validation gate

Run locally:

```powershell
python -m pytest tests/balatro -q
```

Only after deterministic green should the live three-attempt baseline resume.
