# Ranked input and nine-deal-in audit ? October 28, 2026

## Ranked input

Production native play now allows authenticated ranked matches as well as the existing verified AI rooms. The same MahjongSoulAgent.bat starts capture and the automatic worker; no launcher rename or separate ranked script is required. Ranked selection uses server authGame metadata: supported three/four-player East/South format, match category 2, positive mode ID, no custom-room or contest identity, AI not enabled, no authentication error and no unsupported special rules. Own seat and reader readiness still have to be established normally.

The category mapping is independently documented in [mahjong-helper's primary protocol implementation](https://github.com/EndlessCheng/mahjong-helper/blob/master/majsoul_game_config.go). Local liqi-reference.json defines category, mode, room_id, mode_id and contest_uid; it was not modified.

Verification is scoped to the captured connection and game generation. A state flag alone cannot authorize input. Failed reauthentication revokes eligibility. Client-direction records cannot grant it. Gameplay, assist preparation/recovery and result controls all use the shared game_access predicate. Existing full-hand, two-frame, foreground, freshness, legal-operation and confirmation checks remain active. AI authentication stays separate so a ranked game cannot reach custom-room auto Start.

Automatic book selection remains Three-/Four-Player East Speed or South Attack according to authenticated format. Unsupported/special/unknown rooms are not broadened into a generic online fallback. Ranked matchmaking is manual: start the package, join the match yourself, and leave the game foreground at 1920x1080. The X-games cap counts completed matches; it can wait for subsequent manually joined ranked games. No ranked queue, game, or agent was started during development.

Synthetic tests exercise ranked metadata for all four formats, native fake input, switch/result handling, same-generation binding, missing authentication, wrong category, contest metadata, unknown mode, special rules and auth errors. Live ranked auth/result layouts have not yet been validated; synthetic support is not a claim of ranked playing strength.

## Deal-in audit

Reviewed all nine deal-in events from the prior three-game batch using captured public policy information. Seven occurred while the agent was not locked in Riichi; two occurred after accepted Riichi. The seven unrestricted pushes were five one-Shanten hands, one two-Shanten hand and one three-Shanten hand. The distant hand projected five Han on a Junchan route; projected value is not an already secured winning hand or a measured probability of winning first.

The logged chosen route distance equalled the minimum among the logged discard candidates at all nine preceding decisions. The audit did not establish an unhandled same-cost proven-safe alternative at those deal-in decisions. These checks do not prove the discards, Riichi timing or forecast model optimal. Two accepted-Riichi losses require reviewing the earlier declaration/value/wait decision, rather than inventing a legal alternative discard after the declaration.

The main unresolved strategic limitation is evaluating whether these aggressive hands win the race often enough. Preventing all seven unrestricted push losses by folding would change the user's explicit South always-push preference. This change therefore does not secretly add a defensive policy or use opponents' exposed concealed tiles as strategic information. No additional strategic parameter was tuned from this small sample. The implemented change in this task is ranked eligibility and coverage, while the audit records the actual limits of the current decision model.

Validation: the full suite passed 1,044 tests with one skipped. After final metadata/configuration changes and two added authentication regressions, all 44 focused ranked/lobby/launcher tests passed. Work was confined to the Mahjong worktree; Balatro and liqi-reference.json were untouched.
