from __future__ import annotations

"""Bounded leaf valuation for hypothetical unopened Tarot/Spectral outcomes.

This layer is intentionally acyclic: hypothetical unopened outcomes never enter D9,
D11, D14, Build Health, or whole-policy decision code. Only deterministic public
mechanics and bounded B6 target value are admitted; stochastic/generative outcomes
remain literal zero until visible.
"""

from copy import deepcopy
from dataclasses import dataclass

from games.balatro.build import ContextualConsumableTargetEvaluator
from games.balatro.live.consumable_factory import LiveConsumableFactory


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
    """Value one hypothetical public-pool outcome without entering policy authority."""

    def __init__(self, *, consumable_factory=None, target_evaluator=None) -> None:
        self.consumable_factory = consumable_factory or LiveConsumableFactory()
        self.target_evaluator = target_evaluator or ContextualConsumableTargetEvaluator()

    @staticmethod
    def _deterministic_immediate_value(state, kind: str, label: str):
        if kind == "TAROT" and label == "The Hermit":
            gain = min(max(0, int(getattr(state, "money", 0) or 0)), 20)
            return 2.2 + min(5.0, gain * 0.35), (f"Hermit deterministic money gain={gain}",)
        if kind == "TAROT" and label == "Temperance":
            joker_sell_value = sum(
                max(0, int(getattr(joker, "sell_value", 0) or 0))
                for joker in tuple(getattr(state, "jokers", ()) or ())
            )
            gain = min(joker_sell_value, 50)
            return 2.2 + min(5.0, gain * 0.35), (
                f"Temperance deterministic money gain={gain}",
                f"public Joker sell value={joker_sell_value}",
            )
        if kind == "SPECTRAL" and label == "Black Hole":
            return 4.0, ("Black Hole bounded public Spectral base value=4.000",)
        return None

    def evaluate(self, state, record: dict, *, kind: str) -> UnopenedConsumableOutcomeValue:
        kind = str(kind or "").upper()
        data = dict(record)
        label = str(data.get("label") or data.get("ability_name") or "")
        key = (kind, label)

        if key in _DEFERRED_UNOPENED:
            return UnopenedConsumableOutcomeValue(
                0.0,
                (f"unopened {kind} outcome {label!r} deferred at expectation boundary",),
            )

        immediate = self._deterministic_immediate_value(state, kind, label)
        if immediate is not None:
            value, notes = immediate
            return UnopenedConsumableOutcomeValue(
                max(0.0, float(value)),
                ("bounded deterministic unopened consumable value", *notes),
            )

        target = self.consumable_factory.create(data)
        if target is None:
            return UnopenedConsumableOutcomeValue(
                0.0,
                (f"unopened {kind} outcome {label!r} unresolved",),
            )

        projected = deepcopy(state)
        projected.phase = "TAROT_PACK" if kind == "TAROT" else "SPECTRAL_PACK"
        try:
            target_evaluation = self.target_evaluator.recommend(projected, target)
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            target_evaluation = None
        if target_evaluation is None or float(target_evaluation.total_gain) <= 0.0:
            return UnopenedConsumableOutcomeValue(
                0.0,
                (f"unopened {kind} outcome {label!r} has no positive bounded B6 target",),
            )

        value = max(0.0, 3.2 + float(target_evaluation.total_gain))
        return UnopenedConsumableOutcomeValue(
            value,
            (
                "bounded deterministic B6 target value",
                f"target gain={float(target_evaluation.total_gain):.3f}",
                *tuple(target_evaluation.rationale),
            ),
        )
