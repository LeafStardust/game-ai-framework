# Four-player ATK v0.5

ATK now means **pursue valuable wins and keep pushing through danger**. The old v0.2 conservative push/fold policy did not match this style. Balanced remains separate and unchanged. The registered cartridge name remains `yonma-manual-atk` for compatibility; both the automatic player and suggestion monitor use these settings.

- `MahjongSoulAgent.bat`: capture and automatic native play. Ctrl+C stops both.
- `MahjongSoulMonitor.bat`: capture and read-only ATK recommendations for manual play.

Terminal output remains the recommended action. Detailed planning and call rejection reasons go to the recording/explicit JSON output.

## High-value hand development

The discard ranking weighs projected Han, scored tenpai value, Shanten, available improving copies and the tile changes needed for a target. It plans Yakuhai, Tanyao, Honitsu, Chinitsu, Toitoi and Chiitoitsu routes. Closed targets may include a prospective Riichi; open targets never do. Dora that a target necessarily discards is removed from that target's value. Exposed melds constrain which targets are reachable, and exhausted honor pairs do not promise future Yakuhai.

**Projected Han is a planning estimate, not scored Han or a guaranteed completion.** Exact scoring is still performed only for tenpai hands. No unseen Ura Dora, future Kan Dora, Ippatsu or favorable replacement tile is invented. Dora alone does not provide a Yaku.

At the best available Shanten, the policy can sacrifice up to fourteen improving copies to preserve/build value. With at least twenty-four wall tiles, it can accept one additional Shanten for at least two extra projected Han, provided the alternative still has improving copies. It does not choose an exhausted target over a productive alternative just for its advertised value.

Open hands without an existing Yaku evaluate the actual shape distance and improving tiles for each supported scoring route. Tanyao excludes terminals and honors; flush routes exclude off-suit tiles; Toitoi counts triplet development; future Yakuhai reserves the needed honor triplet. The policy compares these reachable routes instead of borrowing generic sequence speed for a speculative high-Han target. Discards that destroy the last supported Yaku route receive no productive route credit. These remain heuristics, not a complete search of every Yaku or expected value.

## Calls and Kan

Chi/Pon simulate exact contributions and legal post-call discards, including called/swap discard restrictions. Calls may build a valuable hand as far out as three-Shanten; they no longer require an already secured Yaku or immediate improvement into one-Shanten. A supported open target must require at most four tile changes, normally project at least two Han and improve progress or develop comparable value. A one-Shanten setback needs at least two extra projected Han and enough wall. A cheap legal tenpai with at least three available Ron copies remains an exception: ATK still takes practical routes to wins.

A ready open hand needs an actual legal scoring wait. Opening must not reduce an already scored ready hand's Ron value. Calls from Tenpai must improve value or available winning copies; equal-value calls that only narrow the waits are declined. Exact Red Five identity is retained. Every considered Chi/Pon logs acceptance/rejection reasons, baseline/best Shanten and best projected Han, so repeated Skips can be reviewed.

Kan no longer has an opponent-threat veto. Valuable open Kan can be the first open meld, with a credible Yaku route and at least three projected Han. It still needs at least eight wall tiles, preserved distance, bounded Ukeire loss and no reduction in known tenpai value. Existing Riichi and developed special-hand restrictions remain; ATK does not blindly Kan every quad.

## Full push

Opponent Riichi, multiple threats, low value and dangerous tiles do **not** switch ATK into Fold mode. Danger is still recorded for diagnosis but does not penalize the offensive discard ranking. This intentionally accepts more deal-in risk. Safety checks around mouse delivery, live state and legal actions remain active.

Offered Riichi can be taken with one available winning copy, against up to three threats, and at least four wall tiles. Furiten checks remain. Riichi is not vetoed merely because its point gain is below 25%; an alternative that actually scores less than the best available Dama is still rejected. Offered Ron/Tsumo always take priority; the policy does not refuse a legal win to chase a more valuable future hand.

## Validation and limits

Regressions cover valuable two-Shanten Toitoi Pon through multiple threats, Honitsu/Yakuhai development, high-value rebuilding, route-incompatible Dora, exhausted targets, actual scoring waits, exact contributions and unchanged Balanced behavior. Captured-state replay checks legal proposals and changed behavior; it cannot measure the counterfactual match result or establish stronger play. Opponent probability models, a full expected-value search and placement strategy are still absent.
