# Mahjong Soul Playbooks

Playbooks contain versioned strategy settings. Shared scoring, legal-action validation and input execution stay outside them. The authenticated lobby selects the match format; the launcher selects the policy family.

| Playbook | Module | Documentation | Version |
| --- | --- | --- | --- |
| Four-Player South Attack | `yonma/south_attack.py` | [South Attack](yonma/SOUTH_ATTACK.md) | 0.12 |
| Four-Player East Speed | `yonma/east_speed.py` | [East Speed](yonma/EAST_SPEED.md) | 0.1 |
| Four-Player Balanced | `model.py` | Generic baseline settings | 0.1 |
| Three-Player Balanced | `model.py` | Generic baseline settings | 0.1 |

## Naming conventions

Display names use `<Player Count>-Player [Match Length] <Strategy>`, spelling out Three or Four. East and South describe match length rather than the current round Wind. Generic Balanced entries omit match length because their settings cover both formats. Display names omit version numbers; the version is a separate field.

Python modules and functions use descriptive `snake_case`: `south_attack.py`, `south_attack_playbook()`, `east_speed.py`, `east_speed_playbook()`. Playbook documents use matching uppercase names: `SOUTH_ATTACK.md`, `EAST_SPEED.md`. The existing `yonma` directory means four-player Mahjong; `mahjong_soul` remains the package name. Existing shared modules keep their descriptive names.

Windows launchers consistently use the `MahjongSoul` prefix and PascalCase role, such as `MahjongSoulAgent.bat`, `MahjongSoulMonitor.bat`, `MahjongSoulCapture.bat` and `MahjongSoulSetup.bat`. The agent launcher stays generic because it selects the playbook from the lobby. The existing `--playstyle atk` policy-family flag remains compatible: it routes to South Attack or East Speed. `--playstyle balanced` selects the generic Balanced entries. Log field names remain stable; recorded historical names are not rewritten.

## Running

- `MahjongSoulAgent.bat`: capture, recording and automatic play with lobby selection.
- `MahjongSoulMonitor.bat`: capture and readable recommendations without automatic input.
- `MahjongSoulSuggest.bat`: compatibility alias for the monitor launcher.

Normal terminal output is the recommended action. Unsupported or unidentified formats report the issue and send no input. Three-player Attack/Speed playbooks have not been implemented.

## Implementation and validation

`model.py` defines the registry and generic Balanced settings. `features.py` provides shared visible-board features. `agents/mahjong_soul/playbook_policy.py` selects the policy; `attack_policy.py`, `attack_routes.py`, `attack_value.py` and `attack_defense.py` implement the shared South/East decision pipeline. Exact complete-hand scoring lives in `scoring.py`.

Tests cover format routing, settings isolation, legal calls, waits, scoring, speed/value priorities and defensive behavior. Offline replay validates proposals on recorded boards; it does not establish a win rate or counterfactual match result. See each playbook document for current behavior and limitations.
