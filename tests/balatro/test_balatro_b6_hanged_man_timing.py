from games.balatro.actions import USE_CONSUMABLE
from games.balatro.card import BalatroCard
from games.balatro.live.consumable_timing import HOLD, USE, LiveConsumableTimingPolicy
from games.balatro.state import BalatroState
from games.balatro.tarots import HangedMan


class _Blind:
    def __init__(self, requirement: int):
        self.requirement = requirement

    def copy(self):
        return _Blind(self.requirement)


def _card(rank, suit, live_id, *, enhancement=None, edition=None, seal=None):
    return BalatroCard(
        rank,
        suit,
        enhancement=enhancement,
        edition=edition,
        seal=seal,
        live_id=live_id,
    )


def _owned_copy(card: BalatroCard) -> BalatroCard:
    return BalatroCard(
        card.rank,
        card.suit,
        enhancement=card.enhancement,
        edition=card.edition,
        seal=card.seal,
        live_id=card.live_id,
    )


def _state(hand):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(hand)
    state.deck = []
    state.owned_deck = [_owned_copy(card) for card in hand]
    state.hands_remaining = 4
    state.score = 0
    state.blind = _Blind(100_000)
    return state


def test_held_hanged_man_uses_two_independently_positive_thinning_targets():
    two = _card("2", "Hearts", 101)
    three = _card("3", "Clubs", 102)
    ace = _card("A", "Spades", 103)
    seven = _card("7", "Diamonds", 104)
    nine = _card("9", "Hearts", 105)
    state = _state([two, three, ace, seven, nine])
    state.owned_deck.extend(
        [
            _card("K", "Diamonds", 201),
            _card("Q", "Hearts", 202),
            _card("10", "Spades", 203),
            _card("J", "Clubs", 204),
        ]
    )
    hanged = HangedMan()
    state.consumables = [hanged]
    state.consumable_slots = 2

    recommendation = LiveConsumableTimingPolicy().recommend(state, hanged)

    assert recommendation.decision == USE
    assert recommendation.target is not None
    assert recommendation.target.target_indices == (0, 1)
    assert recommendation.target.cards == (two, three)
    assert recommendation.target.total_gain > 0.0
    assert recommendation.after_projection is not None
    assert (
        recommendation.after_projection.expected_hand_score
        >= recommendation.before_projection.expected_hand_score
    )
    assert any(
        "two independently positive deck-thinning cards" in note
        for note in recommendation.rationale
    )

    action = recommendation.to_action()
    assert action is not None
    assert action.action_type == USE_CONSUMABLE
    assert action.target is hanged
    assert action.cards == [two, three]


def test_held_hanged_man_preserves_single_good_thinning_target_with_free_slot():
    two = _card("2", "Hearts", 101)
    premium_ace = _card("A", "Spades", 102, edition="Polychrome")
    state = _state([two, premium_ace])
    hanged = HangedMan()
    state.consumables = [hanged]
    state.consumable_slots = 2

    recommendation = LiveConsumableTimingPolicy().recommend(state, hanged)

    assert recommendation.decision == HOLD
    assert recommendation.target is not None
    assert recommendation.target.target_indices == (0,)
    assert recommendation.target.total_gain > 0.0
    assert recommendation.to_action() is None
    assert any(
        "no concrete timing advantage" in note
        for note in recommendation.rationale
    )


def test_full_slots_can_use_single_positive_hanged_man_target():
    two = _card("2", "Hearts", 101)
    premium_ace = _card("A", "Spades", 102, edition="Polychrome")
    state = _state([two, premium_ace])
    hanged = HangedMan()
    state.consumables = [hanged]
    state.consumable_slots = 1

    recommendation = LiveConsumableTimingPolicy().recommend(state, hanged)

    assert recommendation.decision == USE
    assert recommendation.target is not None
    assert recommendation.target.target_indices == (0,)
    assert any(
        "full consumable slots" in note
        for note in recommendation.rationale
    )


def test_hanged_man_timing_fails_closed_on_ambiguous_owned_live_id():
    two = _card("2", "Hearts", 101)
    ace = _card("A", "Spades", 102)
    state = _state([two, ace])
    state.owned_deck = [
        _card("2", "Hearts", 101),
        _card("3", "Clubs", 101),
        _card("A", "Spades", 102),
    ]
    hanged = HangedMan()
    state.consumables = [hanged]
    state.consumable_slots = 1

    recommendation = LiveConsumableTimingPolicy().recommend(state, hanged)

    assert recommendation.decision == HOLD
    assert recommendation.target is not None
    assert recommendation.to_action() is None
    assert any(
        "failed consumable can_use during copied simulation" in note
        for note in recommendation.rationale
    )


def test_hanged_man_simulation_removes_exact_owned_ids_without_mutating_live_state():
    two = _card("2", "Hearts", 101)
    three = _card("3", "Clubs", 102)
    ace = _card("A", "Spades", 103)
    state = _state([two, three, ace])
    hanged = HangedMan()
    state.consumables = [hanged]

    before_owned = [card.live_id for card in state.owned_deck]
    transformed = LiveConsumableTimingPolicy()._simulate_use(
        state,
        consumable_index=0,
        target_indices=(0, 1),
    )

    assert transformed is not None
    assert [card.live_id for card in transformed.owned_deck] == [103]
    assert [card.live_id for card in transformed.hand] == [103]
    assert transformed.discard_pile == []
    assert transformed.consumables == []
    assert [card.live_id for card in state.owned_deck] == before_owned
    assert [card.live_id for card in state.hand] == [101, 102, 103]
    assert state.consumables == [hanged]
