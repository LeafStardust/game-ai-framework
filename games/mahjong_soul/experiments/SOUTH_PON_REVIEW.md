# Opening South Wind Pon versus Skip

## Intervention

The prior offense audit identified a non-value South Wind Pon in seed 80, candidate seat 2. It kept the projected legal route at three-Shanten while increasing the immediate improving-copy proxy from 21 to 40. The hand still needed its West Wind pair to become Yakuhai. This review tests that exact choice rather than assuming that opening without an already secured Yaku was wrong.

The new offline `agents.mahjong_soul.call_counterfactual` tool first runs the normal policy and captures the selected call's public board token. It reruns the same seed, seat, policies and opponent profile. Only at the matching token does it pass the legal Skip to the policy, before the policy can remember a hypothetical post-Pon route. Every later decision uses the normal policy. Both branches may take subsequent calls; Skip does not force a permanently closed hand. Indeed, both branches later Pon West Wind in this hand.

The tool requires exactly one matching intervention, checks identical starting deals, and requires the first replay divergence to be the candidate's Pon. Wins are never suppressed. Native actions still bind to the engine's original legal action list. Missing targets, repeated targets, unavailable Skip, changed deals and unrelated earlier divergence fail the comparison. Tests include the absence of a phantom hand plan after Skip.

## Results

[Comparison data](south_pon_counterfactual.json) includes source hashes and the intervention. Complete fictional MJAI replays remain in local `logs/mahjong_soul/experiments/south-pon-counterfactual*`. RiichiEnv 0.4.10 uses the same Mahjong Soul default rules as the existing harness.

| Opponents | Choice | First-hand outcome | Match wins | Deal-in hands | Final score | Placement |
| --- | --- | --- | --- | --- | --- | --- |
| Call-capable | Pon | Opponent Tsumo; -8,000 | 0 | 1 | 15,000 | Third |
| Call-capable | Skip | Deal-in; -8,000 | 0 | 2 | 17,800 | Third |
| Aggressive | Pon | Opponent Tsumo; -8,000 | 0 | 1 | 7,600 | Third |
| Aggressive | Skip | Deal-in; -8,000 | 0 | 2 | 20,600 | Third |

All four full matches completed. The targeted first hand ends without a self win in every branch. Neither branch declares its own Riichi in that hand, so the -8,000 settlement is also the candidate's hand score loss. Skip changes later draws and game length: caller Pon plays four hands versus three for Skip; aggressive Pon also plays four versus three for Skip. Match-wide scores and deal-in counts therefore describe entire diverged trajectories, not isolated effects on equivalent later hands.

Skipping the initial Pon gives more final points in this fixed deal, but does not recover a win or improve placement and produces an additional deal-in hand. This is mixed evidence, not proof that Pon is optimal or that Skip is a stronger general strategy. Both opponent profiles share the same seed and opening deal; these are not two independent starting-hand samples. The counterfactual uses the actual fixed hidden wall only through the engine; neither policy receives it.

## Decision

Do not change the live call policy from this probe. There is no demonstrated winning benefit to banning this opening. More than one distinct call opportunity is required before adopting a rule about opening before securing Yaku. All 803 Mahjong tests passed. No live agent, capture, native input or terminal formatting changed.

Run another exact-call probe with a new output directory:

```powershell
$env:PYTHONPATH = 'logs/mahjong_soul/simulator-deps'
.\.venv\Scripts\python.exe -m agents.mahjong_soul.call_counterfactual --seed 80 --seat 2 --called-tile 2z --opponents callers --output logs/mahjong_soul/experiments/new-call-probe
```

`--occurrence` selects the nth Pon of that exact called-tile label that the baseline policy chooses. It does not use hand value or future outcomes to select an intervention. Existing output paths are refused.

Next: apply the same one-action comparison to distinct non-value opening calls, focusing on whether the extra improving copies compensate for reliance on a future Yaku tile. No game launch is needed.
