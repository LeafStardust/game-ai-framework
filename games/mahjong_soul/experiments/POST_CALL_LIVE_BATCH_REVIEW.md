# Live batch after the post-call settling fix

Latest run used revision `f72e2c46` with a three-completed-game limit. Three
match completions were counted, two automatic room Start clicks were delivered,
and the worker stopped normally at game_limit_reached. Four game connections
authenticated during the run; the first connection became incomplete without a
recorded terminal match state before the next authenticated connection. It is
not an additional completed result and must not be assigned a placement from
an intermediate hand score.

The three counted completed matches finished third with 27,100 points, third
with -2,700, and first with 81,700. The last result is derived from the final
server Hule scores plus the previously verified own seat, because the worker
stops at the terminal event rather than capturing a later result screen.
Mean placement across these three completed matches was 2.33. This small AI
sample is not a strength estimate; the bust in match two remains a poor outcome.

All 204 submitted gameplay actions received server confirmations. No blocked
input, input failure, decision rejection, error or recovery event was recorded.
Four preflight rejections explicitly detected standing call-animation tiles
beyond the concealed hand. No post-call unmatched discard occurred in this run.
That is positive live evidence for the settling guard, not universal proof.

There were 46 assist attempts: 43 confirmed and two explicitly superseded by
fresh observed state/preferences. No assist timeout or native fallback occurred.
The remaining attempt had no explicit confirmation before completion; do not
count it as a verified switch change. Thirty-six result clicks were delivered,
with seventeen explicit game-state-advanced confirmations. Delivery alone is
not confirmation of each result-stage click.

Recommendation-to-completed-submission latency: median 1.392 seconds, maximum
6.163, 109 of 204 at or below 1.5 seconds and 95 above. Policy computation before
recommendation is excluded. The 1-second ideal / 1.5-second target remains unmet
consistently. There were 139 rejected preflights overall. Recording retention
ran and did not stop the batch.

Next focus: isolate long setup/animation waits and capture overhead while
keeping the new post-call guard. Gameplay value/speed quality also needs more
than a single high-scoring win to offset repeated third places. No code changed,
no agent was launched, and no native input was sent during this review.
