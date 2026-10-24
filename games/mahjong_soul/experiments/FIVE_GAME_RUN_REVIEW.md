# Five-game run review

Latest completed run used revision `f6c74ea2` with a five-match limit.
Five AI games authenticated, all five match completions counted once, four
custom-room Start clicks were delivered, and the worker exited normally with
`game_limit_reached`. There was no sixth Start attempt. This validates the
bounded multi-game loop in this run.

| Game | Place | Points |
| --- | --- | --- |
| 1 | 2nd | 40,900 |
| 2 | 1st | 55,200 |
| 3 | 3rd | 28,000 |
| 4 | 2nd | 39,700 |
| 5 | 2nd | 35,100 |

Mean placement was 2.0. The first four outcomes appear in ended-state frames;
the fifth is from the final server Hule scores and the previously verified
own seat because the worker stops immediately at the requested match count.
There were forty winning hands and three exhaustive draws, fourteen own wins
(six Ron, eight Tsumo), and eight own deal-ins. Five AI matches do not establish
ranked strength or statistically stable win rates.

Of 483 submitted gameplay actions, 482 received explicit server confirmation.
The remaining planned 1 Man discard was followed by a different own 7 Sou
discard. The controller blocked that attempt and recovered from the next
verified board after about 3.12 seconds. No confirmed explanation of the original
lost/mismatched input is available; do not mark it successful. There was also
one decision rejection with the logged reason: capture became stale or incomplete
during policy evaluation. The expiry-only retry correctly does not bypass a
capture-integrity/freshness failure. These are remaining reliability gaps.

All 117 assist changes were confirmed, so optional-assist native fallback was
not exercised. Eighty-seven result clicks were delivered, with forty-two explicit
game-state-advanced confirmations; delivery counters alone do not prove every
result-stage click succeeded. Restart recognition initially withheld some views
but eventually delivered all four required starts.

Input latency from recommendation availability to completed submission had a
median of 1.287 seconds and maximum of 5.076. Ninety-three of 483 met one second;
325 met 1.5 seconds; 158 exceeded 1.5 seconds. Policy computation before the
recommendation is excluded. The requested upper target is not consistently met.

Recording retention removed 1,097 older screenshot files in 1,033 recorded
pruning events while preserving the event journal and newest screenshot.
The run did not stop at its recording cap. Older pruned images are intentionally
unavailable for replay; deletion history identifies them explicitly.

Next development focus: determine why the unmatched discard was lost, and reduce
capture/preflight stalls without accepting stale proposals. No agent was launched
and no native input was sent during this read-only review. No policy changes or
new private session fixtures are included in this commit.
