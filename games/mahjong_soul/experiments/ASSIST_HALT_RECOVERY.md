# Automatic recovery from uncertain sidebar switches

The October 25 run on 12d83fb2 confirmed all 66 submitted gameplay actions, then became indefinitely halted after an unconfirmed Skip Calls enable. The gameplay controller was idle. Later halted screenshots clearly showed every automatic switch OFF, but the follower only attempted recovery for pending gameplay actions and had no assist-state recovery path.

Add a half-second-paced read-only recovery path for failed assist reconciliation. Require two independently captured matching complete switch readings, unchanged layout, foreground geometry, hand, round, connection, Riichi state and Dora, an idle gameplay controller and authenticated AI-room guard. Unknown or moving readings keep being checked automatically without clicking. Once verified, clear the assist failure, discard any stale candidate and resume normal fresh preference reconciliation and gameplay. Existing attempted-gameplay keys remain protected; only an unattempted current board is made eligible for policy reevaluation.

Recovery also handles round/match-ended states through the integrity-checked result snapshot, allowing result navigation and custom-room restarts to resume even while the wire is idle. It does not bypass decode faults, recording failures, foreground requirements or unknown gameplay input delivery. Temporary assist uncertainty now reports waiting_for_assist_recovery instead of instructing the user to restart.

Validation: read-only replay of two matching recorded halted frames recovered all-OFF switch states, with zero input calls. Full suite passed 1001 tests, one skipped; targeted assist/auto tests were rerun after the status wording change. Synthetic tests cover unknown-to-known recovery, changed hands, idle result screens and follower resumption. No live agent was started and no private session fixture was published.

Next: restart the worker once to load the fix, then the user-started three-game batch should recover this failure automatically. Recovery waits for provable current state and does not blindly replay uncertain clicks.
