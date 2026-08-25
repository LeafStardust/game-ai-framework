from types import SimpleNamespace

import games.balatro.playbook.red_white.pack_policy as pack_module

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.live.consumable_timing_core import ConsumableTargetThresholds
from games.balatro.live.pack import LivePackChoice
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


def _registry(*, skip_bias=0.35, minimum_total_gain=None):
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


def test_red_white_exposes_current_d9_and_d10_thresholds():
    playbook = default_balatro_playbooks().get("RED", "WHITE")

    d9 = PackChoiceThresholds.from_mapping(playbook.thresholds_for("D9"))
    d10 = ConsumableTargetThresholds.from_mapping(playbook.thresholds_for("D10"))

    assert d9 == PackChoiceThresholds(skip_bias=0.35)
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


def test_d10_neutral_threshold_preserves_existing_positive_target_behavior(
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

    assert scored.total == 1.5
    assert scored.action.cards == list(state.hand)
    assert any("B6 pack target gain=0.500" in note for note in scored.notes)
