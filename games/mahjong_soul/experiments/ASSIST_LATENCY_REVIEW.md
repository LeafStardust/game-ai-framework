# Move assist setup off the decision's critical path

Session `20261023T062329-081931Z` still had median recommendation-to-submit
latency of 1.691 seconds, maximum 7.893, across sixty confirmed actions. Thirty-six
exceeded 1.5 seconds. Separate those actions by recorded work:

| Group | Actions | Median | Maximum |
| --- | --- | --- | --- |
| No assist setup or rejected preflight | 17 | 1.059 s | 1.400 s |
| Visual retries, no assist setup | 38 | 1.965 s | 3.625 s |
| Assist setup during the decision | 5 | 4.132 s | 7.893 s |

These are descriptive timing groups, not controlled performance comparisons.
There were 103 rejected preflights, often draw/offer animation or ambiguous pixels.
Fresh assist-frame reuse was exercised 92 times, including failed preflights;
that counter does not mean 92 submitted actions.

## Changes

Previously assist polling was reachable only after a recommendation/candidate.
R and K setup therefore waited for our turn, serialized two switch operations,
and waited for later polling to confirm each. The sidebar also resets per hand.

The follower now prepares assists during tracking intervals without a proposal,
including opponents' turns. It still requires fresh capture, foreground, verified
AI room and idle input controller. Desired settings come from the current board,
not a previous hand's policy. Accepted Riichi controls Auto Discard/Skip Calls;
Auto Win is preferred before Kita. Natural ten-slot Thirteen Orphans or All Honors
qualification, a retained North or a North pair protects North even before the
next policy decision. Open fixed groups count toward the honor gate.

After the native click's normal release-consumption wait, read and confirm the
switch immediately on the same board/window. Unknown or unchanged states remain
pending without another click. Pending or known-mismatched switches are checked
after 100 ms instead of 500 ms; known pending setup cannot silently fall through
to gameplay while its short polling delay expires. Already-correct switches keep
the ordinary scan interval. No speculative blind toggles or repeated clicks.

The main loop now polls at 50 ms rather than 100 ms. Ordinary preflight's explicit
settling pause is 50 ms rather than 100 ms, still between two independently
captured/verified images. Geometry, board token, source freshness, complete hand
identity and sampled-pixel stability checks remain. Native press/release timing
is unchanged. These reduce fixed overhead; they do not authorize clicks on an
unfinished draw animation.

Each submission logs `input_latency`: recommendation-to-completed-submission
seconds, a one-second ideal, a 1.5-second upper target and an over-target flag.
That measurement starts when the recommendation is available and excludes policy
computation before it. Whole event-to-input response is therefore slightly longer.
These are performance targets for a usable UI, not a reason to drop a valid action
or promise all animations finish within 1.5 seconds. Ordinary terminal output
remains recommended actions; timing detail stays in the recording.

Next user-started AI match must verify actual first-turn setup timing, switch
confirmations and response distributions. Unit tests cover between-turn setup,
immediate confirmation, protected Yakuman qualification and the existing guards;
offline tests cannot establish the live target. No live game/agent or input was
started during this work.
