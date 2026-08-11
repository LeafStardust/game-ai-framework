from __future__ import annotations

from games.balatro.actions import BalatroAction
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner


class PsychicBlindClearPlanner(LiveBlindClearPlanner):
    """Live blind-clear planner for The Psychic.

    The Psychic's only modeled live restriction is that every PLAY_CARDS action
    must contain exactly five cards. Discard actions are unchanged. Scoring is
    delegated to the normal live score/Joker projection once the play is legal.
    """

    BOSS_NAME = "The Psychic"
    REQUIRED_PLAY_CARDS = 5

    @classmethod
    def supports(cls, state) -> bool:
        return getattr(state, "boss_name", None) == cls.BOSS_NAME

    def _require_state(self, state) -> None:
        super()._require_state(state)
        boss_name = getattr(state, "boss_name", None)
        if boss_name != self.BOSS_NAME:
            raise ValueError(
                f"Psychic planner requires {self.BOSS_NAME}, observed {boss_name!r}"
            )

    def _candidate_actions(self, state, *, allow_discards: bool) -> list[BalatroAction]:
        plays = [
            action
            for action in self.action_generator.generate_play_actions(state)
            if len(action.cards) == self.REQUIRED_PLAY_CARDS
        ]
        ranked_plays = sorted(
            plays,
            key=lambda action: self._play_priority(state, action),
            reverse=True,
        )[: self.play_width]

        if not allow_discards or int(getattr(state, "discards_remaining", 0)) <= 0:
            return ranked_plays

        discards = self.action_generator.generate_discard_actions(state)
        ranked_discards = sorted(
            discards,
            key=lambda action: self._discard_priority(state, action),
            reverse=True,
        )[: self.discard_width]
        return ranked_plays + ranked_discards
