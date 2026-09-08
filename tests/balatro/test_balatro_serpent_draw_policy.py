from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel
from games.balatro.serpent_draw_policy import SERPENT_DRAW_COUNT, serpent_draw_count
from games.balatro.state import BalatroState


class RecordingDrawOutcomes(PublicDrawOutcomeModel):
    def __init__(self):
        super().__init__(exact_combination_limit=10_000, sample_count=32, seed=1)
        self.requested_draws: list[int] = []

    def distribution(self, composition, draws):
        self.requested_draws.append(int(draws))
        return super().distribution(composition, draws)


def _serpent_state() -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.boss_name = "The Serpent"
    state.hand = [
        BalatroCard("A", "Spades", live_id=1),
        BalatroCard("K", "Hearts", live_id=2),
        BalatroCard("8", "Clubs", live_id=3),
        BalatroCard("4", "Diamonds", live_id=4),
    ]
    state.deck = [
        BalatroCard("2", "Spades"),
        BalatroCard("3", "Hearts"),
        BalatroCard("5", "Clubs"),
        BalatroCard("6", "Diamonds"),
    ]
    state.hands_remaining = 2
    state.discards_remaining = 1
    state.blind = Blind(BlindType.BOSS, 10_000)
    return state


def _planner(draws: RecordingDrawOutcomes) -> LiveBlindClearPlanner:
    return LiveBlindClearPlanner(
        draw_outcomes=draws,
        play_width=2,
        discard_width=2,
        child_play_width=1,
        child_discard_width=0,
        horizon=2,
        max_nodes=100,
    )


def test_serpent_draw_count_overrides_ordinary_replacement_width():
    state = _serpent_state()

    assert serpent_draw_count(state, 1) == SERPENT_DRAW_COUNT == 3
    assert serpent_draw_count(state, 5) == 3


def test_chicot_disables_serpent_draw_override():
    state = _serpent_state()
    state.jokers = [ChicotJoker()]

    assert serpent_draw_count(state, 1) == 1
    assert serpent_draw_count(state, 5) == 5


def test_serpent_play_transition_draws_exactly_three_cards():
    state = _serpent_state()
    draws = RecordingDrawOutcomes()
    planner = _planner(draws)
    action = BalatroAction(PLAY_CARDS, cards=[state.hand[0]])

    planner._estimate_play(state, action, depth=2)

    assert draws.requested_draws
    assert set(draws.requested_draws) == {3}


def test_serpent_discard_transition_draws_exactly_three_cards():
    state = _serpent_state()
    draws = RecordingDrawOutcomes()
    planner = _planner(draws)
    action = BalatroAction(DISCARD_CARDS, cards=[state.hand[-1]])

    planner._estimate_discard(state, action, depth=2)

    assert draws.requested_draws
    assert set(draws.requested_draws) == {3}
