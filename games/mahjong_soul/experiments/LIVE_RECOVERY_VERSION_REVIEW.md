# Live match with automatic-recovery version

Session `20261022T112115-168977Z`, October 22, 2026, Malaysia.
Revision `3e1e2d36`, Three-Player South Attack v0.2, authenticated AI room.
Our seat was 0. The complete match ended after six hands.

Second place, 39,200 points. Two hand wins (both 6 Han Tsumo), one deal-in
costing 2,600. The other player's final 18,000-point deal-in ended the match;
it was not our deal-in. These outcomes are observational, not a controlled
measure of policy strength.

All 70 unique controller submissions confirmed. No input failure, error, blocked
row, timeout retry delivery or automatic input recovery was recorded. The final
heartbeat is idle with no halted reason. Thus no indefinite stop occurred, but
this match did not exercise the new recovery path and cannot prove its live
recovery reliability.

Auto Kita ON was confirmed in all six hands. Eight result clicks delivered,
six via templates and two via OCR; five explicit result confirmations. All
result labels were Confirm; Continue was not exercised. The OCR attempts were
classified as match_results, which is the fallback stage when OCR finds no
Han/Fu or Counter token; that label alone does not prove a final ranking screen.
No repeated retry was needed. Remaining recognition work includes those OCR
fallbacks and transient offer/tile ambiguity.

Median preceding-event-to-decision interval was 0.165 seconds across 79 decisions;
maximum 0.873 seconds. Median recommendation-to-submit interval was 1.280 seconds
across 70 unique actions, maximum 4.163 seconds. The preceding thirteen-hand
recording had median 1.422 seconds, but these are uncontrolled different hands.
There were 44 rejected preflights and no waiting-visual expiry rows. The bounded
South completion model ran on fifteen decisions and changed one baseline choice.

Next: retain the current policy and continue ordinary live validation. No
strategy adjustment is justified solely by this second-place result, and no
restart-per-incident or manual input was performed during this audit.
