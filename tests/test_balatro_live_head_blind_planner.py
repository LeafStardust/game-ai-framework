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


def test_head_wild_cards_are_debuffed_by_suit_boss():
    scorer = HeadScorer()
    wild_club = BalatroCard("10", "Clubs", enhancement="Wild")

    assert scorer.is_card_debuffed(wild_club) is True


def test_head_card_locator_retries_dimmer_profiles_until_save_count_matches(monkeypatch):
    calls = []
    seven = [object() for _ in range(7)]
    eight = [object() for _ in range(8)]

    def fake_locate(region, *, min_brightness, max_channel_spread):
        calls.append((min_brightness, max_channel_spread))
        return seven if len(calls) == 1 else eight

    monkeypatch.setattr(head_live, "locate_card_faces", fake_locate)
    locator = head_live._head_card_locator(8)

    assert locator(object()) is eight
    assert calls == [
        head_live.HEAD_CARD_LOCATOR_PROFILES[0],
        head_live.HEAD_CARD_LOCATOR_PROFILES[1],
    ]


def test_head_card_locator_fails_closed_when_no_profile_matches(monkeypatch):
    seven = [object() for _ in range(7)]

    def fake_locate(region, *, min_brightness, max_channel_spread):
        return seven

    monkeypatch.setattr(head_live, "locate_card_faces", fake_locate)
    locator = head_live._head_card_locator(8)

    # Returning the first failed profile preserves the generic executor's strict
    # count-mismatch abort instead of fabricating or inferring a missing card.
    assert locator(object()) is seven


def test_head_planner_refuses_other_bosses():
    state = _head_state()
    state.boss_name = "The Goad"

    with pytest.raises(ValueError, match="Head planner requires The Head"):
        HeadBlindClearPlanner(horizon=1).plan(state)
