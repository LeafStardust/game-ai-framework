from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, USE_CONSUMABLE, BalatroAction
from games.balatro.build import ContextualConsumableTargetEvaluator
from games.balatro.card import BalatroCard
from games.balatro.live.consumable_timing import LiveConsumableTimingPolicy
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState
from games.balatro.tarots import Death


class _Blind:
    def __init__(self, requirement: int = 100_000):
        self.requirement = requirement

    def copy(self):
        return _Blind(self.requirement)


class _Estimator:
    def estimate(self, state, action):
        return 1.0, ("fixture consumable value",)


def _state(cards, *, phase="SELECTING_HAND"):
    state = BalatroState()
    state.phase = phase
    state.hand = list(cards)
    state.deck = [
        BalatroCard(
            card.rank,
            card.suit,
            card.enhancement,
            card.edition,
            card.seal,
        )
        for card in cards
    ]
    state.blind = _Blind()
    return state


def _death_choice():
    return LivePackChoice(
        area_index=0,
        address=0x1000,
        data={
            "area_index": 0,
            "address": 0x1000,
            "live_id": 501,
            "label": "Death",
            "ability_name": "Death",
            "ability_set": "Tarot",
        },
    )


def test_death_prefers_copying_stronger_right_card_into_weaker_left_card():
    two = BalatroCard("2", "Hearts")
    king = BalatroCard("K", "Clubs")
    three = BalatroCard("3", "Diamonds")
    state = _state([two, king, three])
    evaluator = ContextualConsumableTargetEvaluator()

    ranked = evaluator.rank_targets(state, Death())

    assert evaluator.supports(Death())
    assert ranked
    assert ranked[0].target_indices == (0, 1)
    assert ranked[0].cards == (two, king)
    assert ranked[0].intrinsic_delta > 0.0
    assert ranked[0].total_gain > 0.0
    assert any(
        "Death directional copy: hand index 0 becomes hand index 1" in note
        for note in ranked[0].rationale
    )


def test_death_direction_is_not_silently_reversed_when_copy_is_harmful():
    king = BalatroCard("K", "Clubs")
    two = BalatroCard("2", "Hearts")
    state = _state([king, two])

    recommendation = ContextualConsumableTargetEvaluator().recommend(state, Death())

    assert recommendation is not None
    assert recommendation.target_indices == (0, 1)
    assert recommendation.intrinsic_delta < 0.0
    assert recommendation.total_gain < 0.0


def test_death_pack_choice_uses_exact_positive_directional_target():
    two = BalatroCard("2", "Hearts")
    king = BalatroCard("K", "Clubs")
    state = _state([two, king], phase="TAROT_PACK")
    choice = _death_choice()

    ranked = BalatroPackPolicy(
        item_estimator=_Estimator(),
        skip_bias=0.35,
    ).rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=choice),
            BalatroAction(SKIP_BOOSTER),
        ],
    )

    selected = ranked[0]
    assert selected.action.name == SELECT_PACK_CARD
    assert selected.action.target is choice
    assert selected.action.cards == [two, king]
    assert any("intrinsic copy delta=" in note for note in selected.notes)


def test_death_pack_choice_fails_closed_when_only_direction_is_negative():
    king = BalatroCard("K", "Clubs")
    two = BalatroCard("2", "Hearts")
    state = _state([king, two], phase="TAROT_PACK")
    choice = _death_choice()

    ranked = BalatroPackPolicy(
        item_estimator=_Estimator(),
        skip_bias=0.35,
    ).rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=choice),
            BalatroAction(SKIP_BOOSTER),
        ],
    )

    assert ranked[0].action.name == SKIP_BOOSTER
    death = next(result for result in ranked if result.action.name == SELECT_PACK_CARD)
    assert death.total == -1.0
    assert death.action.cards == []


def test_final_hand_death_use_can_preempt_d1_with_exact_directional_target():
    two = BalatroCard("2", "Hearts")
    king = BalatroCard("K", "Clubs")
    state = _state([two, king])
    state.hands_remaining = 1
    death = Death()
    state.consumables = [death]

    recommendation = LiveConsumableTimingPolicy().recommend(state, death)

    assert recommendation.should_use
    assert recommendation.target is not None
    assert recommendation.target.target_indices == (0, 1)
    assert recommendation.after_projection is not None
    assert (
        recommendation.after_projection.expected_hand_score
        > recommendation.before_projection.expected_hand_score
    )

    action = recommendation.to_action()
    assert action is not None
    assert action.action_type == USE_CONSUMABLE
    assert action.target is death
    assert action.cards == [two, king]


def test_death_target_simulation_does_not_mutate_authoritative_cards():
    two = BalatroCard("2", "Hearts", enhancement="Lucky")
    king = BalatroCard("K", "Clubs", enhancement="Steel")
    state = _state([two, king])
    before = [
        (card.rank, card.suit, card.enhancement, card.edition, card.seal)
        for card in state.hand
    ]

    ContextualConsumableTargetEvaluator().rank_targets(state, Death())

    assert [
        (card.rank, card.suit, card.enhancement, card.edition, card.seal)
        for card in state.hand
    ] == before
