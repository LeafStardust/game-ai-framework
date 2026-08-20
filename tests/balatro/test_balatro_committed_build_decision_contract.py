from types import SimpleNamespace

import pytest

import games.balatro  # noqa: F401 - installs the production policy stack
from games.balatro.aces_dna_hand_policy import DNA_SAFE_CLEAR_PROBABILITY, _safe_ace_plan
from games.balatro.ankh_presale_policy import best_ankh_presale_plan
from games.balatro.blue_joker_strategy_rules import BLUE_JOKER_STRATEGY_ID
from games.balatro.committed_build_replacement_policy import _same_route_immediate_upgrade
from games.balatro.strategy import COMMITTED, GOLD, NEUTRAL, SILVER
from games.balatro import strategy_conditional_relationships as conditional


def _joker(name, *, eternal=False):
    return SimpleNamespace(name=name, eternal=eternal)


def _state(*jokers):
    return SimpleNamespace(jokers=list(jokers))


def test_blue_and_hologram_share_one_generator_backed_route():
    blue = _joker("Blue Joker")
    hologram = _joker("Hologram")
    certificate = _joker("Certificate")

    assert conditional.conditional_joker_relationship(
        _state(blue), BLUE_JOKER_STRATEGY_ID, blue
    ) == SILVER
    assert conditional.conditional_joker_relationship(
        _state(hologram), BLUE_JOKER_STRATEGY_ID, hologram
    ) == SILVER
    assert conditional.conditional_joker_relationship(
        _state(certificate), BLUE_JOKER_STRATEGY_ID, certificate
    ) == NEUTRAL

    assert conditional.conditional_joker_relationship(
        _state(blue, certificate), BLUE_JOKER_STRATEGY_ID, blue
    ) == GOLD
    assert conditional.conditional_joker_relationship(
        _state(blue, certificate), BLUE_JOKER_STRATEGY_ID, certificate
    ) == SILVER
    assert conditional.conditional_joker_relationship(
        _state(hologram, certificate), BLUE_JOKER_STRATEGY_ID, hologram
    ) == GOLD
    assert conditional.conditional_joker_relationship(
        _state(hologram, certificate), BLUE_JOKER_STRATEGY_ID, certificate
    ) == SILVER


def test_same_route_gold_can_replace_silver_only_when_current_build_improves():
    incumbent = SimpleNamespace(
        active_alignment=True,
        strategy_id="flush",
        tier=SILVER,
    )
    candidate = SimpleNamespace(
        active_alignment=True,
        strategy_id="flush",
        tier=GOLD,
    )
    improving = SimpleNamespace(build_delta=2.0)
    buildup_only = SimpleNamespace(build_delta=-0.1)

    assert _same_route_immediate_upgrade("flush", incumbent, candidate, improving)
    assert not _same_route_immediate_upgrade("flush", incumbent, candidate, buildup_only)


def test_off_path_gold_is_not_a_same_route_upgrade():
    incumbent = SimpleNamespace(
        active_alignment=True,
        strategy_id="flush",
        tier=SILVER,
    )
    candidate = SimpleNamespace(
        active_alignment=True,
        strategy_id="pair",
        tier=GOLD,
    )
    assert not _same_route_immediate_upgrade(
        "flush", incumbent, candidate, SimpleNamespace(build_delta=100.0)
    )


def _plan(card, clear_probability):
    return SimpleNamespace(
        action=SimpleNamespace(name="PLAY_CARDS", cards=[card]),
        value=SimpleNamespace(
            clear_probability=clear_probability,
            expected_score=100.0,
            expected_hands_remaining=2.0,
        ),
    )


def test_dna_ace_setup_requires_ninety_percent_whole_blind_clear_probability():
    ace = SimpleNamespace(rank="A", edition=None, seal=None, enhancement=None, permanent_bonus=0)
    unsafe = _plan(ace, DNA_SAFE_CLEAR_PROBABILITY - 0.01)
    safe = _plan(ace, DNA_SAFE_CLEAR_PROBABILITY)

    assert _safe_ace_plan((unsafe,), dna_single=True) is None
    assert _safe_ace_plan((unsafe, safe), dna_single=True) is safe


class _Expectation:
    def __init__(self, gain):
        self.available = True
        self.complete = True
        self.expected_build_gain = float(gain)


class _AnkhEvaluator:
    def evaluate(self, state):
        # Fewer random non-Eternal targets improves the desired-copy outcome.
        return _Expectation(10.0 / max(1, len(state.jokers)))


class _Tracker:
    definitions = {}

    def observe(self, state):
        return SimpleNamespace(
            active_status=COMMITTED,
            dominant_strategy_id="aces",
        )

    def primary_strategy_id(self, resolution):
        return "aces"

    def evaluate_item(self, state, joker, *, kind):
        if getattr(joker, "name", "") == "Scholar":
            return SimpleNamespace(
                active_alignment=True,
                strategy_id="aces",
                tier=GOLD,
            )
        return SimpleNamespace(
            active_alignment=False,
            strategy_id=None,
            tier=None,
        )


class _Policy:
    ankh_evaluator = _AnkhEvaluator()
    item_estimator = SimpleNamespace(
        joker_build_value=SimpleNamespace(strategy_tracker=_Tracker())
    )


def test_ankh_presale_keeps_committed_core_and_removes_expendable_targets():
    scholar = _joker("Scholar")
    filler_a = _joker("Sly Joker")
    filler_b = _joker("Banner")
    state = _state(scholar, filler_a, filler_b)

    plan = best_ankh_presale_plan(_Policy(), state)
    assert plan is not None
    assert set(plan.sell_indices) == {1, 2}
    assert 0 not in plan.sell_indices
    assert plan.prepared_expected_gain > plan.current_expected_gain


def test_ankh_presale_never_sells_eternal_joker():
    scholar = _joker("Scholar")
    eternal_filler = _joker("Sly Joker", eternal=True)
    state = _state(scholar, eternal_filler)

    plan = best_ankh_presale_plan(_Policy(), state)
    assert plan is None
