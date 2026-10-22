# Live review after visual-verification optimization

Session `20261022T064356-902665Z`, October 22, 2026, Malaysia.
Revision `9286b71f`; Three-Player South Attack v0.2 in a verified AI room.
Our seat was 1, not the dealer's initial seat 0.

## Match

Complete South match, thirteen ended hands including a draw and dealer repeats.
Second place, 26,500 points. Final scores by seat: 52,500 / 26,500 / 26,000.
Our three wins were 1 Han Ron, 6 Han Ron and 6 Han Tsumo. Two deal-ins cost
1,700 and 12,000 including applicable Honba. Always accept a legal offered win;
the one-Han result is not itself a violation of high-value development priority.
One match does not justify tuning attack into hindsight-driven defense.

The completion lookahead ran on 36 decisions and changed eight baseline actions.
These observations do not establish counterfactual win value or improvement.

## Runtime

All 167 unique controller submissions confirmed, no blocked/error/retry-delivered
rows. There were 102 rejected visual preflights across the longer thirteen-hand
match. Moving tiles, ambiguous samples and buttons remain sources of delay.
Three freshness failures withheld input rather than sending an old proposal.
No waiting-visual expiry rows were recorded.

Median preceding-event-to-decision interval: 0.128 seconds across 178 decisions;
maximum 0.766 seconds. Median recommendation-to-submit interval: 1.422 seconds
across 167 unique actions; maximum 5.004 seconds. The earlier five-hand South
recording had median 2.438 seconds. The observed median is about 42% lower,
but different hands, assists and animations prevent a controlled attribution.
Successful preflight timing is now recorded: median 0.580 seconds, maximum 0.748
across 167 successful preflights. It includes capture, journal and verification
work, not just the exact-distance optimization.

Auto Kita ON was visually confirmed in each of the thirteen hands. Eight own
North-extraction events were observed, alongside eight extraction recommendations;
the journal does not establish that these were exclusively client-automatic
rather than agent-delivered. Do not claim otherwise. Auto Win was reconciled
before Kita, and an obsolete Auto Discard request was safely superseded.

Twelve result-button clicks were delivered: six used OCR and six used templates.
Ten have explicit result confirmation rows. The final unmatched rows cannot be
claimed successful merely from delivery. Both win-detail and round-score Confirm
were separately attempted in the same hand. No Continue attempt was recorded,
so this match did not validate the Continue path. Remaining OCR and client result
animations can still cause multi-second waits; the fast path is not universal.

## Next

Keep this policy version unchanged. Next improvement should target recurring
button/tile recognition and OCR misses using saved frames, while preserving
fresh-state checks. More games are useful for performance and decision review,
but no fixed win-rate claim follows from the current small sample. No game or
agent was started during this audit. User YAKU.md edits remain untouched.
