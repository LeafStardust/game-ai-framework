from types import SimpleNamespace

from games.balatro.actions import BalatroAction, DISCARD_CARDS, PLAY_CARDS
from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.card import BalatroCard
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.state import BalatroState


class _Evaluator:
    def project_play(self, state, action):
        del state
        return SimpleNamespace(
            expected_hand_score=float(action.target.get("immediate_score", 0.0)),
            clear_probability=float(action.target.get("clear_probability", 0.0)),
            outcomes=(),
        )

    def evaluate(self, state, action):
        del state
        return float(action.target.get("fallback_value", 0.0))


def _state(*jokers):
    king = BalatroCard("K", "Spades")
    seven = BalatroCard("7", "Hearts")
    state = BalatroState()
    state.hand = [king, seven]
    # Keep permanent-deck infrastructure neutral so the commitment transition is
    # caused by the real Baron -> Baron+Mime engine, not by a prebuilt Steel/King
    # package in the fixture.
    state.deck = []
    state.owned_deck = []
    state.jokers = list(jokers)
    state.score = 0
    state.blind = SimpleNamespace(requirement=300)
    state.hands_remaining = 3
    state.discards_remaining = 2
    state.discards_used = 0
    state.boss_name = None
    state.blind_type = "SMALL"
    return state, king, seven


def _plan(
    action_name,
    cards,
    *,
    clear_probability=0.0,
    expected_score=0.0,
    fallback_value=0.0,
):
    action = BalatroAction(
        action_name,
        cards=list(cards),
        target={
            "immediate_score": expected_score,
            "clear_probability": clear_probability,
            "fallback_value": fallback_value,
        },
    )
    return LiveBlindPlan(
        action=action,
        value=LiveBlindPlanValue(
            clear_probability=clear_probability,
            expected_progress=0.0,
            expected_score=expected_score,
            expected_hands_remaining=2.0,
            expected_discards_remaining=1.0,
        ),
        horizon=1,
        exact=True,
        candidate_count=3,
    )


def _signature(action):
    return action.name, tuple(
        (
            str(card.rank),
            str(card.suit),
            str(getattr(card, "enhancement", "") or ""),
            str(getattr(card, "seal", "") or ""),
        )
        for card in action.cards
    )


def _pilot_candidate(composition):
    return next(
        candidate
        for candidate in composition.strategy_candidates
        if candidate.strategy_id == "baron_mime_steel"
    )


def _source_tokens(candidate):
    return {
        "".join(ch for ch in str(source).lower() if ch.isalnum()).removesuffix("joker")
        for source in candidate.sources
    }


def _policy(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy(evaluator=_Evaluator())
    # Leave _composition untouched: this regression is specifically proving that
    # the production evaluator/composer naturally supplies the candidate consumed
    # by D1. Only unrelated D1 signals are neutralized so the counterfactual stays
    # about held-card strategy authority.
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


def test_real_baron_engine_forms_then_pins_when_mime_completes_second_core():
    forming_state, _, _ = _state(BaronJoker())
    _, forming = evaluate_bond_composition(forming_state)
    forming_candidate = _pilot_candidate(forming)

    assert forming_candidate.commitment == StrategyCommitment.FORMING
    assert forming.pinned_strategy_id is None
    assert "baron" in _source_tokens(forming_candidate)
    assert forming_candidate.motif_ids == ("baron_mime_steel",)

    pinned_state, _, _ = _state(BaronJoker(), MimeJoker())
    _, pinned = evaluate_bond_composition(pinned_state)
    pinned_candidate = _pilot_candidate(pinned)

    assert pinned_candidate.commitment >= StrategyCommitment.PINNED
    assert pinned.pinned_strategy_id == pinned_candidate.strategy_id
    assert {"baron", "mime"}.issubset(_source_tokens(pinned_candidate))
    # D1 held-card preservation consumes the mechanically relevant core. Steel is
    # optional future infrastructure here and does not need to be synthesized into
    # a candidate merely because the named motif can eventually include it.
    assert {"held_cards", "held_retrigger", "kings"}.issubset(
        set(pinned_candidate.bond_ids)
    )
    assert "baron_mime_steel" in pinned_candidate.motif_ids


def test_real_pinned_baron_mime_composition_changes_final_d1_discard(monkeypatch):
    forming_state, forming_king, forming_seven = _state(BaronJoker())
    forming_policy = _policy(monkeypatch)
    forming_plans = [
        _plan(PLAY_CARDS, [forming_seven], expected_score=10.0),
        _plan(DISCARD_CARDS, [forming_king]),
        _plan(DISCARD_CARDS, [forming_seven]),
    ]

    forming_decision = forming_policy.decide(forming_state, forming_plans)
    assert _signature(forming_decision.action) == _signature(forming_plans[1].action)

    pinned_state, pinned_king, pinned_seven = _state(BaronJoker(), MimeJoker())
    pinned_policy = _policy(monkeypatch)
    pinned_plans = [
        _plan(PLAY_CARDS, [pinned_seven], expected_score=10.0),
        _plan(DISCARD_CARDS, [pinned_king]),
        _plan(DISCARD_CARDS, [pinned_seven]),
    ]

    # Production composition, not a test-injected namespace, must supply the held
    # engine preservation signal.
    king_fit, king_notes = pinned_policy._pinned_card_preservation(
        pinned_state,
        pinned_plans[1].action,
    )
    seven_fit, _ = pinned_policy._pinned_card_preservation(
        pinned_state,
        pinned_plans[2].action,
    )
    assert king_fit < seven_fit
    assert any("preserves held K" in note for note in king_notes)

    pinned_decision = pinned_policy.decide(pinned_state, pinned_plans)
    assert _signature(pinned_decision.action) == _signature(pinned_plans[2].action)


def test_real_pinned_baron_mime_still_spends_king_for_deterministic_survival(monkeypatch):
    state, king, seven = _state(BaronJoker(), MimeJoker())
    state.hands_remaining = 1

    policy = _policy(monkeypatch)
    clear_with_king = _plan(
        PLAY_CARDS,
        [king],
        clear_probability=1.0,
        expected_score=300.0,
    )
    preserve_king_discard = _plan(DISCARD_CARDS, [seven])

    decision = policy.decide(state, [preserve_king_discard, clear_with_king])
    assert _signature(decision.action) == _signature(clear_with_king.action)
