from __future__ import annotations

from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner


class HouseBlindClearPlanner(LiveBlindClearPlanner):
    """Normal-score planner for The House using save-backed hand identities.

    The House changes what a human player can see, not scoring or legal actions.
    For the current live-agent integration we intentionally use the structured
    hand identities already present in save.jkr, including cards that Balatro
    renders face-down. This keeps The House on the same structured-state-first
    observation path as other blinds. A stricter human-visible masking layer can
    be reintroduced later if required by the project.
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
