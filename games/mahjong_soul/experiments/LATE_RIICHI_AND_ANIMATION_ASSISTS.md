# Late Riichi value and animation-time assists

## South Riichi

Add a narrow South attack heuristic: with at least two detected threats, eighteen or fewer wall tiles remaining, a legal non-furiten Dama wait with at least one publicly unseen copy and estimated Ron value at least 8,000 points, require Riichi value to reach 1.5 times Dama value before declaring. Continue attacking in Tenpai; this does not initiate folding. East speed books bypass this check. Earlier hands, cheap Dama hands and materially larger Riichi gains retain the previous rules.

The ratio and late-wall boundary are explicit heuristic choices, not a calibrated expected-value model. They do not price opponent win timing, hidden waits or Ura outcomes. The decision journal records late_valuable_dama_small_riichi_gain for rejected declarations; terminal output remains recommended actions only.

Offline replay of the reviewed last-hand decision now chooses ordinary 9 Sou discard in attack_push mode with zero Shanten. Previously it declared Riichi with that same discard. This change would not by itself have prevented the immediate double Ron. It addresses declaration value, not the user's always-push South risk preference.

## Kita setup

The slow setup trace began with a first-turn native Kita, then a replacement draw and native discard, before R and K could be prepared on an opponent turn. Permit R/K preparation during an existing failed visual-preflight wait. C/D enables remain deferred through this path; required disables still have priority. Switch recognition, two-frame checks, hand/round/connection guards, foreground checks and confirmation requirements are unchanged.

An automatic Kita may advance the hand during this preparation. The candidate board token is rechecked on the next normal poll before native action submission, retiring the obsolete candidate. No old native action is replayed. Preparation time is not free: it may still add latency if the game animation ends meanwhile, so live measurements must determine the net benefit.

Validation: 996 tests passed, one skipped. Synthetic regressions cover late valuable Dama, earlier and unthreatened Riichi, low-value Dama, R/K preparation, and C/D exclusion. The last-hand replay used local records only. No agent or game was started, and no private session payload was published.

Next: the user-started normal three-game run should check first-round K enable delay, overall decision-to-input latency, and any candidate invalidation following client Kita.
