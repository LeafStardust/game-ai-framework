from __future__ import annotations

"""Bounded leaf valuation for hypothetical unopened Tarot/Spectral outcomes.

D8 booster expectation must not call the opened-pack D9 policy.  D9 owns visible
pack choice and can itself install generation/expectation policies; sending a
hypothetical unopened outcome back through that authority creates an upward policy
edge and can recursively re-enter D8/D9 expectation work.

This evaluator deliberately recognizes only outcome classes that can be valued from
bounded public state without another policy decision:

* deterministic immediate consumables (Hermit, Temperance, Black Hole), and
* deterministic targeted transformations supported by B6's target evaluator.

Generation effects, stochastic effects, Joker creation, copy chains, and any
unsupported target remain literal zero.  That makes unopened booster EV a
conservative lower bound while keeping the expectation layer acyclic.
"""

from copy import deepcopy
from dataclasses import dataclass

from games.balatro.actions import BUY_CONSUMABLE, BalatroAction
from games.balatro.build import ContextualConsumableTargetEvaluator
from games.balatro.consumable import ConsumableContext
from games.balatro.live.consumable_factory import LiveConsumableFactory
from games.balatro.shop_policy import DefaultShopItemValueEstimator


_DETERMINISTIC_IMMEDIATE = frozenset({
    ("TAROT", "The Hermit"),
    ("TAROT", "Temperance"),
    ("SPECTRAL", "Black Hole"),
})

# These effects are intentionally not traversed from unopened expectation.  Several
# of them have perfectly valid *visible* D9 models; that does not make those models
# safe children of D8 expectation.
_DEFERRED_UNOPENED = frozenset({
    ("TAROT", "The Fool"),
    ("TAROT", "The Wheel of Fortune"),
    ("TAROT", "The High Priestess"),
    ("TAROT", "The Emperor"),
    ("TAROT", "Judgement"),
    ("SPECTRAL", "Aura"),
    ("SPECTRAL", "Sigil"),
    ("SPECTRAL", "Hex"),
    ("SPECTRAL", "Ankh"),
    ("SPECTRAL", "The Soul"),
    ("SPECTRAL", "Familiar"),
    ("SPECTRAL", "Grim"),
    ("SPECTRAL", "Incantation"),
    ("SPECTRAL", "Wraith"),
    ("SPECTRAL", "Ouija"),
    ("SPECTRAL", "Ectoplasm"),
    ("SPECTRAL", "Immolate"),
    ("SPECTRAL", "Cryptid"),
})


@dataclass(frozen=True)
class UnopenedConsumableOutcomeValue:
    value: float
    rationale: tuple[str, ...] = ()


class UnopenedConsumableOutcomeValueEvaluator:
    """Value one hypothetical public-pool outcome without entering D9 or SHOP policy."""

    def __init__(
        self,
        *,
        consumable_factory=None,
        item_estimator=None,
        target_evaluator=None,
    ) -> None:
        self.consumable_factory = consumable_factory or LiveConsumableFactory()
        self.item_estimator = item_estimator or DefaultShopItemValueEstimator()
        self.target_evaluator = (
            target_evaluator or ContextualConsumableTargetEvaluator()
        )

    def evaluate(self, state, record: dict, *, kind: str) -> UnopenedConsumableOutcomeValue:
        kind = str(kind or "").upper()
        data = dict(record)
        label = str(data.get("label") or data.get("ability_name") or "")
        key = (kind, label)

        if key in _DEFERRED_UNOPENED:
            return UnopenedConsumableOutcomeValue(
                0.0,
                (f"unopened {kind} outcome {label!r} deferred at D8 boundary",),
            )

        target = self.consumable_factory.create(data)
        if target is None:
            return UnopenedConsumableOutcomeValue(
                0.0,
                (f"unopened {kind} outcome {label!r} unresolved",),
            )

        projected = deepcopy(state)
        projected.phase = "TAROT_PACK" if kind == "TAROT" else "SPECTRAL_PACK"

        if key in _DETERMINISTIC_IMMEDIATE:
            try:
                if not target.can_use(ConsumableContext(state=projected)):
                    return UnopenedConsumableOutcomeValue(
                        0.0,
                        (f"unopened deterministic {label!r} is unusable",),
                    )
                utility, notes = self.item_estimator.estimate(
                    projected,
                    BalatroAction(BUY_CONSUMABLE, target=target),
                )
            except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
                return UnopenedConsumableOutcomeValue(0.0, (f"unopened {label!r} valuation failed closed",))
            return UnopenedConsumableOutcomeValue(
                max(0.0, float(utility)),
                ("bounded deterministic unopened consumable value", *tuple(notes)),
            )

        try:
            target_evaluation = self.target_evaluator.recommend(projected, target)
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            target_evaluation = None
        if target_evaluation is None or float(target_evaluation.total_gain) <= 0.0:
            return UnopenedConsumableOutcomeValue(
                0.0,
                (f"unopened {kind} outcome {label!r} has no positive bounded B6 target",),
            )

        try:
            utility, notes = self.item_estimator.estimate(
                projected,
                BalatroAction(BUY_CONSUMABLE, target=target),
            )
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            return UnopenedConsumableOutcomeValue(0.0, (f"unopened {label!r} valuation failed closed",))

        value = max(0.0, float(utility) + float(target_evaluation.total_gain))
        return UnopenedConsumableOutcomeValue(
            value,
            (
                "bounded deterministic B6 target value",
                f"target gain={float(target_evaluation.total_gain):.3f}",
                *tuple(notes),
                *tuple(target_evaluation.rationale),
            ),
        )
