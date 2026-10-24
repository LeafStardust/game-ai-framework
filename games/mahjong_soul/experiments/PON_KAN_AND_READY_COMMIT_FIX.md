# Fix declined Pon, speculative Kan, delayed Kita and unused D

The latest three-game run completed all matches and both restarts. All 373
submitted gameplay actions received confirmations, but this establishes delivery,
not good decisions. One assist enable stayed OFF and correctly fell back to
native play. Strategy and assist preference failures remained.

## Pon and Kan

A declined Green Dragon Pon would have made an already-open, no-Yaku hand
legally ready on four unseen copies. The three-Han opening floor rejected that
one-Han immediate win route. Add a narrow rescue exception: if the hand is already
open without a secured Yaku and the call produces non-furiten legal Ron Tenpai
on at least three unseen copies, it can secure its winning condition despite
the normal value floor. Closed low-value openings retain the existing floor.

The open Kan converted a terminal triplet while the remaining hand had no
secured open Yaku; its projected value depended on completing an honor pair.
Open Kan now requires no more than one-Shanten before the declaration, plus an
actual retained open Yaku or scored legal ready hand afterward. Do not count a
future Yakuhai pair as that condition. Calculate after-Kan improving draws using
the simulated new board/melds, not the old board. Rejection diagnostics identify
these two reasons. Replay changes the declined Pon to Pon and the bad Kan to
Skip. Synthetic regression hands reproduce the structural failures without
publishing session snapshots.

## Explicit ready-hand commitment

The prior D test tried to prove every future draw had no possible improvement,
which was too restrictive for practical automatic play. South now commits an
open non-furiten ready hand at at least 8,000 weighted Ron points and three live
winning copies. East commits a broad legal ready wait (four copies, at least
1,000 points) unless an opponent Riichi requires reconsidering its defense.
South retains its requested always-push behavior under threats.

This is an explicit goal/strategy choice, not proof that future upgrades are
impossible. Once committed, native policy keeps the ready hand, declines
unneeded calls/Kan and discards nonwinning draws; wins and appropriate North
extraction remain available. Assist preferences use the same condition for C/D.
Do not turn D on before a different selected tile is discarded. Confirmed Auto
Win and Auto Kita when needed remain prerequisites for non-Riichi D.
Two recorded valuable ready-hand cases now request C and D after their first
correct discard; previously neither obtained a useful non-Riichi D commitment.

## R/K setup

Auto Win first-enable attempt median was 1.42 seconds after round start, with
an outlier of 68.15; Auto Kita median was 45.65 seconds, maximum 66.98. A dummy
between-turn discard preference incorrectly marked any singleton North as
essential. Keep North pairs, ready North heads and North-sensitive Yakuman
qualification protected; an ordinary unready singleton no longer starves K.

Opponent steps also cancelled sidebar setup even with unchanged own hand and
switches. Bind setup to active connection/generation/status, round, own hand,
Riichi declarations and Dora context. For C/D, additionally recompute their
preference from the current snapshot before input; don't simply ignore changed
visibility. R/K enables take priority over new C/D enables, while needed disables
still come first. Fresh separate switch frames, geometry, source checks and
record-before-delivery remain. Own hand/round changes still cancel preparation. A new hand retires an old
unconfirmed R/K toggle rather than treating its expired deadline as a fresh failure.

South versions: Three-Player v0.5, Four-Player v0.16. Standard validation remains
three user-started games. No agent was started or native input sent during this
work; no private raw fixtures were added. Live verification is still needed for
actual early R/K enable timing and D delivery after commitment.
