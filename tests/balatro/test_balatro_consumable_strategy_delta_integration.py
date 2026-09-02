from types import SimpleNamespace

import pytest

import games.balatro  # install production authorities
import games.balatro.consumable_strategy_delta_policy as strategy_policy
from games.balatro.build.consumable_targeting import ConsumableTargetEvaluation
from games.balatro.card import BalatroCard
from games.balatro.state import BalatroState
from games.balatro.tarots import Chariot, HangedMan, WheelOfFortune


def _evaluation(*, total_gain: float, indices=(0,)) -> ConsumableTargetEvaluation:
    return ConsumableTargetEvaluation(
        target_indices=tuple(indices),
        cards=(),
        total_gain=float(total_gain),
        contextual_delta=float(total_gain),
        effective_changes=1,
        overwrite_penalty=0.0,
        rationale=("literal target proof",),
    )


def test_exact_tarot_projection_updates_persistent_card_without_mutating_current_state():
    state = BalatroState()
    card = BalatroCard("K", "Hearts", live_id=101)
    state.hand = [card]
    # Live observation may hold a distinct object for the persistent composition.
    state.owned_deck = [BalatroCard("K", "Hearts", live_id=101)]

    projected = strategy_policy._project_target_state(state, Chariot(), (0,))

    assert projected is not None
    assert projected is not state
    assert state.hand[0].enhancement is None
    assert state.owned_deck[0].enhancement is None
    assert projected.hand[0].enhancement == "Steel"
    assert projected.owned_deck[0].enhancement == "Steel"


def test_hanged_man_projection_uses_shared_permanent_destruction_semantics():
    state = BalatroState()
    first = BalatroCard("2", "Clubs", live_id=201)
    second = BalatroCard("K", "Hearts", live_id=202)
    state.hand = [first, second]
    state.owned_deck = [
        BalatroCard("2", "Clubs", live_id=201),
        BalatroCard("K", "Hearts", live_id=202),
    ]

    projected = strategy_policy._project_target_state(state, HangedMan(), (0,))

    assert projected is not None
    assert [card.live_id for card in state.owned_deck] == [201, 202]
    assert [card.live_id for card in projected.owned_deck] == [202]
    assert [card.live_id for card in projected.hand] == [202]


def test_strategy_adjustment_uses_canonical_delta_for_already_positive_exact_target(monkeypatch):
    state = BalatroState()
    card = BalatroCard("K", "Hearts", live_id=301)
    state.hand = [card]
    state.owned_deck = [BalatroCard("K", "Hearts", live_id=301)]
    observed = {}

    def fake_delta(current, projected):
        observed["current"] = current
        observed["projected"] = projected
        return SimpleNamespace(value=6.0, raw_delta=7.0, transition_cost=1.0)

    monkeypatch.setattr(strategy_policy, "strategy_delta_from_states", fake_delta)

    adjustment, notes = strategy_policy._strategy_adjustment(
        state,
        Chariot(),
        _evaluation(total_gain=1.5),
    )

    assert observed["current"] is state
    assert observed["projected"] is not state
    assert observed["projected"].owned_deck[0].enhancement == "Steel"
    assert adjustment == pytest.approx(0.6)
    assert any("canonical StrategyDelta=+6.000" in note for note in notes)
    assert any("consumable strategy weight=0.100" in note for note in notes)


def test_nonpositive_target_cannot_be_rescued_by_strategy(monkeypatch):
    state = BalatroState()
    card = BalatroCard("K", "Hearts", live_id=401)
    state.hand = [card]
    state.owned_deck = [BalatroCard("K", "Hearts", live_id=401)]

    def should_not_run(*_args, **_kwargs):
        raise AssertionError("StrategyDelta must not run for non-positive target")

    monkeypatch.setattr(strategy_policy, "strategy_delta_from_states", should_not_run)

    adjustment, notes = strategy_policy._strategy_adjustment(
        state,
        Chariot(),
        _evaluation(total_gain=0.0),
    )

    assert adjustment == 0.0
    assert notes == ()


def test_stochastic_tarot_projection_fails_closed_without_hidden_rng():
    state = BalatroState()
    state.jokers = [SimpleNamespace(edition=None)]
    state.hand = [BalatroCard("K", "Hearts", live_id=501)]
    state.owned_deck = [BalatroCard("K", "Hearts", live_id=501)]

    projected = strategy_policy._project_target_state(state, WheelOfFortune(), (0,))

    assert projected is None


def test_production_target_evaluator_has_canonical_strategy_delta_installed():
    from games.balatro.build.consumable_targeting import ContextualConsumableTargetEvaluator

    assert getattr(
        ContextualConsumableTargetEvaluator,
        "_canonical_strategy_delta_installed",
        False,
    )
