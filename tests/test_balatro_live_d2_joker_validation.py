from games.balatro.joker import Joker, JokerContext
from games.balatro.joker_policy import BUY, HOLD, REPLACE, JokerAcquisitionPolicy
from games.balatro.live.external.live_memory_joker_policy_validation import (
    build_live_d2_view,
    evaluate_shop_jokers,
    select_joker_recommendation,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.state import BalatroState


class InertJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


class PlusMultJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is not None:
            context.score.mult += 40
        return context


def _shop_state(*, slots: int = 5, money: int = 20) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.joker_slots = slots
    state.consumable_slots = 2
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    return state


def _snapshot() -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        phase="SHOP",
        sequence=1,
        payload={},
        state_complete=True,
    )


def test_validator_evaluates_shop_jokers_even_when_joker_slots_are_full():
    state = _shop_state(slots=1)
    state.jokers = [InertJoker()]
    weak = InertJoker()
    strong = PlusMultJoker()
    state.shop_jokers = [weak, strong]

    candidates = evaluate_shop_jokers(state, JokerAcquisitionPolicy())

    assert [candidate.target for candidate in candidates] == [weak, strong]
    assert len(candidates) == 2
    assert any(candidate.decision.action == REPLACE for candidate in candidates)


def test_validator_selects_best_actionable_joker_and_ignores_holds():
    state = _shop_state(slots=2)
    weak = InertJoker()
    strong = PlusMultJoker()
    weak.cost = 5
    strong.cost = 1
    state.shop_jokers = [weak, strong]

    candidates = evaluate_shop_jokers(state, JokerAcquisitionPolicy())
    recommendation = select_joker_recommendation(candidates)

    assert recommendation is not None
    assert recommendation.target is strong
    assert recommendation.decision.action == BUY
    assert any(candidate.decision.action == HOLD for candidate in candidates)


def test_live_d2_view_loads_red_white_threshold_cartridge_without_execution():
    state = _shop_state(slots=2)
    candidate = PlusMultJoker()
    candidate.cost = 1
    candidate.area_index = 0
    state.shop_jokers = [candidate]

    view = build_live_d2_view(_snapshot(), state)

    assert view.playbook_name == "red-white"
    assert view.playbook_version == "0.8"
    assert view.thresholds.minimum_purchase_advantage == 0.35
    assert len(view.candidates) == 1
    assert view.recommendation is not None
    assert view.recommendation.decision.action == BUY


def test_validator_reports_no_recommendation_when_all_candidates_hold():
    state = _shop_state(slots=2)
    candidate = InertJoker()
    candidate.cost = 5
    state.shop_jokers = [candidate]

    candidates = evaluate_shop_jokers(state, JokerAcquisitionPolicy())

    assert candidates[0].decision.action == HOLD
    assert select_joker_recommendation(candidates) is None
