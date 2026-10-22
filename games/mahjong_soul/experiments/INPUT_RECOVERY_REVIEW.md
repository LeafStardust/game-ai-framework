# Recover automatically after uncertain input advances

Session `20261022T103714-684756Z` stopped at input attempt 1936. WindowsMouse
raised `Mahjong Soul is not the foreground window` during a double-click. The
controller correctly retained the uncertain attempt, but AutoFollower's halted
branch only drained capture and recorded screenshots forever, never attempting
its existing newer-board recovery. A later game step could not resume play.

## Correction

While input is blocked and has a pending plan, continue reading capture and
wait for proof of advancement. Do not blindly resend the same uncertain step.

- On a newer playable board, run normal two-frame visual preflight without
  sending input. This requires the current foreground client, unchanged geometry,
  fresh matching source/board, exact visible hand and verified AI room. Then use
  the controller's existing newer-step recovery, preserving attempted-step keys.
- A later server Hule, exhaustive draw or abortive draw may retire the pending
  attempt directly. Require the same connection/generation and a later step or
  later round. This allows result buttons and subsequent rounds to proceed.
- After recovery, clear stale call/Riichi menu continuations and candidates.
  If timeout handling already consumed a recommendation for the newer turn,
  preserve it for the next poll rather than silently losing the turn.
- If still on the uncertain original board or the window/visuals cannot be
  verified, keep waiting automatically. Returning foreground alone does not
  authorize replaying a possibly delivered click. Existing same-board ordinary
  discard timeout retry remains bounded and separately visually verified.

The original action ledger is retained across recovery. No new action can reuse
the old reservation. Failures outside a blocked pending input, such as unrelated
configuration/source errors, retain their explicit blocked behavior; this is not
a catch-all suppression of errors or arbitrary process restart.

## Checks

Tests cover unchanged-board refusal, failed visual verification, successful
new-turn recovery without an extra click, actual polling resumption only on the
new step, server-ended retirement, foreign/stale end rejection, and preserving
an already-considered newer suggestion during timeout recovery.

Full suite after the base recovery change: 894 passed, one skipped. The final
newer-suggestion preservation case and updated polling path were then verified
with all 38 native AutoFollower tests passing. These are offline tests; no game
or agent was launched and no mouse input sent during development. The installed
agent must be restarted once to load the fix. Future eligible focus/input stalls
can then recover without asking the user to restart for each incident.
