from types import SimpleNamespace

import games.balatro  # noqa: F401 - installs production policy stack
from games.balatro.five_run_decision_integrity_policy import (
    _definition_is_retired,
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
