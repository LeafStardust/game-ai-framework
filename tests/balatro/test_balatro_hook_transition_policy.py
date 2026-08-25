from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel
from games.balatro.state import BalatroState


def _state(*, chicot: bool = False) -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.boss_name = "The Hook"
    state.blind = Blind(BlindType.BOSS, 10_000)
    state.hand = [
        BalatroCard("A", "Spades", live_id=1),
        BalatroCard("K", "Hearts", live_id=2),
        BalatroCard("Q", "Clubs", live_id=3),
        BalatroCard("9", "Diamonds", live_id=4),
    ]
    # One public signature keeps the draw distribution deterministic. The Hook's
    # uncertainty is then solely which two of the three retained cards it forces
    # into the discard event.
    state.deck = [BalatroCard("2", "Spades") for _ in range(3)]
    state.hands_remaining = 2
    state.discards_remaining = 2
    state.discards_used = 0
    if chicot:
        state.jokers = [ChicotJoker()]
    return state


def _planner() -> LiveBlindClearPlanner:
    return LiveBlindClearPlanner(
        draw_outcomes=PublicDrawOutcomeModel(
            exact_combination_limit=10_000,
            sample_count=64,
            seed=1,
        ),
        play_width=4,
        discard_width=0,
        horizon=2,
    )


def test_hook_branches_over_two_random_retained_discards_and_refills_hand():
    state = _state()
    planner = _planner()
    observed = []

    def best_value(next_state, _depth):
        observed.append(next_state)
        return planner._terminal_value(next_state, clear=False), True

    planner._best_value = best_value
    action = BalatroAction(PLAY_CARDS, cards=[state.hand[0]])

    planner._estimate_play(state, action, 2)

    # Three retained cards choose two uniformly: C(3, 2) = 3 Hook branches.
    assert len(observed) == 3
    assert all(len(child.discard_pile) == 2 for child in observed)
    assert all(len(child.hand) == 4 for child in observed)
    assert all(child.discards_used == 0 for child in observed)
    assert {
        frozenset(card.rank for card in child.discard_pile)
        for child in observed
    } == {
        frozenset(("K", "Q")),
        frozenset(("K", "9")),
        frozenset(("Q", "9")),
    }


def test_hook_forced_discard_triggers_normal_discard_joker_effects():
    state = _state()
    green = GreenJoker()
    green.mult = 3
    state.jokers = [green]
    planner = _planner()
    observed_mult = []

    def best_value(next_state, _depth):
        observed_mult.append(next_state.jokers[0].mult)
        return planner._terminal_value(next_state, clear=False), True

    planner._best_value = best_value
    planner._estimate_play(
        state,
        BalatroAction(PLAY_CARDS, cards=[state.hand[0]]),
        2,
    )

    # Green increments on the scored hand and then loses one from The Hook's
    # forced CARDS_DISCARDED event, returning to its starting +3 Mult state.
    assert observed_mult == [3, 3, 3]
    assert green.mult == 3


def test_chicot_disables_hook_forced_discard_transition():
    state = _state(chicot=True)
    planner = _planner()
    observed = []

    def best_value(next_state, _depth):
        observed.append(next_state)
        return planner._terminal_value(next_state, clear=False), True

    planner._best_value = best_value
    planner._estimate_play(
        state,
        BalatroAction(PLAY_CARDS, cards=[state.hand[0]]),
        2,
    )

    assert len(observed) == 1
    assert observed[0].discard_pile == []
    assert len(observed[0].hand) == 4
