from types import SimpleNamespace

from games.balatro.card import BalatroCard
from games.balatro.joker_order_policy import JokerOrderPolicy
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.cavendish import CavendishJoker
from games.balatro.jokers.dagger import DaggerJoker
from games.balatro.jokers.droll_joker import DrollJoker
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


def test_order_policy_targets_blueprint_for_the_exact_selected_flush():
    cards = [
        BalatroCard(rank, "Clubs", live_id=index)
        for index, rank in enumerate(("2", "4", "6", "8", "10"))
    ]
    state = _state(
        BlueprintJoker(),
        FlatMultJoker(4),
        DrollJoker(),
        phase="SELECTING_HAND",
    )
    state.hand = cards

    decision = JokerOrderPolicy().recommend_for_play(state, cards)

    assert decision is not None
    ordered = [state.jokers[index] for index in decision.permutation]
    blueprint_index = ordered.index(state.jokers[0])
    assert ordered[blueprint_index + 1] is state.jokers[2]
    assert decision.ordered_score > decision.current_score
    assert any("exact selected-play" in note for note in decision.rationale)


def test_selecting_hand_generic_order_defers_to_exact_play_authority():
    state = _state(
        CavendishJoker(),
        FlatMultJoker(10),
        phase="SELECTING_HAND",
    )

    # Representative shop probes and the exact selected hand can prefer opposite
    # layouts.  Emitting both recommendations caused an endless live reorder loop.
    assert JokerOrderPolicy().recommend(state, phase="SELECTING_HAND") is None


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


def test_order_policy_does_not_project_eternal_dagger_feed_as_destroyed():
    dagger = DaggerJoker()
    eternal = FlatMultJoker(20)
    eternal.eternal = True
    eternal.sell_value = 10
    disposable = EggJoker()
    disposable.sell_value = 1
    state = _state(dagger, eternal, disposable, phase="BLIND_SELECT")

    decision = JokerOrderPolicy().recommend(state)

    assert decision is not None
    ordered = [state.jokers[index] for index in decision.permutation]
    dagger_index = ordered.index(dagger)
    assert ordered[dagger_index + 1] is disposable
    assert JokerOrderPolicy._dagger_sacrifice_targets(
        [dagger, eternal],
    ) == ()


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


def test_dagger_order_protects_negative_feed_even_when_safe_order_scores_lower():
    class _CurrentOrderBiasedPolicy(JokerOrderPolicy):
        def _score(self, state, permutation, *, phase):
            del state, phase
            return (100.0 if permutation == (0, 1, 2) else 0.0), ()

    dagger = DaggerJoker()
    negative_feed = EggJoker()
    negative_feed.edition = "Negative"
    valuable = FlatMultJoker(20)
    state = _state(dagger, negative_feed, valuable, phase="BLIND_SELECT")

    policy = _CurrentOrderBiasedPolicy()
    decision = policy.recommend(state)

    assert decision is not None
    assert decision.ordered_score < decision.current_score
    assert any(
        "PROTECTED_FROM_DAGGER_SACRIFICE" in note
        for note in decision.rationale
    )
    ordered = [state.jokers[index] for index in decision.permutation]
    assert all(
        getattr(target, "edition", None) != "Negative"
        for target in policy._dagger_sacrifice_targets(ordered)
    )


def test_active_dagger_strategy_can_intentionally_sacrifice_negative_feed():
    class _CurrentOrderBiasedPolicy(JokerOrderPolicy):
        def _score(self, state, permutation, *, phase):
            del state, phase
            return (100.0 if permutation == (0, 1, 2) else 0.0), ()

    policy = _CurrentOrderBiasedPolicy()
    policy.evaluator.strategy_tracker = SimpleNamespace(
        observe=lambda state: SimpleNamespace(
            active_status="HIGHLIGHTED",
            dominant_strategy_id="dagger_sacrifice",
        ),
        topology=SimpleNamespace(path=lambda strategy_id: (strategy_id,)),
    )
    dagger = DaggerJoker()
    negative_feed = EggJoker()
    negative_feed.edition = "Negative"
    valuable = FlatMultJoker(20)
    state = _state(dagger, negative_feed, valuable, phase="BLIND_SELECT")

    assert policy.recommend(state) is None
    assert any(
        "ACTIVE_DAGGER_STRATEGY_INTENTIONAL_SACRIFICE" in note
        for note in policy.last_negative_retention_diagnostics
    )
