from types import SimpleNamespace

import games.balatro.playbook.red_white.pack_policy as pack_module

from games.balatro.actions import SELL_JOKER, SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.joker_policy import BUY, HOLD, REPLACE
from games.balatro.live.consumable_timing_core import ConsumableTargetThresholds
from games.balatro.live.pack import LivePackActionGenerator, LivePackChoice
from games.balatro.playbook import (
    BalatroPlaybook,
    BalatroPlaybookRegistry,
    default_balatro_playbooks,
)
from games.balatro.playbook_pack_policy import (
    PackChoiceThresholds,
    PlaybookBalatroPackPolicy,
)
from games.balatro.state import BalatroState


class _Estimator:
    def estimate(self, state, action):
        del state, action
        return 1.0, ("fixture item value",)


class _JokerEstimator(_Estimator):
    joker_build_value = object()


class _ConsumableFactory:
    def create(self, data, live_id=None):
        del data, live_id
        return SimpleNamespace(name="The Chariot", category="TAROT")


class _TargetEvaluator:
    def __init__(self, *, total_gain=0.5, contextual_delta=0.25):
        self.total_gain = total_gain
        self.contextual_delta = contextual_delta

    def recommend(self, state, consumable):
        del consumable
        card = state.hand[0]
        return SimpleNamespace(
            total_gain=self.total_gain,
            contextual_delta=self.contextual_delta,
            cards=(card,),
            target_indices=(0,),
            rationale=("fixture B6 target",),
        )


def _state() -> BalatroState:
    state = BalatroState()
    state.phase = "TAROT_PACK"
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    card = SimpleNamespace(rank="4", suit="Clubs")
    state.hand = [card]
    return state


def _choice() -> LivePackChoice:
    return LivePackChoice(
        area_index=0,
        address=0x1234,
        data={
            "ability_set": "Tarot",
            "ability_name": "The Chariot",
            "label": "The Chariot",
            "live_id": 77,
        },
    )


def _buffoon_state(*, full_roster: bool = False) -> BalatroState:
    state = BalatroState()
    state.phase = "BUFFOON_PACK"
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.joker_slots = 5
    state.jokers = (
        [SimpleNamespace(name=f"fixture-{index}") for index in range(5)]
        if full_roster
        else []
    )
    return state


def _buffoon_choice(*, cost: int = 5) -> LivePackChoice:
    return LivePackChoice(
        area_index=0,
        address=0x5678,
        data={
            "ability_set": "Joker",
            "ability_name": "Joker",
            "label": "Joker",
            "center": "j_joker",
            "cost": cost,
            "live_id": 88,
        },
    )


def _registry(*, skip_bias=0.0, minimum_total_gain=None):
    registry = BalatroPlaybookRegistry()
    registry.register(
        BalatroPlaybook(
            deck="RED",
            stake="WHITE",
            name="pack-threshold-regression",
            strategy={
                "decision_thresholds": {
                    "pack_choice": {"skip_bias": skip_bias},
                    "pack_target": {
                        "minimum_total_gain": minimum_total_gain,
                        "minimum_contextual_delta": None,
                    },
                }
            },
        )
    )
    return registry


def _install_fake_d2(monkeypatch, *, action, total_advantage=3.25, replace_index=None):
    observed = {}

    class _FakePolicy:
        def __init__(self, transition_planner):
            observed["transition_planner"] = transition_planner

        def decide(self, state, candidate):
            del state
            observed["candidate"] = candidate
            selected = None
            if action != HOLD:
                selected = SimpleNamespace(
                    total_advantage=total_advantage,
                    replace_index=replace_index,
                    rationale=("fixture D2 option",),
                )
            return SimpleNamespace(
                action=action,
                selected=selected,
                candidate=type(candidate).__name__,
                rationale=("fixture D2 decision",),
            )

    monkeypatch.setattr(pack_module, "PlaybookJokerAcquisitionPolicy", _FakePolicy)
    return observed


def test_red_white_exposes_current_d9_and_d10_thresholds():
    playbook = default_balatro_playbooks().get("RED", "WHITE")

    d9 = PackChoiceThresholds.from_mapping(playbook.thresholds_for("D9"))
    d10 = ConsumableTargetThresholds.from_mapping(playbook.thresholds_for("D10"))

    assert d9 == PackChoiceThresholds(skip_bias=0.0)
    assert d10 == ConsumableTargetThresholds(minimum_contextual_delta=0.0)


def test_d9_skip_bias_resolves_from_active_playbook(monkeypatch):
    monkeypatch.setattr(
        pack_module,
        "default_balatro_playbooks",
        lambda: _registry(skip_bias=9.0),
    )
    state = _state()
    policy = PlaybookBalatroPackPolicy()

    scored = policy.score_action(state, BalatroAction(SKIP_BOOSTER))

    assert scored.total == 9.0
    assert any("D9 skip_bias=9.000" in note for note in scored.notes)


def test_explicit_d9_override_remains_authoritative(monkeypatch):
    monkeypatch.setattr(
        pack_module,
        "default_balatro_playbooks",
        lambda: _registry(skip_bias=9.0),
    )
    state = _state()
    policy = PlaybookBalatroPackPolicy(skip_bias=0.10)

    scored = policy.score_action(state, BalatroAction(SKIP_BOOSTER))

    assert scored.total == 0.10


def test_d10_reuses_d6_target_contract_and_can_reject_positive_below_threshold(
    monkeypatch,
):
    monkeypatch.setattr(
        pack_module,
        "default_balatro_playbooks",
        lambda: _registry(minimum_total_gain=1.0),
    )
    state = _state()
    choice = _choice()
    policy = PlaybookBalatroPackPolicy(
        item_estimator=_Estimator(),
        consumable_factory=_ConsumableFactory(),
        consumable_target_evaluator=_TargetEvaluator(total_gain=0.5),
    )

    scored = policy.score_action(
        state,
        BalatroAction(SELECT_PACK_CARD, target=choice),
    )

    assert scored.total == -1.0
    assert scored.action.target is choice
    assert any("no positive B6 target" in note for note in scored.notes)


def test_d10_neutral_threshold_preserves_literal_positive_target_behavior(
    monkeypatch,
):
    monkeypatch.setattr(
        pack_module,
        "default_balatro_playbooks",
        lambda: _registry(minimum_total_gain=None),
    )
    state = _state()
    choice = _choice()
    policy = PlaybookBalatroPackPolicy(
        item_estimator=_Estimator(),
        consumable_factory=_ConsumableFactory(),
        consumable_target_evaluator=_TargetEvaluator(total_gain=0.5),
    )

    scored = policy.score_action(
        state,
        BalatroAction(SELECT_PACK_CARD, target=choice),
    )

    # Opened-pack acquisition cost is sunk. D9/D10 carries the literal B6 target
    # gain itself; it no longer adds the generic item/category estimator value.
    assert scored.total == 0.5
    assert scored.action.cards == list(state.hand)
    assert any("B6 pack target gain=0.500" in note for note in scored.notes)


def test_d9_open_slot_buffoon_joker_delegates_to_d2_at_zero_cost(monkeypatch):
    observed = _install_fake_d2(monkeypatch, action=BUY, total_advantage=3.25)
    state = _buffoon_state()
    choice = _buffoon_choice(cost=5)
    policy = PlaybookBalatroPackPolicy(item_estimator=_JokerEstimator())

    scored = policy.score_action(
        state,
        BalatroAction(SELECT_PACK_CARD, target=choice),
    )

    assert scored.action.name == SELECT_PACK_CARD
    assert scored.action.target is choice
    assert scored.total == 3.25
    assert getattr(observed["candidate"], "cost", None) == 0
    assert choice.data["cost"] == 5
    assert any("canonical D2 acquisition" in note for note in scored.notes)
    assert any("normalized to $0" in note for note in scored.notes)


def test_d9_full_roster_buffoon_replacement_delegates_to_zero_cost_d2(monkeypatch):
    observed = _install_fake_d2(
        monkeypatch,
        action=REPLACE,
        total_advantage=4.5,
        replace_index=2,
    )
    state = _buffoon_state(full_roster=True)
    choice = _buffoon_choice(cost=6)
    policy = PlaybookBalatroPackPolicy(item_estimator=_JokerEstimator())

    scored = policy.score_action(
        state,
        BalatroAction(SELECT_PACK_CARD, target=choice),
    )

    assert scored.action.name == SELL_JOKER
    assert scored.action.target == 2
    assert scored.total == 4.5
    assert getattr(observed["candidate"], "cost", None) == 0
    assert choice.data["cost"] == 6


def test_d9_buffoon_d2_hold_can_rank_skip_above_visible_joker(monkeypatch):
    _install_fake_d2(monkeypatch, action=HOLD)
    state = _buffoon_state()
    choice = _buffoon_choice()
    policy = PlaybookBalatroPackPolicy(
        item_estimator=_JokerEstimator(),
        skip_bias=0.0,
    )
    actions = [
        BalatroAction(SELECT_PACK_CARD, target=choice),
        BalatroAction(SKIP_BOOSTER),
    ]

    ranked = policy.rank_actions(state, actions)

    assert ranked[0].action.name == SKIP_BOOSTER
    assert ranked[0].total == 0.0
    assert ranked[1].total == -1.0
    assert any(
        "does not clear canonical D2 acquisition" in note
        for note in ranked[1].notes
    )


def test_live_buffoon_generator_keeps_skip_with_open_joker_slot():
    state = _buffoon_state()
    choice = _buffoon_choice()

    actions = LivePackActionGenerator().generate_actions(state, [choice])

    assert any(action.name == SELECT_PACK_CARD for action in actions)
    assert any(action.name == SKIP_BOOSTER for action in actions)
