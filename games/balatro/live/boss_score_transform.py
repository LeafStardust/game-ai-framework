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


def boss_hand_scores_zero(state, hand) -> bool:
    """Return whether public mutable boss state makes this hand score zero."""
    if state is None or boss_blind_disabled_by_owned_jokers(state):
        return False

    boss_name = str(getattr(state, "boss_name", "") or "")
    hand_name = str(getattr(hand, "value", hand) or "")

    if boss_name == "The Mouth":
        only_hand = getattr(state, "boss_blind_only_hand", None)
        return bool(only_hand) and hand_name != str(only_hand)

    if boss_name == "The Eye":
        prior_hands = {
            str(value)
            for value in (getattr(state, "boss_blind_hands", set()) or set())
        }
        return hand_name in prior_hands

    return False


class BossBaseScoreScorerMixin:
    """Apply validated boss transformations before ordinary score projection."""

    def score(self, hand, state=None, cards=None, **kwargs):
        if state is None or boss_blind_disabled_by_owned_jokers(state):
            return super().score(hand, state, cards, **kwargs)

        # The Mouth debuffs every hand type except the first accepted one for the
        # rest of the blind; The Eye debuffs a type after it has scored once. Public
        # live state exposes those histories. Model them as literal zero-score hands
        # so D1 never treats a forbidden/repeated play as useful progress.
        if boss_hand_scores_zero(state, hand):
            return HandScore(0, 0, 1.0)

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
