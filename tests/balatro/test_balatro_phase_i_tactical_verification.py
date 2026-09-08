from types import SimpleNamespace

import games.balatro  # noqa: F401 - install production authorities
import games.balatro.consumable_strategy_delta_policy as consumable_strategy
from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.build.consumable_targeting import (
    ConsumableTargetEvaluation,
    ContextualConsumableTargetEvaluator,
)
from games.balatro.card import BalatroCard
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.burnt_joker import BurntJoker
from games.balatro.jokers.mime import MimeJoker
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


def _standard_deck():
    ranks = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
    suits = ("Clubs", "Diamonds", "Hearts", "Spades")
    return [BalatroCard(rank, suit) for suit in suits for rank in ranks]


def _state(cards, *, jokers=()):
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


def _plan(
    action_name,
    cards,
    *,
    clear_probability=0.0,
    expected_score=0.0,
    immediate_score=0.0,
):
    action = BalatroAction(
        action_name,
        cards=list(cards),
        target={
            "clear_probability": float(clear_probability),
            "immediate_score": float(immediate_score),
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


def _d1_policy(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy(evaluator=_Evaluator())
    # Keep the production tactical helpers under test. Neutralize only unrelated
    # build/profile signals so the counterfactual is owned by the Phase-I mechanic.
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


def test_burnt_target_hand_breaks_only_survival_equivalent_discard_tie(monkeypatch):
    generic_cards = (BalatroCard("3", "Clubs"), BalatroCard("4", "Diamonds"))
    pair_cards = (BalatroCard("8", "Hearts"), BalatroCard("8", "Spades"))
    play_card = BalatroCard("A", "Hearts")
    state = _state(
        [play_card, *generic_cards, *pair_cards],
        jokers=(BurntJoker(),),
    )

    below_pace_play = _plan(PLAY_CARDS, (play_card,), immediate_score=10.0)
    generic_discard = _plan(DISCARD_CARDS, generic_cards)
    pair_discard = _plan(DISCARD_CARDS, pair_cards)

    policy = _d1_policy(monkeypatch)
    generic_fit, _ = policy._strategy_fit(state, generic_discard.action)
    pair_fit, pair_notes = policy._strategy_fit(state, pair_discard.action)
    decision = policy.decide(
        state,
        (below_pace_play, generic_discard, pair_discard),
    )

    assert pair_fit > generic_fit
    assert any("Burnt target=PAIR" in note for note in pair_notes)
    assert decision.action is pair_discard.action
    assert decision.selected_plan is pair_discard


def test_materially_safer_discard_overrides_real_burnt_target_fit(monkeypatch):
    safe_cards = (BalatroCard("3", "Clubs"), BalatroCard("4", "Diamonds"))
    pair_cards = (BalatroCard("8", "Hearts"), BalatroCard("8", "Spades"))
    play_card = BalatroCard("A", "Hearts")
    state = _state(
        [play_card, *safe_cards, *pair_cards],
        jokers=(BurntJoker(),),
    )

    below_pace_play = _plan(PLAY_CARDS, (play_card,), immediate_score=10.0)
    pair_discard = _plan(
        DISCARD_CARDS,
        pair_cards,
        clear_probability=0.10,
        expected_score=50.0,
    )
    safer_discard = _plan(
        DISCARD_CARDS,
        safe_cards,
        clear_probability=0.30,
        expected_score=90.0,
    )

    policy = _d1_policy(monkeypatch)
    decision = policy.decide(
        state,
        (below_pace_play, pair_discard, safer_discard),
    )

    assert decision.action is safer_discard.action
    assert decision.selected_plan is safer_discard


def test_hanged_man_projection_and_strategy_delta_rank_viable_thinning_targets(
    monkeypatch,
):
    state = BalatroState()
    first = BalatroCard("2", "Clubs", live_id=801)
    second = BalatroCard("9", "Diamonds", live_id=802)
    survivor = BalatroCard("K", "Hearts", live_id=803)
    state.hand = [first, second, survivor]
    state.owned_deck = [
        BalatroCard("2", "Clubs", live_id=801),
        BalatroCard("9", "Diamonds", live_id=802),
        BalatroCard("K", "Hearts", live_id=803),
    ]

    evaluator = ContextualConsumableTargetEvaluator()
    native_targets = (
        ConsumableTargetEvaluation(
            target_indices=(0,),
            cards=(first,),
            total_gain=1.0,
            contextual_delta=1.0,
            effective_changes=1,
            overwrite_penalty=0.0,
            rationale=("first target is already viable",),
        ),
        ConsumableTargetEvaluation(
            target_indices=(1,),
            cards=(second,),
            total_gain=1.0,
            contextual_delta=1.0,
            effective_changes=1,
            overwrite_penalty=0.0,
            rationale=("second target is already viable",),
        ),
    )
    monkeypatch.setattr(
        evaluator,
        "_rank_hanged_man_targets",
        lambda current, consumable: native_targets,
    )

    projected_decks = []

    def controlled_delta(current, projected):
        assert current is state
        live_ids = tuple(card.live_id for card in projected.owned_deck)
        projected_decks.append(live_ids)
        value = 6.0 if 801 not in live_ids else 0.0
        return SimpleNamespace(value=value, raw_delta=value, transition_cost=0.0)

    monkeypatch.setattr(
        consumable_strategy,
        "strategy_delta_from_states",
        controlled_delta,
    )

    ranked = evaluator.rank_targets(state, HangedMan())

    assert tuple(card.live_id for card in state.owned_deck) == (801, 802, 803)
    assert (802, 803) in projected_decks
    assert (801, 803) in projected_decks
    assert ranked[0].target_indices == (0,)
    assert any("canonical StrategyDelta=+6.000" in note for note in ranked[0].rationale)


def test_mechanical_held_value_preserves_steel_baron_mime_card_on_equal_line(
    monkeypatch,
):
    engine_card = BalatroCard("K", "Spades", enhancement="Steel", seal="Red")
    expendable = BalatroCard("7", "Hearts")
    play_card = BalatroCard("A", "Clubs")
    state = _state(
        [play_card, engine_card, expendable],
        jokers=(BaronJoker(), MimeJoker()),
    )

    below_pace_play = _plan(PLAY_CARDS, (play_card,), immediate_score=10.0)
    discard_engine = _plan(DISCARD_CARDS, (engine_card,))
    discard_expendable = _plan(DISCARD_CARDS, (expendable,))

    policy = _d1_policy(monkeypatch)
    engine_fit, engine_notes = policy._strategy_fit(state, discard_engine.action)
    expendable_fit, _ = policy._strategy_fit(state, discard_expendable.action)
    decision = policy.decide(
        state,
        (below_pace_play, discard_engine, discard_expendable),
    )

    assert engine_fit < expendable_fit
    assert any("Steel xMult" in note for note in engine_notes)
    assert any("Baron King xMult" in note for note in engine_notes)
    assert any("Mime retriggers" in note for note in engine_notes)
    assert any("Red Seal" in note for note in engine_notes)
    assert decision.action is discard_expendable.action


def test_materially_stronger_clear_can_spend_steel_baron_mime_card(monkeypatch):
    engine_card = BalatroCard("K", "Spades", enhancement="Steel", seal="Red")
    expendable = BalatroCard("7", "Hearts")
    state = _state(
        [engine_card, expendable],
        jokers=(BaronJoker(), MimeJoker()),
    )

    clear_with_engine = _plan(
        PLAY_CARDS,
        (engine_card,),
        clear_probability=1.0,
        expected_score=300.0,
        immediate_score=300.0,
    )
    weak_preserving_play = _plan(
        PLAY_CARDS,
        (expendable,),
        clear_probability=0.25,
        expected_score=100.0,
        immediate_score=100.0,
    )

    policy = _d1_policy(monkeypatch)
    decision = policy.decide(
        state,
        (weak_preserving_play, clear_with_engine),
    )

    assert decision.action is clear_with_engine.action
    assert decision.selected_plan is clear_with_engine
