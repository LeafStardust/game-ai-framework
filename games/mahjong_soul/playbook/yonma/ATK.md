# 4 Player South Wind ATK v0.12

ATK now means **pursue valuable wins and keep pushing through danger**. The old v0.2 conservative push/fold policy did not match this style. Balanced remains separate and unchanged. The registered playbook name is `4 Player South Wind ATK`, intended for four-player South matches (Hanchan). Both the automatic player and suggestion monitor use these settings. Live play verifies the authenticated room format before selecting this playbook.

- `MahjongSoulATK.bat`: capture and automatic native play. Ctrl+C stops both.
- `MahjongSoulMonitor.bat`: capture and read-only ATK recommendations for manual play.

Terminal output remains the recommended action. Detailed planning and call rejection reasons go to the recording/explicit JSON output.

## High-value hand development

The discard ranking weighs projected Han, scored tenpai value, Shanten, available improving copies and the tile changes needed for a target. It plans Yakuhai, Tanyao, Honitsu, Chinitsu, Toitoi and Chiitoitsu routes. Closed targets may include a prospective Riichi; open targets never do. Dora that a target necessarily discards is removed from that target's value. Exposed melds constrain which targets are reachable, and exhausted honor pairs do not promise future Yakuhai.

**Projected Han is a planning estimate, not scored Han or a guaranteed completion.** Exact scoring is still performed only for tenpai hands. No unseen Ura Dora, future Kan Dora, Ippatsu or favorable replacement tile is invented. Dora alone does not provide a Yaku.

The policy prioritizes the fastest actual supported scoring route, then value among those candidates. Closed hands use route-compatible distance and improving tiles as well as open hands. A distant flush or Toitoi target cannot borrow generic one-Shanten speed. At the best actual scoring distance, value choices must retain at least 70% of the best available improving copies (and lose no more than fourteen). Value-only Shanten rebuilding is disabled. The policy does not deliberately step away from Tenpai to chase projected Han.

Open hands without an existing Yaku evaluate the actual shape distance and improving tiles for each supported scoring route. Tanyao excludes terminals and honors; flush routes exclude off-suit tiles; Toitoi counts triplet development; future Yakuhai reserves the needed honor triplet. The policy compares these reachable routes instead of borrowing generic sequence speed for a speculative high-Han target. Discards that destroy the last supported Yaku route receive no productive route credit. These remain heuristics, not a complete search of every Yaku or expected value.

## Calls and Kan

Chi/Pon simulate exact contributions and legal post-call discards, including called/swap discard restrictions. Calls may build a valuable hand as far out as three-Shanten; they no longer require an already secured Yaku or immediate improvement into one-Shanten. A supported open target must require at most four tile changes, project at least three Han and improve progress or develop comparable value. A one-Shanten setback needs at least two extra projected Han and enough wall. The old cheap-Tenpai exception is disabled: the policy does not open merely to secure a one- or two-Han hand. Offered wins are still accepted.

A ready open hand needs an actual legal scoring wait. Opening must not reduce an already scored ready hand's Ron value. Calls from Tenpai must improve value or available winning copies; equal-value calls that only narrow the waits are declined. Exact Red Five identity is retained. Every considered Chi/Pon logs acceptance/rejection reasons, baseline/best Shanten and best projected Han, so repeated Skips can be reviewed.

Kan no longer has an opponent-threat veto. Valuable open Kan can be the first open meld, with a credible Yaku route and at least three projected Han. It still needs at least eight wall tiles, preserved distance, bounded Ukeire loss and no reduction in known tenpai value. Existing Riichi and developed special-hand restrictions remain; ATK does not blindly Kan every quad.

## Full push

Opponent Riichi, multiple threats, low value and dangerous tiles do **not** switch ATK into Fold mode. Danger is still recorded for diagnosis but does not penalize the offensive discard ranking. This intentionally accepts more deal-in risk. Safety checks around mouse delivery, live state and legal actions remain active.

Offered Riichi can be taken with one available winning copy, against up to three threats, and at least four wall tiles. Furiten checks remain. Riichi is not vetoed merely because its point gain is below 25%; an alternative that actually scores less than the best available Dama is still rejected. Offered Ron/Tsumo always take priority; the policy does not refuse a legal win to chase a more valuable future hand.

## Validation and limits

Regressions cover valuable two-Shanten Toitoi Pon through multiple threats, Honitsu/Yakuhai development, high-value rebuilding, route-incompatible Dora, exhausted targets, actual scoring waits, exact contributions and unchanged Balanced behavior. Captured-state replay checks legal proposals and changed behavior; it cannot measure the counterfactual match result or establish stronger play. Opponent probability models, a full expected-value search and placement strategy are still absent.


## South-match priorities and opening Yakuman gate

Four-player ATK prioritizes hand value, then speed. The projected-Han weight is now 20 (previously 14); calls require at least three projected Han. This is a planning estimate, not a promise of final Han. The agent accepts any offered win rather than passing a completed cheap hand. No Riichi-triggered folding or speculative defense is enabled. Opponent concealed tiles are not known, so apparent waits are not treated as proven.

Yakuman pursuit requires at least ten useful matching tiles in either the original hand or the naturally developed current hand. Before this threshold, Yakuman targets contribute no planning value. Reaching it only enables evaluation: the current tiles and melds must still fit at least one complete target whose missing copies remain unseen. Minimum missing draws must fit the conservative remaining own-draw budget (remaining wall divided by player count); opponent calls are not assumed. Missing opening history does not prevent qualification from the current hand. Eligibility is reconsidered on each decision, and never forces rejecting a better normal-hand call. This feasibility check is a necessary-condition heuristic, not a completion probability.

Supported targets are Kokushi, All Honors, All Terminals, All Green, and Nine Gates. Kokushi counts distinct required kinds plus one useful duplicate for its pair; repeated copies cannot inflate the count. Nine Gates counts its required rank multiplicities plus at most one extra suited tile. The other three count tiles compatible with their restricted tile sets. Eligibility does not guarantee completion: compatible shape distance and available improving copies still guide choices. Closed targets reject opening calls and Kan; exposed melds must fit open targets. Other Yakuman are not deliberately pursued by this version, even if encountered; offered wins are always accepted.


## Hand-plan continuity and scored Tenpai

The policy retains a route and its suit for the current hand, including through call offers. A small continuity preference prevents marginal turn-by-turn route changes; a clearly stronger value/progress option can still replace the plan. Plans reset on a new round, repeat counter, capture generation or game connection. They are policy memory and are rebuilt after restarting the process. The detailed recording logs the previous/current plan and whether it started, stayed or switched. Terminal output remains recommended actions only.

At Tenpai, available-copy-weighted Han from actual scored legal waits replaces the speculative target Han in discard/call valuation. A distant flush or Toitoi target cannot inflate a different completed shape. The policy can prefer a higher-value Dama alternative over a lower-value offered Riichi. Known point values remain part of ranking. This does not predict hidden Ura Dora, Ippatsu or opponents' tile probabilities.

Exposed Chi melds can now prove Sanshoku or Ittsu as legal Yaku routes; loose concealed rank presence alone is not treated as proof. Prospective planning still does not cover every Yaku, and the continuity preference is not a full expected-value search. The threshold and feasibility Yakuman gate and always-push behavior remain active.


## Winning-progress correction (v0.8)

Same-Shanten calls must retain at least 70% of the pre-call improving copies, unless they enable legal Ron from a previously Yakuless ready hand. This is a visible-copy progress guard, not a calibrated win probability. The three-Han opening threshold, immediate acceptance of wins, opening Yakuman gate and no-Riichi-fold behavior remain active. Recorded regressions cover the missed Tenpai in East One and the poor same-distance Chi in East Two from session `20261019T102545-112305Z`.


## Complete Yaku scoring and expanded normal patterns (v0.9)

See [the complete Yaku conditions and values](../../YAKU.md). One canonical complete-hand scorer covers all standard Yaku, Yakuman, Fu and payments; the policy no longer carries a separate abbreviated completed-hand rule set. Exact wait scoring and offered-win analysis share that implementation. Captured event history supplies situational Yaku; unavailable history or hidden future bonuses are not assumed.

The development model now reserves required groups and pairs for Pinfu, Iipeikou/Ryanpeikou, Sanshoku sequences/triplets, Ittsu, Chanta/Junchan, Sanankou, Shousangen and Honroutou, in addition to earlier targets. An isolated Dora that cannot fit those groups and the residual pair is removed from target value. This expands structural coverage while retaining actual scoring distance, winning-progress limits, the opening Yakuman gate and no opponent-Riichi fold. Full scoring coverage is not a claim of complete expected-value or all-Yakuman search.


## Decision review (v0.10)

Offered wins remain first. Discards compare reachable scoring routes, progress and improving copies before value ranking; Riichi compares scored waits and Dama alternatives. Detailed recordings now include each discard action, route, distance, improving-copy count, projected Han, scored waits and ranking utility. Existing call rejection reasons and plan transitions remain available. Speculative danger does not change offensive discard rankings; opponent Riichi never triggers folding. These are transparent heuristics, not calibrated expected win values.


## Recorded ready-hand and call correction (v0.11)

At Tenpai, exact scoring supplies all available legal waits, including Riichi waits outside the provisional Yaku plan. Partial-plan replacement costs no longer penalize an already ready hand. This prevents rejecting a valuable ready discard because only its provisional Yaku subset was counted. Furiten still blocks Ron; Tsumo remains possible.

A call cannot qualify solely through a slower expensive route if the post-call policy would choose a faster cheap route. The opening-value requirement is applied at the nearest post-call scoring distance, so a remote flush cannot sell a call that immediately becomes a one-Han hand.

Session `20261019T164058-353717Z` exposed both cases. In South Three, discarding 6 Pin and declaring Riichi has four available winning copies and a known-copy-weighted Ron value of 5,300 points; the old 7 Pin declaration had five copies and 2,600 points. The new choice satisfies the existing 70% progress guard. The subsequent forced Riichi discard caused the recorded deal-in; these counterfactual choices do not prove the revised line wins or avoids a deal-in. In East Two, the agent now skips the Chi previously justified by a slower five-Han Full Flush route. The other two deal-in decisions did not establish a separate rules or progress bug; no hindsight-based folding is added.


## Automatic lobby routing (v0.12)

Authentication metadata is retained per game connection and propagated through snapshots, observations and decision recordings. Player count comes from the authenticated seat list; match length comes from the game mode, never the currently displayed Wind. A South match remains a South match during East rounds. Known standard mode codes are 1 (East) and 2 (South); other codes are reported as unknown rather than guessed. AI status, category, room ID and rule details are recorded without authentication tokens or account data.

The registry selects by player count, style and match length. The policy family now has four-player South ATK and four-player East Speed entries. Three-player, unidentified and recognized unsupported custom rules produce a readable message and no action. Adding another format-specific playbook registers another entry without changing policy routing. Existing generic Balanced books remain available across match lengths. Old offline snapshots without a lobby field retain legacy explicit selection; every live reader snapshot supplies an identified or unknown lobby, so this compatibility path does not bypass live detection. Metadata is refreshed on authentication and is never inherited by another connection. The reader and shared policy serve both the automatic launcher and monitor.

Supported rule handling remains limited to the implemented standard scoring profile. Open Tanyao is consumed by the scorer; Red Dora configuration and other raw settings are recorded. Recognized special modes and incompatible scoring switches are rejected; capturing a field does not mean arbitrary custom rules have been implemented. If capture began after authentication, reconnect or start a fresh room to supply the missing metadata.
