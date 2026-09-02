from types import SimpleNamespace

import games.balatro.strategy_execution_guard_policy as no_discard
from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.aces_dna_hand_policy import _safe_dna_rank_plan
from games.balatro.bonds.behavior_strategy import _Node, _relation
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime import live_memory_autonomous_step_injected as live_step


def test_active_no_discard_engine_recognizes_green_joker(monkeypatch):
    monkeypatch.setattr(
        no_discard,
        "bond_strategy_diagnostics",
        lambda _state: {"relevant_bonds": [{"bond_id": "no_discard", "realization": "ACTIVE"}]},
    )
    state = SimpleNamespace(jokers=[SimpleNamespace(label="Green Joker")])
    assert no_discard._realized_no_discard_engine(state) is True


def test_active_no_discard_engine_recognizes_delayed_without_banner(monkeypatch):
    monkeypatch.setattr(
        no_discard,
        "bond_strategy_diagnostics",
        lambda _state: {"relevant_bonds": [{"bond_id": "no_discard", "realization": "ACTIVE"}]},
    )
    state = SimpleNamespace(jokers=[SimpleNamespace(label="Delayed Gratification")])
    assert no_discard._realized_no_discard_engine(state) is True


def test_realized_no_discard_prefers_pace_qualified_play_over_discard(monkeypatch):
    monkeypatch.setattr(no_discard, "_realized_no_discard_engine", lambda _state: True)
    play = SimpleNamespace(
        action=SimpleNamespace(name=PLAY_CARDS, cards=(SimpleNamespace(rank="4"),)),
        value=SimpleNamespace(clear_probability=0.9),
    )
    policy = SimpleNamespace(
        EPSILON=1e-9,
        evaluator=SimpleNamespace(project_play=lambda _state, _action: SimpleNamespace(expected_hand_score=120.0)),
        _strategy_fit=lambda _state, _action: (1.0,),
        _within_type_key=lambda _plan: (0,),
    )
    decision = SimpleNamespace(
        selected_plan=play,
        thresholds=SimpleNamespace(safe_clear_probability_tolerance=0.01),
        pace_target=100.0,
    )
    selected = no_discard._safe_pace_play(policy, SimpleNamespace(), (play,), decision)
    assert selected is not None
    assert selected[2] is play


def test_hand_repetition_selects_safe_repeat_instead_of_new_hand(monkeypatch):
    monkeypatch.setattr(no_discard, "_realized_bond", lambda _state, bond_id: bond_id == "hand_repetition")
    repeat = SimpleNamespace(
        action=SimpleNamespace(name=PLAY_CARDS, cards=(SimpleNamespace(rank="4"),)),
        value=SimpleNamespace(clear_probability=0.90),
    )
    fresh = SimpleNamespace(
        action=SimpleNamespace(name=PLAY_CARDS, cards=(SimpleNamespace(rank="5"),)),
        value=SimpleNamespace(clear_probability=0.91),
    )
    monkeypatch.setattr(no_discard, "_hand_key", lambda _policy, _state, plan: "pair" if plan is repeat else "straight")
    state = SimpleNamespace(round_hand_play_counts={"PAIR": 1})
    policy = SimpleNamespace(
        EPSILON=1e-9,
        evaluator=SimpleNamespace(project_play=lambda _state, _action: SimpleNamespace(expected_hand_score=120.0)),
        _strategy_fit=lambda _state, _action: (1.0,),
        _within_type_key=lambda _plan: (0,),
    )
    decision = SimpleNamespace(
        action=fresh.action,
        selected_plan=fresh,
        thresholds=SimpleNamespace(safe_clear_probability_tolerance=0.02),
        pace_target=100.0,
    )
    selected = no_discard._safe_repeat_play(policy, state, (fresh, repeat), decision)
    assert selected is not None
    assert selected[2] is repeat


def test_hand_repetition_can_replace_unnecessary_discard(monkeypatch):
    monkeypatch.setattr(no_discard, "_realized_bond", lambda _state, bond_id: bond_id == "hand_repetition")
    repeat = SimpleNamespace(
        action=SimpleNamespace(name=PLAY_CARDS, cards=(SimpleNamespace(rank="4"),)),
        value=SimpleNamespace(clear_probability=0.90),
    )
    discard = SimpleNamespace(
        action=SimpleNamespace(name=DISCARD_CARDS, cards=(SimpleNamespace(rank="K"),)),
        value=SimpleNamespace(clear_probability=0.91),
    )
    monkeypatch.setattr(no_discard, "_hand_key", lambda _policy, _state, _plan: "pair")
    state = SimpleNamespace(round_hand_play_counts={"PAIR": 1})
    policy = SimpleNamespace(
        EPSILON=1e-9,
        evaluator=SimpleNamespace(project_play=lambda _state, _action: SimpleNamespace(expected_hand_score=125.0)),
        _strategy_fit=lambda _state, _action: (1.0,),
        _within_type_key=lambda _plan: (0,),
    )
    decision = SimpleNamespace(
        action=discard.action,
        selected_plan=discard,
        thresholds=SimpleNamespace(safe_clear_probability_tolerance=0.02),
        pace_target=100.0,
    )
    selected = no_discard._safe_repeat_play(policy, state, (discard, repeat), decision)
    assert selected is not None
    assert selected[2] is repeat


def test_dna_behavior_links_to_rank_requirement_without_pair_table():
    dna = _Node(
        source="DNA",
        bond_ids=("deck_growth",),
        outputs=frozenset(),
        requires=frozenset(),
        scales_with=frozenset(),
        amplifies=frozenset(),
        value=4.0,
    )
    walkie = _Node(
        source="Walkie Talkie",
        bond_ids=("low_ranks",),
        outputs=frozenset({"score:chips"}),
        requires=frozenset({"rank:4", "rank:10"}),
        scales_with=frozenset(),
        amplifies=frozenset(),
        value=4.0,
    )
    assert _relation(dna, walkie) == "CARD_COPY_FEEDS_REQUIRED_RANK"


def test_dna_safe_copy_prefers_required_rank():
    required = SimpleNamespace(
        action=SimpleNamespace(name=PLAY_CARDS, cards=(SimpleNamespace(rank="10", edition=None, seal=None, enhancement=None, permanent_bonus=0),)),
        value=SimpleNamespace(clear_probability=0.95, expected_score=100.0, expected_hands_remaining=3.0),
    )
    irrelevant = SimpleNamespace(
        action=SimpleNamespace(name=PLAY_CARDS, cards=(SimpleNamespace(rank="K", edition=None, seal=None, enhancement=None, permanent_bonus=0),)),
        value=SimpleNamespace(clear_probability=0.99, expected_score=150.0, expected_hands_remaining=3.0),
    )
    decision = SimpleNamespace(
        selected_plan=irrelevant,
        thresholds=SimpleNamespace(safe_clear_probability_tolerance=0.05),
    )
    assert _safe_dna_rank_plan((irrelevant, required), ("4", "10"), decision) is required


def test_live_d13_receives_translated_state(monkeypatch):
    snapshot = LiveBalatroSnapshot(
        sequence=7,
        phase="BLIND_SELECT",
        state_complete=True,
        payload={"blind": {"type": "SMALL"}},
    )
    state = SimpleNamespace(marker="translated")
    observer = SimpleNamespace(observe=lambda: snapshot)
    translator = SimpleNamespace(translate=lambda _snapshot: state)
    captured = {}

    def fake_decide(snapshot_arg, **kwargs):
        captured["snapshot"] = snapshot_arg
        captured["state"] = kwargs.get("state")
        return SimpleNamespace(action_name="SELECT_BLIND", notes=("contextual",))

    monkeypatch.setattr(live_step, "decide_blind_play_or_skip", fake_decide)
    runner = live_step.LiveMemoryInjectedSingleStepRunner(
        observer,
        translator=translator,
        bridge=SimpleNamespace(),
        dispatcher=SimpleNamespace(),
    )
    decision = runner.decide()
    assert captured["state"] is state
    assert decision.state is state
    assert decision.notes == ("contextual",)
