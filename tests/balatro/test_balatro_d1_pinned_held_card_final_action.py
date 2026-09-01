from types import SimpleNamespace

from games.balatro.actions import BalatroAction, DISCARD_CARDS, PLAY_CARDS
from games.balatro.card import BalatroCard
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


def _candidate(*, pinned: bool):
    return SimpleNamespace(
        strategy_id="held_kings_engine",
        pinned=pinned,
        bond_ids=("held_cards", "held_retrigger", "kings"),
        prescriptions=("preserve held Kings",),
    )


def _composition(*, candidate):
    return SimpleNamespace(
        pinned_strategy_id=candidate.strategy_id,
        strategy_candidates=(candidate,),
    )


def _state(cards):
    state = BalatroState()
    state.hand = list(cards)
    state.deck = []
    state.owned_deck = []
    state.jokers = []
    state.score = 0
    state.blind = SimpleNamespace(requirement=300)
    state.hands_remaining = 3
    state.discards_remaining = 2
    state.discards_used = 0
    state.boss_name = None
    state.blind_type = "SMALL"
    return state


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


def _action_signature(action):
    return (
        action.name,
        tuple(
            (
                str(getattr(card, "rank", "")),
                str(getattr(card, "suit", "")),
                str(getattr(card, "enhancement", "") or ""),
                str(getattr(card, "edition", "") or ""),
                str(getattr(card, "seal", "") or ""),
            )
            for card in action.cards
        ),
    )


def _policy(monkeypatch, *, pinned):
    policy = StrategyAwareLiveHandActionPolicy(evaluator=_Evaluator())
    candidate = _candidate(pinned=pinned)
    composition = _composition(candidate=candidate)
    monkeypatch.setattr(policy, "_composition", lambda state: ((), composition))
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


def test_pinned_held_card_preservation_changes_final_d1_discard(monkeypatch):
    king = BalatroCard("K", "Spades")
    seven = BalatroCard("7", "Hearts")
    state = _state([king, seven])

    weak_play = _plan(PLAY_CARDS, [seven], expected_score=10.0)
    discard_king = _plan(DISCARD_CARDS, [king])
    discard_seven = _plan(DISCARD_CARDS, [seven])
    plans = [weak_play, discard_king, discard_seven]

    forming_policy = _policy(monkeypatch, pinned=False)
    forming_decision = forming_policy.decide(state, plans)
    assert _action_signature(forming_decision.action) == _action_signature(
        discard_king.action
    )

    pinned_policy = _policy(monkeypatch, pinned=True)
    king_fit, king_notes = pinned_policy._pinned_card_preservation(
        state,
        discard_king.action,
    )
    seven_fit, seven_notes = pinned_policy._pinned_card_preservation(
        state,
        discard_seven.action,
    )
    assert king_fit < seven_fit
    assert any("preserves held K" in note for note in king_notes)
    assert seven_fit == 0.0
    assert any("sacrifices no held-engine card" in note for note in seven_notes)

    pinned_decision = pinned_policy.decide(state, plans)
    assert _action_signature(pinned_decision.action) == _action_signature(
        discard_seven.action
    )
    assert any(
        "sacrifices no held-engine card" in note
        for note in pinned_decision.rationale
    )


def test_survival_clear_overrides_pinned_held_card_preservation(monkeypatch):
    king = BalatroCard("K", "Spades")
    seven = BalatroCard("7", "Hearts")
    state = _state([king, seven])
    state.hands_remaining = 1

    clear_with_king = _plan(
        PLAY_CARDS,
        [king],
        clear_probability=1.0,
        expected_score=300.0,
    )
    preserve_king_discard = _plan(DISCARD_CARDS, [seven])

    pinned_policy = _policy(monkeypatch, pinned=True)
    decision = pinned_policy.decide(
        state,
        [preserve_king_discard, clear_with_king],
    )

    assert _action_signature(decision.action) == _action_signature(
        clear_with_king.action
    )
