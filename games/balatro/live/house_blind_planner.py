from __future__ import annotations

from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner


class HouseBlindClearPlanner(LiveBlindClearPlanner):
    """Normal-score planner for The House once every held card is face-up.

    The House changes observation, not scoring: its initial hand is hidden. The
    external validator is responsible for proving from screen pixels that no held
    cards remain face-down before this planner may inspect save-backed identities.
    Subsequent draws are ordinary face-up draws, so normal public draw modeling is
    valid after that visibility gate passes.
    """

    BOSS_NAME = "The House"

    @classmethod
    def supports(cls, state) -> bool:
        return getattr(state, "boss_name", None) == cls.BOSS_NAME

    def _require_state(self, state) -> None:
        super()._require_state(state)
        boss_name = getattr(state, "boss_name", None)
        if boss_name != self.BOSS_NAME:
            raise ValueError(
                f"House planner requires {self.BOSS_NAME}, observed {boss_name!r}"
            )
