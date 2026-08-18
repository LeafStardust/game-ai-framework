import pytest

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.baseball_card import BaseballCardJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.live.boss_blind_integration import (
    BossAwareCardSelector,
    BossAwareLiveHandDecisionEvaluator,
    boss_blind_planning_rule,
    boss_play_action_is_legal,
)
from games.balatro.live.cerulean_bell import CeruleanBellHandDecisionEvaluator
from games.balatro.live.crimson_heart import CrimsonHeartHandDecisionEvaluator
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.finisher_state_translator import (
    FinisherAwareBalatroStateTranslator,
)
from games.balatro.live.verdant_leaf import VerdantLeafSalePolicy
from games.balatro.state import BalatroState


def _state(boss_name: str, cards, jokers=()):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.blind = Blind(BlindType.BOSS, 1_000)
    state.boss_name = boss_name
    state.hand = list(cards)
    state.owned_deck = list(cards)
    state.deck = []
    state.jokers = list(jokers)
    state.hands_remaining = 4
    state.discards_remaining = 3
    state.discards_used = 0
    state.hand_size = len(cards)
    return state


def test_finisher_registry_exposes_all_four_remaining_bosses():
    ace = BalatroCard("A", "Spades")
    for name in ("Amber Acorn", "Verdant Leaf", "Crimson Heart", "Cerulean Bell"):
        rule = boss_blind_planning_rule(_state(name, [ace]))
        assert rule is not None
        assert rule.boss_name == name

    assert isinstance(
        BossAwareLiveHandDecisionEvaluator().evaluator_for_state(
            _state("Crimson Heart", [ace])
        ),
        CrimsonHeartHandDecisionEvaluator,
    )
    assert isinstance(
        BossAwareLiveHandDecisionEvaluator().evaluator_for_state(
            _state("Cerulean Bell", [ace])
        ),
        CeruleanBellHandDecisionEvaluator,
    )


def test_finisher_translator_hydrates_forced_card_and_disabled_joker():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "money": 0,
            "hand": {
                "limit": 2,
                "cards": [
                    {
                        "value": {"rank": "A", "suit": "S"},
                        "live_id": 10,
                        "forced_selection": False,
                    },
                    {
                        "value": {"rank": "K", "suit": "H"},
                        "live_id": 11,
                        "forced_selection": True,
                    },
                ],
            },
            "cards": {"limit": 0, "cards": []},
            "jokers": {
                "limit": 5,
                "cards": [
                    {
                        "label": "Joker",
                        "center": "j_joker",
                        "live_id": 20,
                        "debuff": True,
                    }
                ],
            },
            "consumables": {"limit": 2, "cards": []},
            "blind": {
                "type": "BOSS",
                "name": "Cerulean Bell",
                "score": 1000,
            },
        },
    )

    state = FinisherAwareBalatroStateTranslator().translate(snapshot)

    assert [card.forced_selection for card in state.hand] == [False, True]
    assert len(state.jokers) == 1
    assert state.jokers[0].debuffed is True


def test_cerulean_bell_requires_forced_card_in_play_and_discard_actions():
    ace = BalatroCard("A", "Spades", live_id=1)
    king = BalatroCard("K", "Hearts", live_id=2, forced_selection=True)
    queen = BalatroCard("Q", "Clubs", live_id=3)
    state = _state("Cerulean Bell", [ace, king, queen])

    selector = BossAwareCardSelector()
    plays = selector.generate_play_actions(state)
    discards = selector.generate_discard_actions(state)

    assert plays and discards
    assert all(king in action.cards for action in plays)
    assert all(king in action.cards for action in discards)
    assert boss_play_action_is_legal(
        state,
        BalatroAction(PLAY_CARDS, cards=[ace]),
    ) is False
    assert boss_play_action_is_legal(
        state,
        BalatroAction(DISCARD_CARDS, cards=[king]),
    ) is True


def test_cerulean_future_without_observed_forced_card_is_marked_inexact():
    ace = BalatroCard("A", "Spades")
    state = _state("Cerulean Bell", [ace])
    evaluator = CeruleanBellHandDecisionEvaluator()

    projection = evaluator.project_play(
        state,
        BalatroAction(PLAY_CARDS, cards=[ace]),
    )

    assert projection.joker_projection_complete is False
    assert "BossBlind:Cerulean Bell future forced selection" in projection.unsupported_jokers


def test_crimson_heart_disables_current_joker_effect_and_rotates_exactly():
    ace = BalatroCard("A", "Spades", live_id=1)
    disabled = FlatMultJoker(4)
    disabled.debuffed = True
    active = FlatMultJoker(10)
    active.debuffed = False
    state = _state("Crimson Heart", [ace], [disabled, active])

    transition = CrimsonHeartHandDecisionEvaluator().score_outcomes.project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    # High Card: 5 base + 11 Ace = 16 chips. Only the active +10 Mult Joker
    # applies, giving 16 * 11 = 176. With two Jokers Crimson cannot choose the
    # previously disabled one again, so the next disabled Joker is deterministic.
    assert transition.distribution.minimum == 176
    assert transition.distribution.maximum == 176
    assert len(transition.distribution.outcomes) == 1
    branch = transition.distribution.outcomes[0].state_after_scoring
    assert [joker.debuffed for joker in branch.jokers] == [False, True]
    assert disabled.debuffed is True
    assert active.debuffed is False


def test_crimson_heart_branches_next_joker_without_sampling_hidden_rng():
    ace = BalatroCard("A", "Spades", live_id=1)
    first = FlatMultJoker(1)
    first.debuffed = True
    second = FlatMultJoker(2)
    third = FlatMultJoker(3)
    state = _state("Crimson Heart", [ace], [first, second, third])

    transition = CrimsonHeartHandDecisionEvaluator().score_outcomes.project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert len(transition.distribution.outcomes) == 2
    assert all(
        outcome.probability == pytest.approx(0.5)
        for outcome in transition.distribution.outcomes
    )
    disabled_indices = {
        tuple(
            index
            for index, joker in enumerate(outcome.state_after_scoring.jokers)
            if joker.debuffed
        )
        for outcome in transition.distribution.outcomes
    }
    assert disabled_indices == {(1,), (2,)}
    assert "Crimson Heart next disabled Joker" in transition.distribution.random_sources


def test_crimson_baseball_still_reads_debuffed_uncommon_rarity():
    ace = BalatroCard("A", "Spades", live_id=1)
    bull = BullJoker()
    bull.rarity = "UNCOMMON"
    bull.debuffed = True
    baseball = BaseballCardJoker()
    baseball.debuffed = False
    state = _state("Crimson Heart", [ace], [bull, baseball])
    state.money = 100

    transition = CrimsonHeartHandDecisionEvaluator().score_outcomes.project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    # Bull itself is disabled (no +200 chips), but active Baseball Card still sees
    # the debuffed Joker's Uncommon rarity and supplies X1.5: int(16 * 1.5) = 24.
    assert transition.distribution.minimum == 24


def test_verdant_leaf_uses_authoritative_card_debuff_state():
    ace = BalatroCard("A", "Spades", debuffed=True)
    state = _state("Verdant Leaf", [ace])
    projection = BossAwareLiveHandDecisionEvaluator().project_play(
        state,
        BalatroAction(PLAY_CARDS, cards=[ace]),
    )

    # Debuffed Ace contributes no card chips; only Level-1 High Card base remains.
    assert projection.hand_score == 5


def test_verdant_leaf_sells_lowest_value_non_eternal_joker_to_lift_debuff():
    ace = BalatroCard("A", "Spades", debuffed=True)
    eternal_weak = FlatMultJoker(0)
    eternal_weak.eternal = True
    weak = FlatMultJoker(1)
    weak.label = "Weak Joker"
    strong = FlatMultJoker(20)
    strong.label = "Strong Joker"
    state = _state("Verdant Leaf", [ace], [eternal_weak, weak, strong])

    decision = VerdantLeafSalePolicy().recommend(state)

    assert decision is not None
    assert decision.joker_index == 1
    assert decision.joker == "Weak Joker"
    assert decision.to_action().name == "SELL_JOKER"
    assert decision.to_action().target["area_index"] == 1


def test_verdant_leaf_sale_policy_is_inert_after_debuff_lifts():
    ace = BalatroCard("A", "Spades", debuffed=False)
    state = _state("Verdant Leaf", [ace], [FlatMultJoker(1)])

    assert VerdantLeafSalePolicy().recommend(state) is None


def test_chicot_suppresses_finisher_rule_constraints():
    ace = BalatroCard("A", "Spades", forced_selection=True)
    king = BalatroCard("K", "Hearts")
    state = _state("Cerulean Bell", [ace, king], [ChicotJoker()])

    assert boss_blind_planning_rule(state) is None
    assert boss_play_action_is_legal(
        state,
        BalatroAction(PLAY_CARDS, cards=[king]),
    ) is True
