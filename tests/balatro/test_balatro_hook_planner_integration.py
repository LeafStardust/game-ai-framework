from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.jokers.chicot import ChicotJoker
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


def test_hook_planner_keeps_each_score_branch_forced_discards_removed():
    state = _state()
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

    # The score-outcome layer already creates C(3, 2)=3 exact Hook branches.
    # D1 must carry each branch's discarded identities forward instead of
    # rebuilding all children from the common pre-Hook retained hand.
    assert len(observed) == 3
    assert all(len(child.discard_pile) == 2 for child in observed)
    assert all(len(child.hand) == 4 for child in observed)

    discarded_sets = set()
    for child in observed:
        discarded_ids = {
            card.live_id for card in child.discard_pile if card.live_id is not None
        }
        held_ids = {
            card.live_id for card in child.hand if card.live_id is not None
        }
        assert discarded_ids.isdisjoint(held_ids)
        discarded_sets.add(frozenset(discarded_ids))

    assert discarded_sets == {
        frozenset((2, 3)),
        frozenset((2, 4)),
        frozenset((3, 4)),
    }


def test_chicot_restores_single_ordinary_post_play_branch():
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
