# Four-player ATK v0.2

Cartridge: `yonma-manual-atk`, style `atk`, version `0.2`. Configuration is in [atk.py](atk.py). Balanced behavior remains separate.

Run the manual recommendation monitor from the Mahjong worktree:

```powershell
.\MahjongSoulSuggest.bat
```

This selects `--policy playbook --playstyle atk`. Capture must already be running. Restart capture and the monitor after this update so both load the room-rule observation changes. You click the recommended actions yourself. Default terminal output contains only the action, including Man/Pin/Sou and capitalized Wind/Dragon names. `--json` explicitly enables analysis. No mouse execution is part of this launcher.

## Review and changes

| Area | Previous gap | v0.2 behavior |
| --- | --- | --- |
| Value | Dora/honor retention proxy only | Scores tenpai completion scenarios for known han, fu and points, including dealer status, red fives, indicator dora and fixed/closed kan. No hidden ura or assumed ippatsu. |
| Yaku | Only value honors affected opening decisions | Separates scoring routes from bonus tiles. Recognizes retained yakuhai, tanyao, flush and forced triplet routes, with bounded preferences for sanshoku, ittsu, iipeikou, seven pairs and orphans shapes. |
| Calls | Always Skip | Simulates each offered Chi/Pon and its legal follow-up discards. Requires a yaku route and normally a shanten improvement into at most one-shanten; prefers at least two value units, with a cheaper exception for tenpai with at least three legal unseen winning copies. |
| Kan | Always discard/Skip | Considers offered closed/added/open kan without assuming a favorable replacement draw or new dora. Requires sufficient wall, no detected threat, preserved shanten, at most two ukeire lost and no reduction in scored tenpai value. Open kan additionally needs an already open hand with a retained yaku route and at least four value units. |
| Riichi | Structural wait count only | Checks offered closed-hand candidates, post-discard permanent furiten, legal scoring waits and danger. Can retain high-value dama when Riichi adds little scored value. |
| Defense | Genbutsu only; no fallback danger ordering | Ranks every discard against each threat, including cautious suji/kabe/honor visibility factors. Folding minimizes the worst opponent danger before summed danger. Three exposed melds with visible value can also count as a threat. |

## Value and efficiency

Normally keep the best shanten and consider at most six fewer unseen improving copies for value. The ranking includes known bonus loss, value-honor pair/triplet loss, breaking developed seven-pairs shapes, bounded yaku-shape preference and scored tenpai value. These are configurable trade-offs. The exception to preserving structural shanten is an entirely exhausted tenpai: the policy may rebuild a productive one-shanten hand instead of waiting on zero unseen copies.

Only tenpai hands receive complete hand-calculator scoring. Earlier-hand routes and shape preferences are estimates, not guaranteed final han or expected value. The existing pinned [MahjongRepository calculator](https://github.com/MahjongRepository/mahjong) handles completion scoring. Ordinary scoring assumes the standard red-five tile set; custom variants are not comprehensively modeled.

Open Tanyao is enabled only when captured `GameDetailRule.shiduan` confirms it. A missing rule stays unknown and does not justify a Tanyao opening. Dora alone never establishes a yaku. Calls preserve exact red contributions, avoid called/swap discards, protect developed closed special hands and reject furiten/no-yaku tenpai. A same-shanten opening is allowed when it turns a yakuless closed tenpai into a legal Ron worth at least 2,000 points with at least three unseen winning copies. The next monitor recommendation is recomputed from the actual post-call server offer.

## Push, fold and Riichi

A push normally requires one threat, a sufficiently valuable near-ready hand, enough wall, a retained scoring route for open hands and a relative danger at most 75. Two-shanten pushes additionally need at least four value units, twenty improving copies and twenty-four wall tiles. Developed yaku shapes and a closed hand's prospective Riichi can contribute to this early value estimate; no future Riichi point gain is treated as an already scored win.

Multiple threats, weak hands, exhausted/furiten Ron waits and excessive danger favor folding. Suji and kabe only reduce relative danger: they do not prove a tile safe. These scores are rankings, not deal-in probabilities. Full placement strategy, calibrated opponent models and expected-value search remain gaps.

Riichi normally needs two unseen winning copies, or six against a threat, at least eight wall tiles, and known non-furiten state. It can prefer dama with at least 7,700 known Ron points, four legal unseen copies and less than 25% scored gain from Riichi. Server offers remain the legal action authority. Offered wins take priority.

All ukeire and wait counts refer to copies not accounted for in visible information, including tiles that may be held by opponents. They are not a count of tiles known to remain in the live wall. Furiten checks include structural waits already exhausted in visible information.

## Validation

Real-hand regressions cover legal and yakuless openings, room-rule-dependent Tanyao, exact red calls, kuikae, kan efficiency, scoring, reported/permanent furiten, exhausted waits, dama/Riichi and multiple threats. The default CLI is tested to print only the recommendation.

Two recorded captures validate all 295 proposed decisions with zero policy/validation failures. The 164-board capture proposes 118 discards, 38 Skips, four Riichi, two Ron, one Tsumo and one closed kan. The other 131 boards propose 106 discards, 20 Skips and five Ron. Maximum measured decision latency was 108 ms. Separate real-hand tests exercise positive Chi/Pon choices. Replay follows the human's recorded trajectory; it does not measure counterfactual win rate or establish optimal play.

The next step is manual ATK testing and review of surprising recommendations. Automatic input development is deferred; the current native runner does not yet execute every newly recommended call.
