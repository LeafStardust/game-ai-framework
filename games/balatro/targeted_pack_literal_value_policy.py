from __future__ import annotations

"""Make opened-pack targeted consumables compete on their actual target value.

D9 runs after the booster purchase is already sunk.  The historical shared pack
path nevertheless added ``DefaultShopItemValueEstimator``'s generic consumable
category value (for example the Tarot fallback) to D10/B6's concrete target value.
That shop-oriented base is not an effect of choosing the visible card and can make
an otherwise neutral transformation beat Skip.

For deterministic targeted Tarot/Spectral choices, D10/B6 already owns legality,
contextual/intrinsic target value, overwrite cost, and other modeled opportunity
costs.  Use that value directly.  Stochastic modeled effects such as Aura keep their
own dedicated expectation paths and are not altered here.
"""

from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.build import ContextualConsumableTargetEvaluator


_TARGETED_TAROTS = ContextualConsumableTargetEvaluator.SUPPORTED_TAROTS
_TARGETED_SPECTRALS = ContextualConsumableTargetEvaluator.SUPPORTED_SPECTRALS


def install_targeted_pack_literal_value_policy() -> None:
    if getattr(BalatroPackPolicy, "_targeted_pack_literal_value_installed", False):
        return

    original_score_consumable = BalatroPackPolicy._score_consumable

    def score_consumable(self, state, action, choice):
        is_targeted = (
            choice.kind == "TAROT" and choice.label in _TARGETED_TAROTS
        ) or (
            choice.kind == "SPECTRAL" and choice.label in _TARGETED_SPECTRALS
        )
        if not is_targeted:
            return original_score_consumable(self, state, action, choice)

        target = self.consumable_factory.create(choice.data, live_id=choice.live_id)
        if target is None:
            return PackActionScore(action, -1.0, ("unresolved targeted consumable",))

        target_evaluation = self.consumable_target_evaluator.recommend(state, target)
        if target_evaluation is None or target_evaluation.total_gain <= 0.0:
            return PackActionScore(
                action,
                -1.0,
                (
                    f"{choice.kind.title()} has no positive admitted D10/B6 target",
                    "opened-pack choice receives no generic shop/category utility",
                ),
            )

        targeted_action = type(action)(
            action.name,
            cards=list(target_evaluation.cards),
            target=choice,
        )
        return PackActionScore(
            targeted_action,
            float(target_evaluation.total_gain),
            (
                "opened-pack deterministic target uses literal D10/B6 value only",
                "booster purchase cost is already sunk; no generic shop/category value is added",
                f"D10/B6 target gain={target_evaluation.total_gain:.3f}",
                f"target_indices={target_evaluation.target_indices}",
                *target_evaluation.rationale,
            ),
        )

    BalatroPackPolicy._score_consumable = score_consumable
    BalatroPackPolicy._targeted_pack_literal_value_installed = True
