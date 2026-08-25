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

    def _candidate_actions(
        self,
        state,
        *,
        allow_discards: bool,
        play_width: int | None = None,
        discard_width: int | None = None,
    ) -> list[BalatroAction]:
        play_limit = self.play_width if play_width is None else int(play_width)
        discard_limit = (
            self.discard_width if discard_width is None else int(discard_width)
        )

        plays = [
            action
            for action in self.action_generator.generate_play_actions(state)
            if len(action.cards) == self.REQUIRED_PLAY_CARDS
        ]
        ranked_plays = sorted(
            plays,
            key=lambda action: self._play_priority(state, action),
            reverse=True,
        )[:play_limit]

        if (
            not allow_discards
            or discard_limit <= 0
            or int(getattr(state, "discards_remaining", 0)) <= 0
        ):
            return ranked_plays

        discards = self.action_generator.generate_discard_actions(state)
        all_ranked_discards = sorted(
            discards,
            key=lambda action: self._discard_priority(state, action),
            reverse=True,
        )
        ranked_discards = all_ranked_discards[:discard_limit]

        # The Psychic constrains PLAY actions only. Canonical D1 can legitimately
        # rank several five-card redraws at the top of the discard beam, especially
        # while badly under pace, but allowing that to fill the whole beam makes the
        # planner behave as though the boss's five-card rule also applies to DISCARD.
        # Preserve the strongest legal non-five-card discard whenever one exists so
        # expectimax can still compare ordinary targeted redraws against full redraws.
        if (
            ranked_discards
            and all(len(action.cards) == self.REQUIRED_PLAY_CARDS for action in ranked_discards)
        ):
            best_non_five = next(
                (
                    action
                    for action in all_ranked_discards
                    if len(action.cards) != self.REQUIRED_PLAY_CARDS
                ),
                None,
            )
            if best_non_five is not None:
                ranked_discards[-1] = best_non_five

        return ranked_plays + ranked_discards
