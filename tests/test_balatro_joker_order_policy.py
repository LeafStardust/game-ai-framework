from games.balatro.joker_order_policy import JokerOrderPolicy
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.cavendish import CavendishJoker
from games.balatro.jokers.dagger import DaggerJoker
from games.balatro.jokers.egg import EggJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.state import BalatroState


def _state(*jokers, phase="SHOP"):
    state = BalatroState()
    state.phase = phase
    state.jokers = list(jokers)
    return state


def test_order_policy_moves_additive_mult_before_blueprinted_xmult():
    state = _state(
        BlueprintJoker(),
        FlatMultJoker(10),
        CavendishJoker(),
    )

    decision = JokerOrderPolicy().recommend(state)

    assert decision is not None
    assert decision.permutation == (1, 0, 2)
    assert decision.ordered_score > decision.current_score
    assert decision.to_action().target == (1, 0, 2)


def test_order_policy_places_disposable_joker_right_of_dagger_before_blind():
    dagger = DaggerJoker()
    valuable = FlatMultJoker(20)
    valuable.sell_cost = 1
    disposable = EggJoker()
    disposable.sell_value = 1
    state = _state(dagger, valuable, disposable, phase="BLIND_SELECT")

    decision = JokerOrderPolicy().recommend(state)

    assert decision is not None
    assert decision.permutation == (0, 2, 1)
    assert any("Dagger sacrifice=EggJoker" in note for note in decision.rationale)


def test_order_policy_does_not_emit_noop_for_already_optimal_order():
    state = _state(
        FlatMultJoker(10),
        BlueprintJoker(),
        CavendishJoker(),
    )

    assert JokerOrderPolicy().recommend(state) is None


def test_blind_select_bypasses_scoring_order_without_dagger():
    class _NoScoringPolicy(JokerOrderPolicy):
        def _score(self, state, permutation, *, phase):
            raise AssertionError("blind selection must not run scoring-order search")

    state = _state(
        FlatMultJoker(10),
        BlueprintJoker(),
        CavendishJoker(),
        phase="BLIND_SELECT",
    )

    assert _NoScoringPolicy().recommend(state) is None


def test_six_joker_board_uses_bounded_neighbour_search():
    class _CountingPolicy(JokerOrderPolicy):
        def __init__(self):
            super().__init__()
            self.scored = 0

        def _score(self, state, permutation, *, phase):
            self.scored += 1
            return float(sum(index * value for index, value in enumerate(permutation))), ()

    policy = _CountingPolicy()
    state = _state(*(FlatMultJoker(index) for index in range(1, 7)))

    policy.recommend(state)

    # Current order plus C(6, 2) one-swap neighbours, not 6! permutations.
    assert policy.scored == 16
