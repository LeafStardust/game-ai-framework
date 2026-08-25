from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, REORDER_HAND, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.hand_order_policy import HandOrderPolicy
from games.balatro.joker_policy import (
    BUY,
    HOLD,
    JokerAcquisitionDecision,
    JokerAcquisitionThresholds,
)
from games.balatro.jokers.constellation import ConstellationJoker
from games.balatro.live.planet_policy import LivePlanetPolicy, USE
from games.balatro.live.runtime import live_memory_autonomous_step_injected as runtime_module
from games.balatro.live.runtime.live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
)
from games.balatro.planet_pack_fallback_policy import _celestial_headroom
from games.balatro.planets import create_planet
from games.balatro.playbook.red_white import joker_policy as red_white_joker_policy
from games.balatro.shop_consumable_policy import (
    BUY_AND_USE,
    ConsumableAcquisitionPolicy,
)


class HangingChadJoker:
    pass


class _FlatProjectionEvaluator:
    def __init__(self):
        self.calls = 0

    def project_play(self, state, action):
        self.calls += 1
        return SimpleNamespace(
            clear_probability=0.0,
            hand_score=100,
            expected_hand_score=100.0,
            maximum_hand_score=100,
        )


def test_hand_order_prefers_live_first_and_searches_only_first_card_candidates():
    cards = [
        BalatroCard("A", "Spades", debuffed=True),
        BalatroCard("K", "Hearts"),
        BalatroCard("Q", "Clubs"),
        BalatroCard("J", "Diamonds"),
        BalatroCard("10", "Spades"),
    ]
    state = SimpleNamespace(
        phase="SELECTING_HAND",
        hand=cards,
        jokers=[HangingChadJoker()],
    )
    evaluator = _FlatProjectionEvaluator()

    decision = HandOrderPolicy().recommend(
        state,
        BalatroAction(PLAY_CARDS, cards=cards),
        evaluator=evaluator,
    )

    assert decision is not None
    assert evaluator.calls == len(cards)
    assert decision.permutation[0] != 0
    assert not cards[decision.permutation[0]].debuffed


def test_live_runtime_executes_hand_order_override(monkeypatch):
    cards = [BalatroCard("A", "Spades"), BalatroCard("K", "Hearts")]
    play_action = BalatroAction(PLAY_CARDS, cards=cards)

    fake_playbook = SimpleNamespace(
        name="red-white",
        version="test",
        strategy={
            "decision_thresholds": {"hand_action": {}},
            "planner": {
                "max_horizon": 1,
                "max_search_nodes": 1,
                "max_search_seconds": 0.1,
                "search_schedule_mode": "full",
            },
        },
    )
    monkeypatch.setattr(
        runtime_module,
        "default_balatro_playbooks",
        lambda: SimpleNamespace(for_state=lambda state: fake_playbook),
    )

    class FakeEngine:
        def __init__(self, **kwargs):
            pass

        def rank_plans(self, state, *, planner=None):
            return ()

        def decide(self, state):
            return SimpleNamespace(
                action=play_action,
                mode="TEST",
                confidence=1.0,
                selected_plan=SimpleNamespace(
                    value=SimpleNamespace(clear_probability=1.0),
                    exact=True,
                ),
                selected_pace_ratio=None,
                search_attempts=(),
            )

    monkeypatch.setattr(runtime_module, "LiveHandActionDecisionEngine", FakeEngine)

    reordered = BalatroAction(REORDER_HAND, target=(1, 0))

    class FakeOrderDecision:
        permutation = (1, 0)
        rationale = ("test hand-order override",)

        def to_action(self):
            return reordered

    class FakeOrderPolicy:
        def __init__(self):
            self.calls = 0

        def recommend(self, state, action):
            self.calls += 1
            assert action is play_action
            return FakeOrderDecision()

    runner = object.__new__(LiveMemoryInjectedSingleStepRunner)
    runner.max_horizon = None
    runner.max_search_nodes = None
    runner.exact_limit = 8
    runner.child_exact_limit = 4
    runner.hand_order_policy = FakeOrderPolicy()
    state = SimpleNamespace(phase="SELECTING_HAND", hand=cards)

    action, notes = runner._recommend_hand(state, None)

    assert action.name == REORDER_HAND
    assert action.target == (1, 0)
    assert runner.hand_order_policy.calls == 1
    assert "execution_override=REORDER_HAND" in notes


class _NoProjectionEvaluator:
    class _Generator:
        def generate_play_actions(self, state):
            raise AssertionError("Planet scaler fast path must not enumerate hand plays")

    action_generator = _Generator()

    def project_play(self, state, action):
        raise AssertionError("Planet scaler fast path must not project hand score")


def _planet_state(*, phase, money=10):
    planet = create_planet("MERCURY")
    return planet, SimpleNamespace(
        phase=phase,
        money=money,
        consumables=[planet] if phase == "SELECTING_HAND" else [],
        consumable_slots=2,
        jokers=[ConstellationJoker()],
        hand_levels={"PAIR": 1},
        hand_play_counts={"PAIR": 0},
        hands_remaining=4,
        score=0,
        blind=SimpleNamespace(requirement=300),
    )


def test_d7_planet_scaler_uses_planet_without_score_projection():
    planet, state = _planet_state(phase="SELECTING_HAND")

    decision = LivePlanetPolicy(hand_evaluator=_NoProjectionEvaluator()).recommend(
        state,
        planet,
    )

    assert decision.decision == USE
    assert decision.level_gain == 1
    assert decision.before_projection is None
    assert decision.after_projection is None
    assert any("Planet-use scaler" in note for note in decision.rationale)


class _ZeroConsumableEvaluator:
    def evaluate(self, candidate, state):
        return SimpleNamespace(total_gain=0.0, rationale=())


def test_d4_planet_scaler_forces_reserve_safe_buy_and_use():
    planet, state = _planet_state(phase="SHOP", money=10)
    decision = ConsumableAcquisitionPolicy(
        evaluator=_ZeroConsumableEvaluator(),
    ).decide(state, planet)

    assert decision.action == BUY_AND_USE
    assert decision.selected is not None
    assert decision.selected.economics.money_after >= decision.thresholds.reserve_target


def test_d4_planet_scaler_does_not_break_reserve():
    planet, state = _planet_state(phase="SHOP", money=7)
    decision = ConsumableAcquisitionPolicy(
        evaluator=_ZeroConsumableEvaluator(),
    ).decide(state, planet)

    assert decision.action != BUY_AND_USE


def test_planet_scaler_bypasses_generic_celestial_hand_headroom():
    _, state = _planet_state(phase="SHOP", money=10)
    state.hand_play_counts = {}
    state.hand_levels = {"PAIR": 1}

    headroom, notes = _celestial_headroom(state)

    assert headroom > 0
    assert any("Planet-use scaler" in note for note in notes)


def test_red_white_d2_vetoes_new_canonical_conflict(monkeypatch):
    candidate = SimpleNamespace(name="Ride the Bus")
    state = SimpleNamespace(jokers=[SimpleNamespace(name="Scary Face")])

    class FakeCorePolicy:
        def __init__(self, *args, **kwargs):
            pass

        def decide(self, state, candidate):
            return JokerAcquisitionDecision(
                action=BUY,
                candidate="Ride the Bus",
                selected=None,
                options=(),
                thresholds=JokerAcquisitionThresholds(),
                rationale=("core D2 would buy",),
            )

    monkeypatch.setattr(red_white_joker_policy, "JokerAcquisitionPolicy", FakeCorePolicy)
    monkeypatch.setattr(
        red_white_joker_policy,
        "default_balatro_playbooks",
        lambda: SimpleNamespace(
            for_state=lambda state: SimpleNamespace(thresholds_for=lambda layer: {})
        ),
    )

    def fake_evaluate(projected_state):
        conflicts = ()
        if len(projected_state.jokers) > 1:
            conflicts = (("face_cards", "no_face_cards"),)
        return (), SimpleNamespace(conflicts=conflicts)

    monkeypatch.setattr(red_white_joker_policy, "evaluate_bond_composition", fake_evaluate)

    decision = red_white_joker_policy.PlaybookJokerAcquisitionPolicy(
        transition_planner=SimpleNamespace(),
    ).decide(state, candidate)

    assert decision.action == HOLD
    assert decision.selected is None
    assert any("canonical Bond conflict veto" in note for note in decision.rationale)
