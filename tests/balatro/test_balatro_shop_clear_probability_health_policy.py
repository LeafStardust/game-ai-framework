from types import SimpleNamespace

import games.balatro.shop_clear_probability_health_policy as policy
from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator
from games.balatro.card import BalatroCard
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


class _FixedScorer:
    def score(self, *args, **kwargs):
        del args, kwargs
        return SimpleNamespace(total=100.0)


def _shop_state(*, target=1000, cards=None):
    state = BalatroState()
    state.phase = "SHOP"
    state.blind_score = target
    state.score = target + 500
    state.hands_remaining = 0
    state.discards_remaining = 0
    state.discards_used = 3
    state.owned_deck = list(cards or state.deck)
    state.deck = []
    return state


def test_production_shop_survival_uses_bounded_clear_probability(monkeypatch):
    state = _shop_state(target=1000)
    monkeypatch.setattr(
        policy,
        "bounded_shop_clear_probability",
        lambda state, *, target, hands: 0.25,
    )

    evaluator = RuntimeBuildHealthEvaluator(scorer=BalatroScorer())
    survival, immediate = evaluator._survival_and_immediate(state)

    assert survival == 0.25
    assert 0.0 <= immediate <= 1.0


def test_unavailable_bounded_projection_preserves_generic_fallback(monkeypatch):
    state = _shop_state(target=1000)
    monkeypatch.setattr(
        policy,
        "bounded_shop_clear_probability",
        lambda state, *, target, hands: None,
    )

    evaluator = RuntimeBuildHealthEvaluator(scorer=BalatroScorer())
    survival, immediate = evaluator._survival_and_immediate(state)

    assert 0.0 <= survival <= 1.0
    assert 0.0 <= immediate <= 1.0
    assert survival != 0.25


def test_custom_scorer_contract_is_not_routed_through_live_d1(monkeypatch):
    state = _shop_state(target=1000)
    calls = []

    def unexpected(*args, **kwargs):
        calls.append((args, kwargs))
        return 0.0

    monkeypatch.setattr(policy, "bounded_shop_clear_probability", unexpected)
    evaluator = RuntimeBuildHealthEvaluator(scorer=_FixedScorer())
    survival, immediate = evaluator._survival_and_immediate(state)

    assert calls == []
    assert survival == 0.4
    assert immediate == 0.4


def test_bounded_opening_projection_is_invariant_to_owned_deck_order(monkeypatch):
    cards = [
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Clubs"),
        BalatroCard("J", "Diamonds"),
        BalatroCard("10", "Spades"),
        BalatroCard("9", "Hearts"),
        BalatroCard("8", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("6", "Spades"),
        BalatroCard("5", "Hearts"),
    ]

    class _FakePlanner:
        def __init__(self, **kwargs):
            del kwargs

        def plan(self, state):
            ranks = sorted(card.rank for card in state.hand)
            probability = 1.0 if "A" in ranks else 0.0
            return SimpleNamespace(
                value=SimpleNamespace(clear_probability=probability),
            )

    monkeypatch.setattr(policy, "LiveBlindClearPlanner", _FakePlanner)
    forward = _shop_state(target=1000, cards=cards)
    reverse = _shop_state(target=1000, cards=reversed(cards))

    first = policy.bounded_shop_clear_probability(forward, target=1000, hands=4)
    second = policy.bounded_shop_clear_probability(reverse, target=1000, hands=4)

    assert first == second


def test_shop_opening_branch_resets_round_state_without_mutating_authoritative_shop():
    state = _shop_state(target=1200)
    state.boss_name = "The Plant"
    state.boss_blind_state_observed = True
    state.boss_blind_hands = {"PAIR"}
    state.boss_blind_only_hand = "PAIR"
    original_score = state.score
    original_boss = state.boss_name

    composition = policy.PublicDeckComposition.from_cards(state.owned_deck)
    model = policy.PublicDrawOutcomeModel(
        exact_combination_limit=1,
        sample_count=1,
        seed=0,
    )
    opening = model.distribution(composition, state.hand_size).outcomes[0]
    branch = policy._opening_state(
        state,
        target=1200,
        hands=4,
        opening=opening,
        composition=composition,
        model=model,
    )

    assert branch.phase == "SELECTING_HAND"
    assert branch.score == 0
    assert branch.blind.requirement == 1200
    assert branch.hands_remaining == 4
    assert branch.discards_remaining == 3
    assert branch.discards_used == 0
    assert branch.boss_name is None
    assert state.phase == "SHOP"
    assert state.score == original_score
    assert state.boss_name == original_boss
