from __future__ import annotations

from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import LiveHandActionPolicy
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.state import BalatroState
from games.balatro.strategy import BRONZE, SILVER
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES


class RedCardJoker:
    name = "Red Card"


class BannerJoker:
    pass


class DelayedGratificationJoker:
    pass


class _PackPolicy(BalatroPackPolicy):
    def score_action(self, state, action):
        if action.name == SKIP_BOOSTER:
            return PackActionScore(action, 0.35, ("skip booster",))
        return PackActionScore(action, 50.0, ("valuable visible pack choice",))


class _Evaluator:
    def project_play(self, state, action):
        score = 200.0 if all(card.debuffed for card in action.cards) else 150.0
        return SimpleNamespace(expected_hand_score=score)

    def evaluate(self, state, action):
        return self.project_play(state, action).expected_hand_score


def _plan(action, expected_score):
    return LiveBlindPlan(
        action=action,
        value=LiveBlindPlanValue(
            clear_probability=0.0,
            expected_progress=0.0,
            expected_score=float(expected_score),
            expected_hands_remaining=3.0,
            expected_discards_remaining=3.0,
        ),
        horizon=1,
        exact=True,
        candidate_count=2,
    )


def test_red_card_forces_skip_over_more_valuable_pack_choice() -> None:
    state = BalatroState()
    state.phase = "TAROT_PACK"
    state.jokers = [RedCardJoker()]
    skip = BalatroAction(SKIP_BOOSTER)
    take = BalatroAction(SELECT_PACK_CARD, target=object())

    ranked = _PackPolicy().rank_actions(state, [take, skip])

    assert ranked[0].action.name == SKIP_BOOSTER
    assert any("Red Card owned" in note for note in ranked[0].notes)


def test_banner_is_bronze_but_delayed_gratification_stays_silver() -> None:
    definition = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["no_discard_reserve"]
    assert definition.relationship_for(BannerJoker(), kind="JOKER") == BRONZE
    assert definition.relationship_for(DelayedGratificationJoker(), kind="JOKER") == SILVER


def test_pace_play_avoids_all_debuffed_hand_when_active_alternative_meets_pace() -> None:
    state = BalatroState()
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 3
    state.blind = SimpleNamespace(requirement=400)

    debuffed = [BalatroCard(str(rank), "Clubs", debuffed=True) for rank in range(2, 7)]
    active = [BalatroCard("A", "Hearts"), BalatroCard("A", "Diamonds")]
    bad_action = BalatroAction(PLAY_CARDS, cards=debuffed)
    good_action = BalatroAction(PLAY_CARDS, cards=active)
    plans = [_plan(bad_action, 200), _plan(good_action, 150)]

    decision = LiveHandActionPolicy(evaluator=_Evaluator()).decide(state, plans)

    assert decision.action is good_action
    assert decision.selected_immediate_score == 150.0
    assert any("visibly debuffed cards" in note for note in decision.rationale)
