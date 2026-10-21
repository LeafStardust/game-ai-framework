# Three-Player East Speed v0.7: live review

Session: `20261021T105101-126627Z`, October 21, 2026.
Revision: `6ab8b863edac95d3cf353bc1a950edc78f025c6d`.
Authenticated three-player East AI room; recorded playbook version 0.7.

## Outcome

Second place, 38,200 points; final scores by seat: 38,200 / 18,100 / 48,700.
One hand win in three completed hands, no deal-ins. East 1 ended with an
opponent Ron against the other opponent; East 2 ended with an opponent Tsumo.
Our East 3 win was a 3 Han, 40 Fu Ron worth 5,200 points, plus the Riichi deposit.

## Execution

All 37 controller submissions received server confirmations. No recorded error,
blocked action, retry delivery or controller halt. Nineteen visual preflight
rejections occurred during animation or ambiguous tile/button recognition;
subsequent attempts progressed without an unconfirmed submitted action.
These rejections remain a latency cost, rather than evidence of flawless vision.

Three result-button clicks were delivered; two have explicit confirmation rows.
The final click has no explicit result-button confirmation, so its success is
not established by that counter. Five result-button attempts were withheld when
screen pixels or reader state changed.

The interval from the preceding logged game event to each decision had a maximum
of 1.365 seconds across 38 decisions. This includes polling and policy work; it
is not an isolated policy benchmark or complete click latency measurement.

## Discard lookahead

Eight decisions recorded the completion baseline and selected the same discard.
Thus the lookahead executed in production, but did not change a discard in this
match. The win cannot be attributed to this feature. No policy tuning is justified
by this single match; retain v0.7 and collect further live games to inspect changed
choices, call opportunities and repeated visual delays.
