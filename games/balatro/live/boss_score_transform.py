from __future__ import annotations

from math import ceil

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.scoring import HandScore


def effective_boss_hand_level(state, hand, hand_level: int) -> int:
    if state is None or boss_blind_disabled_by_owned_jokers(state):
        return int(hand_level)
    if str(getattr(state, "boss_name", "") or "") == "The Arm":
        return max(1, int(hand_level) - 1)
    return int(hand_level)


def transform_boss_base_score(state, chips: int, mult: int) -> tuple[int, int]:
    if state is None or boss_blind_disabled_by_owned_jokers(state):
        return int(chips), int(mult)
    if str(getattr(state, "boss_name", "") or "") == "The Flint":
        return int(ceil(chips / 2)), int(ceil(mult / 2))
    return int(chips), int(mult)


class BossBaseScoreScorerMixin:
    """Transform only the leveled poker-hand base before card/Joker scoring."""

    def score(self, hand, state=None, cards=None, **kwargs):
        if state is None or boss_blind_disabled_by_owned_jokers(state):
            return super().score(hand, state, cards, **kwargs)

        boss_name = str(getattr(state, "boss_name", "") or "")
        if boss_name not in {"The Arm", "The Flint"}:
            return super().score(hand, state, cards, **kwargs)

        levels = getattr(state, "hand_levels", {})
        hand_level = int(levels.get(hand.value, levels.get(hand, 1)) or 1)
        effective_level = effective_boss_hand_level(state, hand, hand_level)
        base = self.SCORES[hand]

        planet_chips = 0
        planet_mult = 0
        if hand_level > 1 or effective_level > 1:
            from games.balatro.planets import PLANET_CARDS

            planet = next(
                (
                    candidate
                    for candidate in PLANET_CARDS.values()
                    if candidate.hand_type == hand.value
                ),
                None,
            )
            if planet is not None:
                planet_chips = int(planet.chips)
                planet_mult = int(planet.mult)

        current_increment_chips = planet_chips * max(0, hand_level - 1)
        current_increment_mult = planet_mult * max(0, hand_level - 1)
        target_chips = base.chips + planet_chips * max(0, effective_level - 1)
        target_mult = base.mult + planet_mult * max(0, effective_level - 1)
        target_chips, target_mult = transform_boss_base_score(
            state,
            target_chips,
            target_mult,
        )

        # BalatroScorer will still add the current state's ordinary level increment.
        # Shift the temporary level-1 base so that the sum lands on the boss target,
        # while keeping state.hand_levels untouched for Matador and other mechanics.
        adjusted = HandScore(
            target_chips - current_increment_chips,
            target_mult - current_increment_mult,
            base.x_mult,
        )
        original_scores = self.SCORES
        self.SCORES = {**original_scores, hand: adjusted}
        try:
            return super().score(hand, state, cards, **kwargs)
        finally:
            self.SCORES = original_scores
