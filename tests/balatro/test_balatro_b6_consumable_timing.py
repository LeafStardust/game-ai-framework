from types import SimpleNamespace

from games.balatro.actions import USE_CONSUMABLE
from games.balatro.card import BalatroCard
from games.balatro.jokers.ancient_joker import AncientJoker
from games.balatro.live.consumable_timing import HOLD, USE, LiveConsumableTimingPolicy
from games.balatro.state import BalatroState
from games.balatro.tarots import Hermit, HighPriestess, Strength, Sun, Temperance


class _Blind:
    def __init__(self, requirement: int):
        self.requirement = requirement

    def copy(self):
        return _Blind(self.requirement)


def _state(
    cards: list[BalatroCard],
    *,
    hands_remaining: int = 4,
    requirement: int = 100_000,
) -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = cards
    state.deck = [
        BalatroCard(card.rank, card.suit, card.enhancement, card.edition, card.seal)
        for card in cards
    ]
    state.hands_remaining = hands_remaining
    state.score = 0
    state.blind = _Blind(requirement)
    return state


def test_early_marginal_strength_use_holds_without_concrete_timing_advantage():
    state = _state([BalatroCard("2", "Hearts"), BalatroCard("3", "Clubs")])
    strength = Strength()
    state.consumables = [strength]
    state.consumable_slots = 2

    recommendation = LiveConsumableTimingPolicy().recommend(state, strength)

    assert recommendation.decision == HOLD
    assert not recommendation.should_use
    assert recommendation.target is not None
    assert recommendation.after_projection is not None
    assert (
        recommendation.after_projection.expected_hand_score
        > recommendation.before_projection.expected_hand_score
    )
    assert any("no concrete timing advantage" in note for note in recommendation.rationale)


def test_final_hand_uses_positive_immediate_strength_gain():
    state = _state(
        [BalatroCard("2", "Hearts"), BalatroCard("3", "Clubs")],
        hands_remaining=1,
    )
    strength = Strength()
    state.consumables = [strength]

    recommendation = LiveConsumableTimingPolicy().recommend(state, strength)

    assert recommendation.decision == USE
    assert recommendation.should_use
    assert recommendation.target is not None
    assert recommendation.after_projection is not None
    assert (
        recommendation.after_projection.expected_hand_score
        > recommendation.before_projection.expected_hand_score
    )
    assert any("final hand" in note for note in recommendation.rationale)

    action = recommendation.to_action()
    assert action is not None
    assert action.action_type == USE_CONSUMABLE
    assert action.target is strength
    assert action.cards == list(recommendation.target.cards)


def test_full_consumable_slots_can_use_positive_build_context_target():
    four = BalatroCard("4", "Clubs")
    state = _state([four])
    ancient = AncientJoker()
    ancient.suit = "Hearts"
    state.jokers = [ancient]
    sun = Sun()
    state.consumables = [sun]
    state.consumable_slots = 1

    recommendation = LiveConsumableTimingPolicy().recommend(state, sun)

    assert recommendation.decision == USE
    assert recommendation.target is not None
    assert recommendation.target.target_indices == (0,)
    assert recommendation.target.cards == (four,)
    assert recommendation.target.contextual_delta > 0.0
    assert recommendation.after_projection is not None
    assert (
        recommendation.after_projection.expected_hand_score
        >= recommendation.before_projection.expected_hand_score
    )
    assert any("positive build value" in note for note in recommendation.rationale)


def test_hermit_uses_at_peak_money_value_without_card_target():
    state = _state([BalatroCard("2", "Hearts")])
    hermit = Hermit()
    state.money = 10
    state.consumables = [hermit]
    state.consumable_slots = 2

    recommendation = LiveConsumableTimingPolicy().recommend(state, hermit)

    assert recommendation.decision == USE
    assert recommendation.target is None
    assert recommendation.immediate_gain == 10.0
    assert recommendation.before_projection is None
    assert recommendation.after_projection is None
    assert any("maximum-value $10 threshold" in note for note in recommendation.rationale)

    action = recommendation.to_action()
    assert action is not None
    assert action.action_type == USE_CONSUMABLE
    assert action.target is hermit
    assert action.cards == []


def test_hermit_below_peak_holds_when_slot_is_free():
    state = _state([BalatroCard("2", "Hearts")])
    hermit = Hermit()
    state.money = 6
    state.consumables = [hermit]
    state.consumable_slots = 2

    recommendation = LiveConsumableTimingPolicy().recommend(state, hermit)

    assert recommendation.decision == HOLD
    assert recommendation.immediate_gain == 6.0
    assert recommendation.to_action() is None
    assert any("below $10" in note for note in recommendation.rationale)


def test_full_slots_can_use_positive_hermit_gain_below_peak():
    state = _state([BalatroCard("2", "Hearts")])
    hermit = Hermit()
    state.money = 6
    state.consumables = [hermit]
    state.consumable_slots = 1

    recommendation = LiveConsumableTimingPolicy().recommend(state, hermit)

    assert recommendation.decision == USE
    assert recommendation.immediate_gain == 6.0
    assert any("full consumable slots" in note for note in recommendation.rationale)


def test_temperance_uses_at_fifty_dollar_cap_from_live_sell_costs():
    state = _state([BalatroCard("2", "Hearts")])
    temperance = Temperance()
    state.jokers = [
        SimpleNamespace(sell_cost=30),
        SimpleNamespace(sell_cost=25),
    ]
    state.consumables = [temperance]
    state.consumable_slots = 2

    recommendation = LiveConsumableTimingPolicy().recommend(state, temperance)

    assert recommendation.decision == USE
    assert recommendation.target is None
    assert recommendation.immediate_gain == 50.0
    assert any("$50 payout cap" in note for note in recommendation.rationale)

    action = recommendation.to_action()
    assert action is not None
    assert action.action_type == USE_CONSUMABLE
    assert action.target is temperance
    assert action.cards == []


def test_temperance_below_cap_holds_when_slot_is_free():
    state = _state([BalatroCard("2", "Hearts")])
    temperance = Temperance()
    state.jokers = [SimpleNamespace(sell_cost=12), SimpleNamespace(sell_cost=8)]
    state.consumables = [temperance]
    state.consumable_slots = 2

    recommendation = LiveConsumableTimingPolicy().recommend(state, temperance)

    assert recommendation.decision == HOLD
    assert recommendation.immediate_gain == 20.0
    assert recommendation.to_action() is None
    assert any("below its $50 cap" in note for note in recommendation.rationale)


def test_temperance_legacy_sell_value_fallback_remains_supported():
    state = _state([BalatroCard("2", "Hearts")])
    temperance = Temperance()
    state.jokers = [SimpleNamespace(sell_value=50)]
    state.consumables = [temperance]

    recommendation = LiveConsumableTimingPolicy().recommend(state, temperance)

    assert recommendation.decision == USE
    assert recommendation.immediate_gain == 50.0


def test_other_unsupported_no_target_consumable_stays_fail_closed():
    state = _state([BalatroCard("2", "Hearts"), BalatroCard("3", "Clubs")])
    high_priestess = HighPriestess()
    state.consumables = [high_priestess]

    recommendation = LiveConsumableTimingPolicy().recommend(state, high_priestess)

    assert recommendation.decision == HOLD
    assert recommendation.target is None
    assert recommendation.to_action() is None
    assert any("no supported deterministic" in note for note in recommendation.rationale)


def test_timing_simulation_does_not_mutate_live_state():
    first = BalatroCard("2", "Hearts")
    second = BalatroCard("3", "Clubs")
    state = _state([first, second], hands_remaining=1)
    strength = Strength()
    state.consumables = [strength]
    before_hand = [(card.rank, card.suit, card.enhancement) for card in state.hand]
    before_consumables = list(state.consumables)

    recommendation = LiveConsumableTimingPolicy().recommend(state, strength)

    assert recommendation.decision == USE
    assert [(card.rank, card.suit, card.enhancement) for card in state.hand] == before_hand
    assert state.consumables == before_consumables
    assert state.consumables[0] is strength


def test_economy_timing_does_not_mutate_live_money_or_inventory():
    state = _state([BalatroCard("2", "Hearts")])
    hermit = Hermit()
    state.money = 10
    state.consumables = [hermit]

    recommendation = LiveConsumableTimingPolicy().recommend(state, hermit)

    assert recommendation.decision == USE
    assert state.money == 10
    assert state.consumables == [hermit]
