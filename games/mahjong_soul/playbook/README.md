# Mahjong Soul strategy playbooks

The four-player [ATK v0.3 strategy](yonma/ATK.md) describes the current high-value, always-push policy. Use `.\MahjongSoulSuggest.bat` for recommended-action-only output.

These are executable, versioned strategy settings, following Balatro's cartridge/registry approach. Shared Mahjong facts, server-offer validation and shanten calculations stay outside the cartridges. The policy reads thresholds from the selected playbook; editing this Markdown does not change behavior.

| Playbook | Selection | Version | Use |
| --- | --- | --- | --- |
| `yonma-manual-balanced` | Four players | `0.1` | Manual suggestion tests |
| `sanma-manual-balanced` | Three players, balanced | `0.1` | Manual suggestion tests, with sanma tile-pool handling |
| [`yonma-manual-atk`](yonma/ATK.md) | Four players, atk | `0.3` | High-Han route planning, earlier value calls and full pushes |

The two balanced cartridges start with the same conservative thresholds; separate entries allow later evidence-based tuning. The four-player attack cartridge has distinct offensive settings. They are not tuned for particular ranks, room rules or match lengths. Selection uses (player count, playstyle) and rejects unregistered pairs; there is no implicit attack-to-balanced fallback. Balanced remains the default.

## Modules

- `model.py`: MahjongPlaybook, registry, stable layer IDs and default cartridges.
- `features.py`: shared dora cycles, seat/round value honors, yakuhai evidence and opponent-specific discarded-tile safety.
- `agents/mahjong_soul/playbook_policy.py`: consumes those features/settings and returns one offered action. No native input is imported or sent.

ATK-specific evaluation lives in `agents/mahjong_soul/attack_policy.py`, `attack_value.py`, `attack_routes.py` and `attack_defense.py`. These choose suggestions without importing native input.

## Balanced decision layers

| ID | Settings | Initial behavior |
| --- | --- | --- |
| D1: discard value | Dora loss weight `1.0`, value-honor pair loss `0.5`, triplet loss `2.0` | Tie-break equal shanten/ukeire choices to preserve bonus tiles and valuable honor shapes. These are heuristic weights, not han or point estimates. |
| D2: defense | Fold from best shanten `2` | Against declared/accepted opponent Riichi, if at least one offered discard has known safety evidence, prefer the tile safe against the most threats, then efficiency/value. With no such evidence, retain efficiency ranking. |
| D3: Riichi | Enabled; allow under opponent Riichi threat `false` | Accept offered Riichi with the best ranked offered tenpai discard when no threat is present. Otherwise stay undeclared. |

For the balanced cartridges, offered wins take priority and Chi/Pon/kan still decline through Skip. ATK v0.3 has its own high-value opening policy and never switches into defensive Fold mode. Near-ready hands below the fold threshold retain efficiency priority, with safety then value as tie-breaks. Opponent discarded tiles are treated as genbutsu only against that opponent; a tile safe against one player is not claimed safe against everyone. Red and ordinary fives share safety identity, while their value differs.

Value honors use the dealer-relative seat wind and round wind, including double winds. Existing/preserved value-honor triplets are evidence of a possible scoring route; they do not certify the complete hand's yaku. The policy does not yet calculate full han/fu, score expected value, placement strategy, furiten-adjusted waits, suji/kabe risk, non-Riichi open-hand threats or unknown opponent hands. Dora are bonus value, not a yaku. Open tanyao and other room-rule-dependent yaku are not assumed.

Shared rule reference for discarded-tile furiten and dora cycles: [World Riichi Championship rules, sections 8.11.2 and 8.13](https://www.worldriichi.org/s/WRC_Rules_2022_20220708_site.pdf). This supports those general features, not a claim that Mahjong Soul uses every tournament rule. Server offers remain authoritative for action legality; sanma's reduced Man pool is handled separately.

## Run manually

```powershell
.\.venv\Scripts\python.exe -u -m agents.mahjong_soul.shadow --policy playbook
```

This prints only readable recommended actions by default. You perform them manually. Use `--json` for playbook name/version, fold/efficiency mode and selected candidate evidence; use `--policy efficiency` to compare against the earlier pure-efficiency policy. Add `--playstyle atk` for the four-player attack cartridge. No three-player attack cartridge exists yet. The CLI default policy is `playbook` and style is `balanced`, but an already running process or an explicit `--policy efficiency` command does not switch by itself.

## Validation and tuning

Tests cover registry selection/isolation, custom threshold effects, dora/wind cycles, double winds, opponent-specific genbutsu, red-five normalization, multi-opponent threats, fold boundaries, absence of safety evidence, Riichi threat settings, and win priority.

Replay of the completed ten-round capture validated all 164 proposals: 120 ordinary discards, 38 Skips, three Riichi, two Ron and one Tsumo. Ten recommendations differed from EfficiencyPolicy; five discard decisions used fold mode. Peak measured decision time was 47.76 ms on that replay. This is a historical-trajectory legality/behavior check, not a simulation or strength estimate. Settings remain initial manual-test hypotheses.

For each manual test, record the round/action where a recommendation looks wrong, the competing action and visible reasoning. Reproduce it offline before changing a threshold, add a targeted regression, replay prior captures, then increment the cartridge version when its strategy behavior changes. No extra screenshots or game setup are required merely to create or edit these playbooks.
