from types import SimpleNamespace

import games.balatro  # noqa: F401 - install production authorities
from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.bonds.build_value import evaluate_build_value
from games.balatro.bonds.strategy_delta import strategy_delta_from_states
from games.balatro.build.consumable_targeting import ContextualConsumableTargetEvaluator
from games.balatro.card import BalatroCard
from games.balatro.consumable_strategy_delta_policy import _project_target_state
from games.balatro.joker import Joker, JokerContext
from games.balatro.joker_policy import (
    BUY,
    REPLACE,
    JokerAcquisitionPolicy,
    JokerAcquisitionThresholds,
    _bond_transition_bonus,
)
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.burnt_joker import BurntJoker
from games.balatro.jokers.erosion import ErosionJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.trading_card import TradingCardJoker
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.state import BalatroState
from games.balatro.tarots import HangedMan


class _Evaluator:
    def project_play(self, state, action):
        del state
        target = action.target or {}
        return SimpleNamespace(
            expected_hand_score=float(target.get("immediate_score", 0.0)),
            clear_probability=float(target.get("clear_probability", 0.0)),
            outcomes=(),
        )

    def evaluate(self, state, action):
        del state
        return float((action.target or {}).get("fallback_value", 0.0))


class _MaterialScoringJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is not None:
            context.score.mult += 80
        return context


class _InertJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


def _standard_deck():
    ranks = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
    suits = ("Clubs", "Diamonds", "Hearts", "Spades")
    return [BalatroCard(rank, suit) for suit in suits for rank in ranks]


def _shop_state(*jokers):
    state = BalatroState()
    state.phase = "SHOP"
    state.ante = 3
    state.money = 20
    state.joker_slots = 5
    state.jokers = list(jokers)
    state.owned_deck = _standard_deck()
    return state


def _thresholds():
    return JokerAcquisitionThresholds(
        minimum_purchase_advantage=0.0,
        minimum_replacement_advantage=0.0,
        aligned_minimum_replacement_advantage=0.0,
        price_weight=0.0,
        interest_weight=0.0,
        reserve_weight=0.0,
        last_joker_slot_penalty=0.0,
        penultimate_joker_slot_penalty=0.0,
    )


def _plan(action_name, cards, *, clear_probability=0.0, expected_score=0.0):
    action = BalatroAction(
        action_name,
        cards=list(cards),
        target={
            "clear_probability": float(clear_probability),
            "immediate_score": float(expected_score),
        },
    )
    return LiveBlindPlan(
        action=action,
        value=LiveBlindPlanValue(
            clear_probability=float(clear_probability),
            expected_progress=0.0,
            expected_score=float(expected_score),
            expected_hands_remaining=2.0,
            expected_discards_remaining=1.0,
        ),
        horizon=1,
        exact=True,
        candidate_count=3,
    )


def _hand_state(cards, *, jokers):
    state = BalatroState()
    state.hand = list(cards)
    state.deck = []
    state.owned_deck = _standard_deck()
    state.jokers = list(jokers)
    state.score = 0
    state.blind = SimpleNamespace(requirement=300)
    state.hands_remaining = 3
    state.discards_remaining = 2
    state.discards_total = 2
    state.discards_used = 0
    state.hand_levels = {"HIGH_CARD": 1, "PAIR": 3}
    state.hand_play_counts = {}
    state.boss_name = None
    state.blind_type = "SMALL"
    return state


def _d1_policy(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy(evaluator=_Evaluator())
    monkeypatch.setattr(policy, "_hand_bond_intents", lambda state: ())
    monkeypatch.setattr(policy, "_preservation", lambda plan: 0.0)
    monkeypatch.setattr(policy, "_vagabond_generation_active", lambda state: False)
    monkeypatch.setattr(
        policy,
        "_green_preserved_decision",
        lambda state, plans, decision: decision,
    )
    monkeypatch.setattr(policy.build_evaluator, "prepare", lambda state: None)
    monkeypatch.setattr(policy.build_evaluator, "reset_cache", lambda: None)
    return policy


def test_burnt_construction_reaches_final_buy_then_target_discard(monkeypatch):
    state = _shop_state()
    candidate = BurntJoker()
    candidate.cost = 0

    projected = state.copy()
    projected.jokers = [candidate]
    delta = strategy_delta_from_states(state, projected)
    decision = JokerAcquisitionPolicy(_thresholds()).decide(state, candidate)

    assert delta.value > 0.0
    assert projected is not state
    assert evaluate_build_value(projected).by_bond_id["hand_leveling"].value > 0.0
    assert decision.action == BUY
    assert decision.selected is not None
    assert any("canonical StrategyDelta=+" in note for note in decision.selected.rationale)

    generic = (BalatroCard("3", "Clubs"), BalatroCard("4", "Diamonds"))
    pair = (BalatroCard("8", "Hearts"), BalatroCard("8", "Spades"))
    play_card = BalatroCard("A", "Hearts")
    tactical = _hand_state([play_card, *generic, *pair], jokers=(candidate,))
    below_pace_play = _plan(PLAY_CARDS, (play_card,), expected_score=10.0)
    generic_discard = _plan(DISCARD_CARDS, generic)
    target_discard = _plan(DISCARD_CARDS, pair)

    final_action = _d1_policy(monkeypatch).decide(
        tactical,
        (below_pace_play, generic_discard, target_discard),
    )

    assert final_action.action is target_discard.action
    assert final_action.selected_plan is target_discard


def test_deck_thinning_construction_reaches_buy_then_permanent_hanged_man_target():
    state = _shop_state(ErosionJoker())
    candidate = TradingCardJoker()
    candidate.cost = 0

    projected = state.copy()
    projected.jokers = [*state.jokers, candidate]
    current_value = evaluate_build_value(state).by_bond_id["deck_thinning"].value
    projected_value = evaluate_build_value(projected).by_bond_id["deck_thinning"].value
    decision = JokerAcquisitionPolicy(_thresholds()).decide(state, candidate)

    assert projected_value > current_value
    assert strategy_delta_from_states(state, projected).value > 0.0
    assert decision.action == BUY
    assert decision.selected is not None
    assert any("canonical StrategyDelta=+" in note for note in decision.selected.rationale)

    first = BalatroCard("2", "Clubs", live_id=801)
    second = BalatroCard("9", "Diamonds", live_id=802)
    survivor = BalatroCard("K", "Hearts", live_id=803)
    tactical = BalatroState()
    tactical.jokers = [ErosionJoker(), candidate]
    tactical.hand = [first, second, survivor]
    tactical.owned_deck = [first, second, survivor]

    ranked = ContextualConsumableTargetEvaluator().rank_targets(tactical, HangedMan())
    chosen = ranked[0]
    result = _project_target_state(tactical, HangedMan(), chosen.target_indices)

    assert chosen.target_indices == (0, 1)
    assert result is not None
    assert tuple(card.live_id for card in tactical.owned_deck) == (801, 802, 803)
    assert tuple(card.live_id for card in result.owned_deck) == (803,)


def test_held_engine_buy_retention_loss_override_and_tactical_preservation(monkeypatch):
    state = _shop_state(BaronJoker())
    for card in state.owned_deck:
        if card.rank == "K" and card.suit in {"Hearts", "Spades"}:
            card.enhancement = "Steel"
    candidate = MimeJoker()
    candidate.cost = 0

    projected = state.copy()
    projected.jokers = [*state.jokers, candidate]
    delta = strategy_delta_from_states(state, projected)
    decision = JokerAcquisitionPolicy(_thresholds()).decide(state, candidate)

    assert delta.value > 0.0
    assert evaluate_build_value(projected).motif_total > 0.0
    assert decision.action == BUY
    assert decision.selected is not None
    assert any("canonical StrategyDelta=+" in note for note in decision.selected.rationale)

    projected.joker_slots = 2
    inert = _InertJoker()
    loss, loss_notes = _bond_transition_bonus(projected, inert, replace_index=1)
    assert loss < 0.0
    assert any("canonical StrategyDelta=-" in note for note in loss_notes)

    stronger = _MaterialScoringJoker()
    stronger.cost = 0
    replacement = JokerAcquisitionPolicy(_thresholds()).decide(projected, stronger)
    assert replacement.action == REPLACE
    assert replacement.selected is not None
    assert replacement.selected.replace_joker == "MimeJoker"
    assert replacement.selected.build_gain > 0.0
    assert any("canonical StrategyDelta=-" in note for note in replacement.selected.rationale)

    engine = BalatroCard("K", "Spades", enhancement="Steel", seal="Red")
    expendable = BalatroCard("7", "Hearts")
    play_card = BalatroCard("A", "Clubs")
    tactical = _hand_state(
        [play_card, engine, expendable],
        jokers=(BaronJoker(), candidate),
    )
    below_pace_play = _plan(PLAY_CARDS, (play_card,), expected_score=10.0)
    discard_engine = _plan(DISCARD_CARDS, (engine,))
    discard_expendable = _plan(DISCARD_CARDS, (expendable,))

    final_action = _d1_policy(monkeypatch).decide(
        tactical,
        (below_pace_play, discard_engine, discard_expendable),
    )

    assert final_action.action is discard_expendable.action
    assert final_action.selected_plan is discard_expendable
