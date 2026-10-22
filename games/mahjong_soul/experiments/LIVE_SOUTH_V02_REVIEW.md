# Three-Player South Attack v0.2: first live review

Session `20261022T043546-483121Z`, October 22, 2026 (Malaysia).
Source revision `951767a3`; authenticated three-player South AI room.
The policy journal records Three-Player South Attack v0.2 throughout.

## Result

First place with 74,400 points. Final scores: 74,400 / -200 / 30,800.
The match ended early during East 3 Honba 1 when an opponent went negative;
it did not change to an East playbook or require reaching South rounds.

| Hand | Outcome for our seat |
| --- | --- |
| East 1 | Won 9 Han, 30 Fu by Tsumo |
| East 1 Honba 1 | Dealt into a 2 Han, 40 Fu Ron; lost 2,800 including Honba |
| East 2 | Won 8 Han, 50 Fu by Ron, worth 16,000 |
| East 3 | Another opponent dealt in; no win or deal-in for us |
| East 3 Honba 1 | Won 5 Han, 30 Fu by Ron, worth 8,000 before Honba/deposits |

Three wins in five hands, one deal-in. High-Han wins match the requested attack
objective, but one AI match cannot establish a strength improvement.

## Completion model exposure

Nine decisions recorded `attack_value_preserving` completion comparisons. Two
changed the old baseline:

- East 2, decision 557: discard 8 Pin instead of 9 Pin; both projected 6 Han,
  two Shanten, fifteen improving copies. Model capped draw cost improved from
  11.8196 to 11.7830. The hand later won 8 Han, but that does not establish that
  the changed discard caused the win or outperforms its counterfactual.
- East 3, decision 997: discard South Wind instead of 6 Sou; both projected
  4 Han, two Shanten, sixteen improving copies. Model cost improved from
  11.8950 to 11.8203. The hand ended in a win by another player.

All shortlisted model estimates in these two decisions were available. The model
probabilities are bounded own-draw forecast quantities, not real-game win odds.
No strategy retuning follows from these two observations alone.

## Execution and latency

All 58 unique controller submissions received confirmation; duplicate journal
submission rows are not extra clicks. No error, blocked action or retry-delivered
rows. One obsolete assist request was safely superseded without halting.

There were 47 visual preflight failures, mostly moving UI, incomplete draw
animations and ambiguous tile/button samples. No waiting-visual expiry row was
recorded. These transient rejections still cost time; this is not flawless vision.
Six result-button clicks were delivered and four explicitly confirmed, so the
journal alone does not establish successful outcomes for the remaining two.

Across 61 decisions, median time from the preceding logged game event to a
recommendation was 0.132 seconds, maximum 0.706 seconds. Across 58 unique submitted
actions, median recommendation-to-submit time was 2.438 seconds, maximum 7.012
seconds. These include polling and UI checks; they are not isolated policy CPU
measurements. The remaining delay is mainly after the recommendation, so this
match does not justify simplifying strategy computation.

Next: retain v0.2 and inspect subsequent South games for repeated recognition
failures, missed calls, deal-ins and additional changed lookahead decisions.
No game process was launched and no gameplay input was sent during this review.
