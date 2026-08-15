import pytest

from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.bootstraps import BootstrapsJoker
from games.balatro.jokers.ice_cream import IceCreamJoker
from games.balatro.live.external import head_blind_planner_action_live_validation as head_live
from games.balatro.live.head_blind_planner import (
    HeadBlindClearPlanner,
    HeadHandDecisionEvaluator,
    HeadScorer,
)
from games.balatro.state import BalatroState


def _head_state() -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.score = 0
    state.money = 20
    state.hands_remaining = 4
    state.discards_remaining = 4
    state.blind = Blind(BlindType.BOSS, 1600)
    state.boss_name = "The Head"
    state.hand = [
        BalatroCard("K", "Diamonds", live_id=0),
        BalatroCard("Q", "Diamonds", live_id=1),
        BalatroCard("J", "Hearts", live_id=2),
        BalatroCard("10", "Spades", live_id=3),
        BalatroCard("8", "Clubs", live_id=4),
        BalatroCard("6", "Clubs", live_id=5),
        BalatroCard("2", "Hearts", live_id=6),
        BalatroCard("2", "Clubs", live_id=7),
    ]
    state.deck = [
        BalatroCard(str((index % 9) + 2), "Spades")
        for index in range(20)
    ]
    ice_cream = IceCreamJoker()
    ice_cream.chips = 70
    state.jokers = [ice_cream, BootstrapsJoker()]
    return state


def test_head_debuffed_high_card_still_defines_hand_but_scores_no_card_chips():
    scorer = HeadScorer()
    state = BalatroState()
    cards = [
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Clubs"),
    ]

    score = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        cards=cards,
        include_card_chips=True,
        resolve_random_effects=False,
    )

    # The K of Hearts still defines High Card K. Because it is debuffed, it adds
    # zero rank chips; the lower Q must not be substituted as the scoring card.
    assert score.chips == 5
    assert score.mult == 1
    assert score.total == 5


def test_head_pair_scores_only_the_non_debuffed_member_with_live_jokers():
    state = _head_state()
    evaluator = HeadHandDecisionEvaluator()
    cards = [state.hand[6], state.hand[7]]
    action = BalatroAction(PLAY_CARDS, cards=cards)

    projection = evaluator.project_play(state, action)

    # Pair base 10 chips + only the 2 of Clubs + Ice Cream 70 = 82 chips.
    # Pair base 2 mult + Bootstraps at $20 (+8 mult) = 10 mult.
    assert projection.hand == PokerHand.PAIR
    assert projection.hand_score == 820
    assert projection.expected_hand_score == 820.0
    assert projection.outcomes[0].score == 820
    assert state.jokers[0].chips == 70


def test_head_d1_prefers_live_scoring_card_over_boss_debuffed_higher_rank():
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.score = 0
    state.money = 0
    state.hands_remaining = 1
    state.discards_remaining = 0
    state.blind = Blind(BlindType.BOSS, 15)
    state.boss_name = "The Head"
    ace = BalatroCard("A", "Hearts", live_id=0)
    king = BalatroCard("K", "Clubs", live_id=1)
    state.hand = [ace, king]
    state.deck = []

    plan = HeadBlindClearPlanner(horizon=1, play_width=3).plan(state)

    # Treating the disabled Ace as an ordinary card would make it look stronger.
    # The correct D1 projection values it at only the 5-chip High Card base, so
    # the live King is the only candidate that actually clears the 15-chip boss.
    assert plan.action.name == PLAY_CARDS
    assert plan.action.cards == [king]
    assert plan.value.clear_probability == 1.0
    assert plan.value.expected_score == 15.0


def test_head_wild_cards_are_debuffed_by_suit_boss():
    scorer = HeadScorer()
    wild_club = BalatroCard("10", "Clubs", enhancement="Wild")

    assert scorer.is_card_debuffed(wild_club) is True


def test_head_card_locator_uses_save_backed_expected_count_locator(monkeypatch):
    calls = []
    eight = [object() for _ in range(8)]
    region = object()

    def fake_locate(value, expected_count):
        calls.append((value, expected_count))
        return eight

    monkeypatch.setattr(head_live, "locate_card_faces_expected_count", fake_locate)
    monkeypatch.setattr(head_live, "_locations_form_uniform_grid", lambda locations: True)
    locator = head_live._head_card_locator(8)

    assert locator(region) is eight
    assert calls == [(region, 8)]


def test_head_card_locator_fails_closed_when_expected_count_locator_misses(monkeypatch):
    seven = [object() for _ in range(7)]

    def fake_locate(region, expected_count):
        assert expected_count == 8
        return seven

    monkeypatch.setattr(head_live, "locate_card_faces_expected_count", fake_locate)
    locator = head_live._head_card_locator(8)

    # A count mismatch remains visible to the generic executor's strict abort path;
    # the wrapper never fabricates or infers a missing card.
    assert locator(object()) is seven


def test_head_planner_refuses_other_bosses():
    state = _head_state()
    state.boss_name = "The Goad"

    with pytest.raises(ValueError, match="Head planner requires The Head"):
        HeadBlindClearPlanner(horizon=1).plan(state)
