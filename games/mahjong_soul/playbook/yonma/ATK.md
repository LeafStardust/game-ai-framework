# Four-player attack playbook

Cartridge: `yonma-manual-atk`, style `atk`, version `0.1`.
Configuration: [atk.py](atk.py). Shared decision logic remains in `agents/mahjong_soul/playbook_policy.py`.

Attack means pursuing worthwhile offensive opportunities: preserve value, push selectively and use good Riichi opportunities. This initial cartridge expresses that bias through observable evidence and explicit limits. Thresholds are manual-test hypotheses, not an expected-value or trained risk model.

## Discards and value

The cartridge never increases shanten for offensive value. Within the best shanten it considers discards up to six ukeire copies below the best available count, then balances ukeire against the value discarded. The initial conversion is two ukeire copies per weighted value-loss unit. Dora loss weight is 2.0, value-honor pair loss 1.25 and value-honor triplet loss 4.0. Red fives count as bonus value, including red-plus-indicator dora. This lets attack keep a valuable tile at a bounded speed cost while avoiding a whole extra shanten detour.

These weights are policy trade-offs, not point or han estimates. Complete hand scoring, placement considerations, flush planning and guaranteed-yaku evaluation remain future work.

## Push and fold

Normally use the balanced two-shanten fold boundary when known discarded-tile safety is available. A selective push exception requires all of:

- Exactly one declared/accepted opponent Riichi.
- Best shanten at most two.
- At least three units of retained bonus/value-honor-triplet evidence in the selected offensive candidate.
- At least twelve tiles reported left in the wall.
- For an open hand, a retained value-honor triplet/kan as a known scoring route. Closed hands can pursue Riichi later.

Against multiple Riichi threats, do not grant that value-push exception. Near-ready hands retain offensive ranking; farther hands use the available genbutsu evidence. If no offered tile has known safety evidence, the policy cannot invent a safe discard and retains its offensive ranking. Safety is always opponent-specific.

## Riichi

Take offered wins first. Otherwise Riichi remains restricted to server-offered, zero-shanten discard candidates. Attack requires at least two unseen improving copies normally, and six when countering one opponent Riichi. It declines new Riichi when there are two or more threats, fewer than eight tiles left, or own furiten is true/unknown. The chosen offered discard uses the same bounded value/ukeire ranking.

Current ukeire counts unseen structural improvements, not guaranteed live-wall tiles. These Riichi thresholds therefore do not constitute a point-value or deal-in probability calculation.

## Scope and manual test

This first attack cartridge covers discard value, push/fold and Riichi. Chi/Pon/kan selection still declines through Skip; a yaku-aware opening/call layer is not implemented. It does not enable mouse input. Three-player attack is not registered and fails explicitly instead of falling back to four-player settings. Balanced remains the default style.

```powershell
.\.venv\Scripts\python.exe -u -m agents.mahjong_soul.shadow --policy playbook --playstyle atk
```

Use `--json` only to inspect playbook/style and candidate analysis. Default output remains the recommended action only.

## Evidence

The full Mahjong test suite passes 378 tests, including attack-specific checks for style selection, bounded value sacrifice, no offensive shanten increase, retained-yaku route requirements, selective pushes, multiple threats, late-wall limits, furiten and counter-Riichi. Replaying the recorded ten-round four-player match validates all 164 proposed actions: 119 discards, 38 skips, four Riichi, two Ron and one Tsumo; zero policy or validation errors. Balanced proposes three Riichi on that trajectory. This verifies interface legality and intended behavior, not stronger actual results or counterfactual match outcomes.

Next manual test: compare recommendations with balanced when an expensive discard, an opponent Riichi or your own Riichi opportunity appears. Save the round/step of surprising advice for offline reproduction. No automated game interaction is needed.
