from __future__ import annotations

from types import SimpleNamespace

from games.balatro.actions import (
    DISCARD_CARDS,
    PLAY_CARDS,
    SELECT_PACK_CARD,
    SKIP_BOOSTER,
    BalatroAction,
)
from games.balatro.card import BalatroCard
from games.balatro.five_run_followup_policy import (
    _realized_joker_weakness,
    _roster_pressure,
    _should_force_roster_reroll,
)
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


class GoldenJoker:
    pass


class AbstractJoker:
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


class _RecoveryEvaluator:
    def project_play(self, state, action):
        return SimpleNamespace(expected_hand_score=80.0)

    def evaluate(self, state, action):
        if action.name == DISCARD_CARDS:
            return 100.0
        return 80.0


def _plan(
    action,
    expected_score,
    *,
    expected_progress=0.0,
    clear_probability=0.0,
):
    return LiveBlindPlan(
        action=action,
        value=LiveBlindPlanValue(
            clear_probability=float(clear_probability),
            expected_progress=float(expected_progress),
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

    # Give the debuffed line stronger planner progress so ordinary D1 selects it
    # before the suit-boss follow-up correction runs. Both plays still satisfy the
    # 100-chip pace target; the regression is specifically that the wrapper must
    # replace the otherwise-preferred all-debuffed play with the active alternative.
    plans = [
        _plan(bad_action, 200, expected_progress=1.0),
        _plan(good_action, 150, expected_progress=0.0),
    ]

    decision = LiveHandActionPolicy(evaluator=_Evaluator()).decide(state, plans)

    assert decision.action is good_action
    assert decision.selected_immediate_score == 150.0
    assert any("visibly debuffed cards" in note for note in decision.rationale)


def test_realized_scaler_strength_reduces_weak_roster_pressure() -> None:
    cold = SimpleNamespace(name="Red Card", public_state={"mult": 0})
    online = SimpleNamespace(name="Red Card", public_state={"mult": 20})

    assert _realized_joker_weakness(cold) == 1.0
    assert _realized_joker_weakness(online) == 0.0


def test_cash_rich_full_weak_roster_forces_one_upgrade_search_window() -> None:
    state = BalatroState()
    state.phase = "SHOP"
    state.ante = 5
    state.round_num = 11
    state.money = 30
    state.joker_slots = 5
    state.jokers = [
        BannerJoker(),
        GoldenJoker(),
        SimpleNamespace(name="Red Card", public_state={"mult": 0}),
        AbstractJoker(),
        AbstractJoker(),
    ]

    assert _roster_pressure(state) >= 2.0
    assert _should_force_roster_reroll(state, reroll_cost=5)

    state.money = 24
    assert not _should_force_roster_reroll(state, reroll_cost=5)


def test_final_discard_is_preserved_when_recovery_gain_is_small() -> None:
    state = BalatroState()
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 1
    state.blind = SimpleNamespace(requirement=400)

    play_action = BalatroAction(
        PLAY_CARDS,
        cards=[BalatroCard("A", "Hearts")],
    )
    discard_action = BalatroAction(
        DISCARD_CARDS,
        cards=[BalatroCard("2", "Clubs")],
    )
    plans = [
        _plan(play_action, 80),
        _plan(discard_action, 90),
    ]

    decision = LiveHandActionPolicy(evaluator=_RecoveryEvaluator()).decide(state, plans)

    assert decision.action is play_action
    assert any("preserve the final discard" in note for note in decision.rationale)
