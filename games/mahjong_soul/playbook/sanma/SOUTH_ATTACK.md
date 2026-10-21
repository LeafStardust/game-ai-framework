# Three-Player South Attack v0.1

Priority: **attack, then speed, then defense**. The authenticated three-player
South match (mode 12) selects this book through the existing `atk` policy family.
`MahjongSoulAgent.bat` and the monitor select it automatically; no new launcher.
The current round Wind does not change the selected match-format playbook.

## Decisions

This initial version inherits Four-Player South Attack v0.12's tested value and
winning-progress settings, with at most two opposing Riichi threats. Factories
create independent settings; Three-Player East Speed remains unchanged.

Accept offered Ron/Tsumo first. Build reachable valuable Yaku routes rather than
chase Dora without Yaku. Rank attack value within the shared progress guards:
keep the nearest legal scoring distance, preserve at least 70% of improving
copies, and do not rebuild into a slower speculative expensive hand. Speed breaks
value tradeoffs within those constraints. Actual scored waits replace speculative
Han at Tenpai. These are heuristic priorities, not a complete expected-value solver.

Opening calls normally require at least three projected Han at the nearest
post-call scoring distance and a supported Yaku route. Calls cannot justify a
cheap immediate continuation through a remote expensive route. Sanma offers no
Chi; Pon, legal Kan, Riichi, North extraction and wins use the shared native
executor and recorder. North bonuses count only after a real Yaku exists. Keep
North when extraction would worsen the fastest hand; do not sacrifice a win to
extract. Three-player tiles, Dora cycle and payments use the existing Sanma rules.

Opponent Riichi does not trigger folding: this book inherits `always_push=True`.
Danger is recorded for review; it does not override the value/progress objective
or trigger speculative defense. Furiten still prevents Ron.
Thirteen Orphans Tenpai stays Dama, including narrow waits.

## Yakuman qualification

The shared Yakuman planner requires **at least ten matching hand slots** in the
opening hand or reached naturally later. Duplicate copies cannot substitute for
required distinct Thirteen Orphans kinds. A current qualification also needs
unseen required copies and enough remaining own draws; unavailable copies or an
insufficient wall reject the target. Below the gate, play normal Yaku/value lines,
never steer toward Yakuman merely to reach ten. Existing plan-feasibility checks
apply throughout development. This reuses the existing supported pattern planner;
complete-hand scoring supports more Yakuman than proactive planning does.

## Validation

Regression tests cover automatic South routing even during East rounds, isolated
settings, attack through two Riichi threats, value calls, Yakuman qualification
and late infeasibility, North handling, legal Sanma actions and Kokushi Dama.
The initial book is an adaptation of Four-Player South, not a trained Sanma model.
No live win-rate claim is made. Next validation is a user-started three-player
South AI room with normal recording enabled; no extra calibration is required
solely because the match length changes.
