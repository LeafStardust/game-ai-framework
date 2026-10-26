# October 26 batch and Kan-only offer fix

The batch on eca299f7 completed all three games and both custom-room restarts. Own results, using the actual seat for each connection: second with 26,100 (four hand wins, two deal-in events), second with 50,000 (two wins, no deal-ins), second with 29,100 (one win, two deal-ins). All 195 submitted gameplay actions were confirmed. One unconfirmed Skip Calls enable recovered after approximately 1.36 seconds. The game limit stopped the worker normally.

Timing was mixed: median 1.398 seconds versus 1.326 previously; 128 of 195 actions (65.6 percent) were within 1.5 seconds versus 57.4 percent previously. Maximum was 3.228 seconds versus 3.363 previously. This is not a controlled codec benchmark and does not isolate encoding effects.

## Actual policy error

An own Riichi draw supplied only operation type 4 (concealed Kan), without a discard operation. The policy entered opponent Chi/Pon evaluation despite neither action being offered. Its Tenpai scorer then tried evaluating a fourteen-effective-tile own-turn hand as a thirteen-effective-tile ready hand and raised a concealed-count exception. That proposal was rejected and never submitted; confirmed-submission totals therefore do not capture this missed decision.

Short-circuit Chi/Pon evaluation when neither is offered. When the sole normalized legal proposal is a server-offered concealed Kan, choose that exact contribution directly rather than ranking nonexistent discard/call options. This honors the available proposal set; it is not a claim that every optional Kan has positive expected value. Other multi-action Kan choices retain existing strategic filters.

The native planner accepts the Kan-only operation list using the same reviewed concealed-Kan button location as the normal discard-plus-Kan layout. It still requires visible Kan-label verification, two distinct stable frames, exact live operation binding and matching own server confirmation. It does not synthesize a discard, inject protocol traffic or weaken label thresholds. Live UI delivery for this exact operation subset still needs validation.

Validation: the saved failed offer now produces the exact offered concealed-Kan proposal instead of throwing. Synthetic policy and fake-mouse controller regressions cover the Kan-only offer, one delivered native action and matching server confirmation. No live agent or game was started, and no private snapshot was published.

Next: restart to load the fix and use the normal three-game batch. Continue checking timing; the remaining engine animations cannot be removed by encoding changes.
