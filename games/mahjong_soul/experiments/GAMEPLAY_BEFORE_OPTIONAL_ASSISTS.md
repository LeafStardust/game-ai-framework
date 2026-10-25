# Prioritize gameplay over optional assist preparation

The latest three-game review identified a 6.764-second decision-to-input outlier that included both Auto Win and Auto Kita setup between the decision and native delivery. Eleven actions with intervening assist attempts had median latency 3.282 seconds, while the remaining 304 had median 1.370 seconds. The animation-wait preparation path introduced in 12d83fb2 let optional setup consume a pending turn's budget.

Remove that path and its special prepare_automation option. Failed visual preflight now retries gameplay directly. New optional switch enables run only through the existing between-turn path with no pending candidate. The normal pre-action assist reconciliation still allows required disables, and pending uncertain switch outcomes still require confirmation or recovery. Client Auto Win/Discard behavior, read-only assist recovery and fresh gameplay verification remain intact.

A fake-mouse regression simulates an unfinished draw followed by a stable frame. It requires exactly one prepare_optional=False assist reconciliation per poll, no extra setup call on visual failure, and one gameplay delivery when verification succeeds. Existing tests cover required North-protection disables, verified-OFF fallback, automatic unknown-state recovery, and foreground/board guards.

This corrects scheduling, not game animation duration. The live one-to-one-and-a-half-second goal is not yet guaranteed. Initial R/K setup may occur later when the agent starts on its own turn; native legal actions remain available meanwhile. The next user-started three-game batch should measure the tradeoff, especially maximum input delay and first Kita enable time. No agent or game was started for this change.
