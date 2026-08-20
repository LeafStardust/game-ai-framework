from types import SimpleNamespace

import games.balatro  # noqa: F401 - installs production policy stack
import games.balatro.five_run_decision_integrity_policy as integrity
from games.balatro.actions import SELECT_PACK_CARD, BalatroAction
from games.balatro.five_run_decision_integrity_policy import (
    _definition_is_retired,
    _early_survival_buy,
    _madness_threatens_established_build,
)
from games.balatro.strategy import GOLD, HIGHLIGHTED, SILVER
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_tree_catalog import TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY
from games.balatro.strategy_tree_tracker import TreeAwareStateAwareBalatroStrategyTracker


def _joker(name, *, eternal=False):
    return SimpleNamespace(name=name, eternal=eternal)


class _Tracker:
    definitions = {}

    def __init__(self, *, score=6.0, tier=GOLD):
        self.score = float(score)
        self.tier = tier

    def observe(self, state):
        del state
        assessment = SimpleNamespace(score=self.score)
        return SimpleNamespace(
            active_status=HIGHLIGHTED,
            dominant_strategy_id="aces",
            assessment=lambda strategy_id: assessment if strategy_id == "aces" else None,
        )

    def primary_strategy_id(self, resolution):
        del resolution
        return "aces"

    def evaluate_item(self, state, joker, *, kind):
        del state, kind
        aligned = getattr(joker, "name", "") == "Scholar"
        return SimpleNamespace(
            active_alignment=aligned,
            strategy_id="aces" if aligned else None,
            tier=self.tier if aligned else None,
        )


class _Policy:
    def __init__(self, tracker):
        self.transition_planner = SimpleNamespace(
            evaluator=SimpleNamespace(strategy_tracker=tracker)
        )


def test_madness_cannot_pivot_over_established_non_eternal_gold_core():
    state = SimpleNamespace(jokers=[_joker("Scholar")])
    policy = _Policy(_Tracker(score=6.0, tier=GOLD))

    assert _madness_threatens_established_build(policy, state, _joker("Madness"))


def test_madness_guard_does_not_fire_for_eternal_core_or_weak_highlight():
    eternal_state = SimpleNamespace(jokers=[_joker("Scholar", eternal=True)])
    strong = _Policy(_Tracker(score=6.0, tier=SILVER))
    assert not _madness_threatens_established_build(strong, eternal_state, _joker("Madness"))

    weak_state = SimpleNamespace(jokers=[_joker("Scholar")])
    weak = _Policy(_Tracker(score=5.99, tier=GOLD))
    assert not _madness_threatens_established_build(weak, weak_state, _joker("Madness"))


def test_ante_one_survival_scorer_can_override_strategy_purity_when_reserve_survives():
    option = SimpleNamespace(
        eligible=True,
        total_advantage=0.10,
        economics=SimpleNamespace(money_after=7),
        rationale=("fixture economics",),
    )
    decision = SimpleNamespace(
        action="HOLD",
        options=(option,),
        selected=None,
        thresholds=SimpleNamespace(
            reserve_target=5,
            minimum_purchase_advantage=0.35,
        ),
        rationale=("off-strategy hold",),
    )
    value = SimpleNamespace(
        direct_scoring_value=2.0,
        total_gain=-0.5,
        base_total_gain=1.5,
    )
    policy = SimpleNamespace(
        transition_planner=SimpleNamespace(
            plan=lambda state, candidate: SimpleNamespace(candidate_value=value)
        )
    )
    state = SimpleNamespace(ante=1, jokers=[_joker("Flash Card")], joker_slots=5)

    result = _early_survival_buy(policy, state, _joker("Crazy Joker"), decision)

    assert result.action == "BUY"
    assert result.selected.total_advantage > decision.thresholds.minimum_purchase_advantage
    assert any("survival takes precedence" in note for note in result.rationale)


def test_early_survival_override_does_not_spend_below_reserve_or_force_non_scorer():
    base = SimpleNamespace(
        action="HOLD",
        selected=None,
        thresholds=SimpleNamespace(reserve_target=5, minimum_purchase_advantage=0.35),
        rationale=(),
    )
    low_cash_option = SimpleNamespace(
        eligible=True,
        total_advantage=0.10,
        economics=SimpleNamespace(money_after=4),
        rationale=(),
    )
    non_scoring_option = SimpleNamespace(
        eligible=True,
        total_advantage=0.10,
        economics=SimpleNamespace(money_after=7),
        rationale=(),
    )
    state = SimpleNamespace(ante=1, jokers=[], joker_slots=5)

    low_cash_policy = SimpleNamespace(
        transition_planner=SimpleNamespace(
            plan=lambda state, candidate: SimpleNamespace(
                candidate_value=SimpleNamespace(
                    direct_scoring_value=2.0,
                    total_gain=-0.5,
                    base_total_gain=1.5,
                )
            )
        )
    )
    non_scoring_policy = SimpleNamespace(
        transition_planner=SimpleNamespace(
            plan=lambda state, candidate: SimpleNamespace(
                candidate_value=SimpleNamespace(
                    direct_scoring_value=0.0,
                    total_gain=-0.5,
                    base_total_gain=1.5,
                )
            )
        )
    )

    low_cash = _early_survival_buy(
        low_cash_policy,
        state,
        _joker("Crazy Joker"),
        SimpleNamespace(**{**base.__dict__, "options": (low_cash_option,)}),
    )
    non_scoring = _early_survival_buy(
        non_scoring_policy,
        state,
        _joker("Egg"),
        SimpleNamespace(**{**base.__dict__, "options": (non_scoring_option,)}),
    )

    assert low_cash.action == "HOLD"
    assert non_scoring.action == "HOLD"


def test_buffoon_free_slot_madness_is_blocked_for_established_aces():
    tracker = _Tracker(score=6.0, tier=GOLD)
    policy = SimpleNamespace(
        item_estimator=SimpleNamespace(
            joker_build_value=SimpleNamespace(strategy_tracker=tracker)
        ),
        _pack_joker_factory=SimpleNamespace(
            create=lambda data: _joker(data["label"])
        ),
    )
    state = SimpleNamespace(
        phase="BUFFOON_PACK",
        joker_slots=5,
        jokers=[_joker("Scholar")],
    )
    choice = SimpleNamespace(
        kind="JOKER",
        data={"label": "Madness"},
    )
    action = BalatroAction(SELECT_PACK_CARD, target=choice)

    result = integrity.PlaybookBalatroPackPolicy.score_action(policy, state, action)

    assert result.total == -1.0
    assert any("Madness Buffoon choice blocked" in note for note in result.notes)


def test_buffoon_full_roster_uses_strategy_aware_transition_planner(monkeypatch):
    used = {}

    class _StrategyPlanner:
        def __init__(self, *, evaluator):
            used["evaluator"] = evaluator

    class _AcquisitionPolicy:
        def __init__(self, planner):
            used["planner"] = planner

        def decide(self, state, candidate):
            del state, candidate
            return SimpleNamespace(
                action="HOLD",
                selected=None,
                candidate="GreenJoker",
                rationale=("fixture hold",),
            )

    monkeypatch.setattr(integrity, "StrategyAwareJokerBuildTransitionPlanner", _StrategyPlanner)
    monkeypatch.setattr(integrity, "PlaybookJokerAcquisitionPolicy", _AcquisitionPolicy)

    evaluator = SimpleNamespace(strategy_tracker=object())
    policy = SimpleNamespace(
        item_estimator=SimpleNamespace(joker_build_value=evaluator),
        _pack_joker_factory=SimpleNamespace(create=lambda data: _joker(data["label"])),
    )
    state = SimpleNamespace(phase="BUFFOON_PACK", joker_slots=1, jokers=[_joker("Walkie Talkie")])
    choice = SimpleNamespace(kind="JOKER", data={"label": "Green Joker"})
    action = BalatroAction(SELECT_PACK_CARD, target=choice)

    result = integrity.PlaybookBalatroPackPolicy._buffoon_replacement_score(
        policy, state, action, choice
    )

    assert used["evaluator"] is evaluator
    assert isinstance(used["planner"], _StrategyPlanner)
    assert result.total == -1.0
    assert any("does not justify replacing" in note for note in result.notes)


def test_retired_support_and_merged_legacy_routes_are_not_actionable():
    tracker = TreeAwareStateAwareBalatroStrategyTracker(
        RUNTIME_UNIVERSAL_BALATRO_STRATEGIES,
        topology=TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
    )
    state = SimpleNamespace(
        jokers=[],
        vouchers=[],
        consumables=[],
        owned_deck=[],
        deck=[],
        hand_levels={},
        hand_play_counts={},
        ante=1,
        money=10,
    )

    ids = {assessment.strategy_id for assessment in tracker.assess(state)}
    assert "abstract_joker" not in ids
    assert "hologram_growth" not in ids
    assert "hologram_dna" not in ids
    assert "hologram_certificate" not in ids
    assert "hologram_marble" not in ids
    assert "blue_joker_deck" in ids


def test_retirement_detector_recognizes_guard_and_merge_markers():
    assert _definition_is_retired(
        SimpleNamespace(required_jokers=frozenset({"__retired_non_standalone_strategy__"}))
    )
    assert _definition_is_retired(
        SimpleNamespace(required_jokers=frozenset({"__merged_into_blue_hologram_deck_growth__"}))
    )
    assert not _definition_is_retired(SimpleNamespace(required_jokers=frozenset()))
