from __future__ import annotations

"""Literal score value of permanently adding playing cards to the deck.

Blue Joker and Hologram both reward card additions, but not with a generic shared
bonus. Blue Joker reads the actual number of cards remaining in ``state.deck`` and
therefore gains exactly +2 Chips per added card at an equivalent scoring state.
Hologram receives a CARDS_ADDED event and gains +0.25 XMult per added card.

This evaluator applies those exact public mechanics on a copied state and measures
the before/after representative whole-build score using the same relative direct-
score normalization as D2. It does not inspect future draw order or sample RNG.
"""

import copy

from games.balatro.card import BalatroCard
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.build.literal_score_expectation import literal_expected_score
from games.balatro.jokers.blue_joker import BlueJoker
from games.balatro.jokers.hologram import HologramJoker


def _token(joker: object) -> str:
    for value in (
        getattr(joker, "name", None),
        getattr(joker, "label", None),
        getattr(joker, "ability_name", None),
        type(joker).__name__,
    ):
        token = "".join(ch for ch in str(value or "").lower() if ch.isalnum())
        if token:
            return token
    return ""


def _growth_kind(joker: object) -> str | None:
    token = _token(joker)
    if token in {"bluejoker", "bluejokerjoker"}:
        return "BLUE"
    if token in {"hologram", "hologramjoker"}:
        return "HOLOGRAM"
    return None


def _materialize_growth_jokers(state) -> None:
    """Give public/fallback Joker records their exact executable score mechanic.

    Normal production states already contain concrete Joker classes.  Some public
    projections and deterministic fixtures intentionally carry only an authoritative
    Joker name plus public state.  Materialize only the two mechanics owned by this
    evaluator so literal score comparison does not depend on Python class identity.
    """
    materialized = []
    for joker in tuple(getattr(state, "jokers", ()) or ()):
        kind = _growth_kind(joker)
        if kind == "BLUE" and not isinstance(joker, BlueJoker):
            replacement = BlueJoker()
            replacement.debuffed = bool(getattr(joker, "debuffed", False))
            materialized.append(replacement)
            continue
        if kind == "HOLOGRAM" and not isinstance(joker, HologramJoker):
            replacement = HologramJoker()
            replacement.x_mult = float(getattr(joker, "x_mult", 1.0) or 1.0)
            replacement.debuffed = bool(getattr(joker, "debuffed", False))
            materialized.append(replacement)
            continue
        materialized.append(joker)
    state.jokers = materialized


class DeckGrowthScoreValueEvaluator:
    def __init__(self, *, joker_evaluator: JokerBuildValueEvaluator | None = None) -> None:
        self.joker_evaluator = joker_evaluator or JokerBuildValueEvaluator()

    @staticmethod
    def _active_growth_jokers(state) -> tuple[object, ...]:
        return tuple(
            joker
            for joker in tuple(getattr(state, "jokers", ()) or ())
            if _growth_kind(joker) is not None
            and not bool(getattr(joker, "debuffed", False))
        )

    def evaluate(self, state, *, added_count: int = 1) -> tuple[float, tuple[str, ...]]:
        count = max(0, int(added_count))
        active = self._active_growth_jokers(state)
        if count <= 0 or not active:
            return 0.0, ("no active Blue Joker/Hologram deck-growth scorer",)

        before_state = copy.deepcopy(state)
        after_state = copy.deepcopy(state)
        _materialize_growth_jokers(before_state)
        _materialize_growth_jokers(after_state)

        dummy_cards = [BalatroCard("2", "Hearts") for _ in range(count)]
        after_state.deck = [*list(getattr(after_state, "deck", ()) or ()), *dummy_cards]
        if getattr(after_state, "owned_deck", None) is not None:
            after_state.owned_deck = [
                *list(after_state.owned_deck or ()),
                *copy.deepcopy(dummy_cards),
            ]

        hologram_growth = 0
        for joker in tuple(getattr(after_state, "jokers", ()) or ()):
            if _growth_kind(joker) != "HOLOGRAM" or bool(getattr(joker, "debuffed", False)):
                continue
            joker.x_mult = float(getattr(joker, "x_mult", 1.0) or 1.0) + 0.25 * count
            hologram_growth += 1

        weighted_gain = 0.0
        total_weight = 0.0
        observed = self.joker_evaluator._probe_weights(state)
        for hand, template_cards in self.joker_evaluator._scoring_probes(state):
            cards = copy.deepcopy(list(template_cards))
            try:
                before = literal_expected_score(
                    before_state,
                    hand,
                    cards,
                    scorer=self.joker_evaluator.scorer,
                )
                after = literal_expected_score(
                    after_state,
                    hand,
                    cards,
                    scorer=self.joker_evaluator.scorer,
                )
            except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
                continue
            gain = (float(after) - float(before)) / max(abs(float(before)), 1.0)
            if observed is None:
                weight = 1.0
            else:
                weight = (
                    self.joker_evaluator._OBSERVED_HAND_PRIOR_WEIGHT
                    + observed.get(self.joker_evaluator._hand_key(hand.value), 0.0)
                )
            weighted_gain += gain * weight
            total_weight += weight

        direct_gain = weighted_gain / total_weight if total_weight > 0.0 else 0.0
        weights = self.joker_evaluator.weights
        direct_value = max(
            -float(weights.direct_scoring_cap),
            min(
                float(weights.direct_scoring_cap),
                direct_gain * float(weights.direct_scoring_gain),
            ),
        )
        blue_count = sum(_growth_kind(joker) == "BLUE" for joker in active)
        return direct_value, (
            f"deck growth added cards={count}",
            f"active Blue Joker count={blue_count}; exact coefficient=+2 Chips/card",
            f"active Hologram count={hologram_growth}; exact coefficient=+0.25 XMult/card",
            f"representative whole-build relative score gain={direct_gain:.6f}",
            f"D2-normalized literal deck-growth value={direct_value:.3f}",
        )
