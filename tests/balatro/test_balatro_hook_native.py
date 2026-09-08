from copy import deepcopy
from types import SimpleNamespace

import games.balatro  # noqa: F401 - initialize production registration
from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner


def _card(live_id, rank="2"):
    return SimpleNamespace(
        live_id=live_id,
        rank=rank,
        suit="Clubs",
        enhancement=None,
        edition=None,
        seal=None,
        debuffed=False,
        permanent_bonus=0,
    )


class _FakeDrawOutcomes:
    def __init__(self):
        self.requested_draws = []

    def distribution(self, _composition, draws):
        self.requested_draws.append(draws)
        return SimpleNamespace(
            exact=True,
            outcomes=(
                SimpleNamespace(
                    cards=("draw-1", "draw-2", "draw-3"),
                    probability=1.0,
                ),
            ),
        )

    @staticmethod
    def card_from_signature(signature):
        return _card(signature)

    @staticmethod
    def remaining_cards(_composition, _draw_outcome):
        return []


def test_native_hook_play_refills_from_post_forced_discard_branch():
    played = _card("played", "A")
    forced_one = _card("forced-1")
    forced_two = _card("forced-2")
    retained_one = _card("retained-1")
    retained_two = _card("retained-2")
    original_hand = [played, forced_one, forced_two, retained_one, retained_two]

    # Hook scoring has already removed the two random forced-discard cards from
    # this branch. The played card remains until planner transition handling.
    branch_state = SimpleNamespace(
        hand=[deepcopy(played), deepcopy(retained_one), deepcopy(retained_two)],
        deck=[],
        score=0,
        hands_remaining=2,
        discards_remaining=1,
        consumables=[],
        consumable_slots=2,
        jokers=[],
        boss_name="The Hook",
    )
    projection = SimpleNamespace(
        joker_projection_complete=True,
        state_after_scoring=None,
        outcomes=(
            SimpleNamespace(
                score=10,
                probability=1.0,
                state_after_scoring=branch_state,
            ),
        ),
    )
    evaluator = SimpleNamespace(project_play=lambda _state, _action: projection)
    draw_outcomes = _FakeDrawOutcomes()
    planner = LiveBlindClearPlanner(
        evaluator=evaluator,
        draw_outcomes=draw_outcomes,
    )
    planner._guaranteed_next_play_value = lambda _state: None

    continued_hand_sizes = []

    def best_value(next_state, _depth):
        continued_hand_sizes.append(len(next_state.hand))
        return planner._zero_value(), True

    planner._best_value = best_value
    state = SimpleNamespace(
        hand=original_hand,
        deck=[_card(f"deck-{index}") for index in range(8)],
        score=0,
        hands_remaining=2,
        discards_remaining=1,
        consumables=[],
        consumable_slots=2,
        jokers=[],
        boss_name="The Hook",
        blind=SimpleNamespace(requirement=100),
    )
    action = BalatroAction(PLAY_CARDS, cards=[played])

    planner._estimate_play(state, action, depth=2)

    # Five original cards minus one played and two Hook-forced discards leaves two
    # retained cards, so the exact refill is three cards back to hand size five.
    assert draw_outcomes.requested_draws == [3]
    assert continued_hand_sizes == [5]


def test_production_stack_does_not_install_hook_planner_overlay():
    assert LiveBlindClearPlanner._estimate_play.__module__ == (
        "games.balatro.live.blind_clear_planner"
    )
    assert not hasattr(
        LiveBlindClearPlanner,
        "_hook_planner_integration_installed",
    )
