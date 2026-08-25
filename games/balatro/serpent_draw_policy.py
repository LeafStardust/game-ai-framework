from __future__ import annotations

from contextlib import contextmanager

from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner


SERPENT_DRAW_COUNT = 3


def serpent_draw_count(state, ordinary_draw_count: int) -> int:
    """Return the exact post-action public draw count under The Serpent.

    The Serpent changes both Play and Discard transitions: after either action,
    Balatro draws exactly three cards (bounded naturally by the remaining deck).
    Chicot disables the boss and restores the ordinary replacement count.
    """
    if state is None or boss_blind_disabled_by_owned_jokers(state):
        return max(0, int(ordinary_draw_count))
    if str(getattr(state, "boss_name", "") or "") == "The Serpent":
        return SERPENT_DRAW_COUNT
    return max(0, int(ordinary_draw_count))


@contextmanager
def _serpent_distribution_override(planner: LiveBlindClearPlanner, state):
    ordinary_distribution = planner.draw_outcomes.distribution
    forced = serpent_draw_count(state, -1)
    if forced != SERPENT_DRAW_COUNT:
        yield
        return

    had_instance_override = "distribution" in vars(planner.draw_outcomes)
    prior_instance_value = vars(planner.draw_outcomes).get("distribution")

    def distribution(composition, _requested_draws):
        return ordinary_distribution(composition, SERPENT_DRAW_COUNT)

    planner.draw_outcomes.distribution = distribution
    try:
        yield
    finally:
        if had_instance_override:
            planner.draw_outcomes.distribution = prior_instance_value
        else:
            delattr(planner.draw_outcomes, "distribution")


def install_serpent_draw_policy() -> None:
    if getattr(LiveBlindClearPlanner, "_serpent_draw_policy_installed", False):
        return

    original_estimate_play = LiveBlindClearPlanner._estimate_play
    original_estimate_discard = LiveBlindClearPlanner._estimate_discard

    def estimate_play(self, state, action, depth):
        with _serpent_distribution_override(self, state):
            return original_estimate_play(self, state, action, depth)

    def estimate_discard(self, state, action, depth):
        with _serpent_distribution_override(self, state):
            return original_estimate_discard(self, state, action, depth)

    LiveBlindClearPlanner._estimate_play = estimate_play
    LiveBlindClearPlanner._estimate_discard = estimate_discard
    LiveBlindClearPlanner._serpent_draw_policy_installed = True
