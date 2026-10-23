# Live assist latency review

Session: `20261023T071725-098919Z`, revision `32b642ff`.
Verified three-player South AI room, eight hands. Finished third with 23,600
points, versus 25,900 and 55,500. One win: five-Han dealer Tsumo.
Two deal-ins: 7,700 and 6,600 including repeat counters.

## Input reliability and timing

All 102 submitted gameplay actions received server confirmation. No input-failure
or action-failure events were recorded. This demonstrates delivery in this match,
not policy strength or universal reliability.

Recommendation availability to completed submission: median 1.466 seconds,
maximum 4.291. Eight actions met one second; 54 met 1.5 seconds; 48 exceeded it.
This metric excludes policy computation before the recommendation.

| Recorded work before submission | Actions | Median | Maximum |
| --- | --- | --- | --- |
| No rejected preflight or assist attempt | 31 | 1.024 s | 1.425 s |
| Rejected preflight, no assist attempt | 68 | 1.736 s | 3.138 s |
| Assist attempt | 3 | 3.586 s | 4.291 s |

Groups are descriptive, not controlled comparisons. There were 110 rejected
preflights: forty involved slot 13, eighteen an unavailable/ambiguous Skip button,
eleven moving UI, and six an unavailable/ambiguous Extract North button.
These observations identify animation and recognition retries as the next focus;
they do not justify clicking before the actual target is verified.

All seventeen assist changes were confirmed: Auto Win enabled eight times,
Auto Kita six times, Auto Discard twice and Skip Calls once. Attempt-to-confirm
ranged from 0.945 to 1.565 seconds. Between-turn preparation reduced own-turn
setup exposure, but three submissions still included setup. The one-second ideal
and 1.5-second upper target have not been achieved consistently.

Sixteen result Confirm clicks were delivered; seven explicit game-state-advanced
confirmations were recorded. Delivery alone does not establish every result-stage
click succeeded. Two stale result recognitions were withheld because pixels or
screen context changed. No recorded Continue click exercised that control.

Next: profile capture/assist verification and drawn-tile animation retries to
reduce latency without dropping board, window, hand or visual-target checks.
No agent was launched and no game input was sent during this review.
