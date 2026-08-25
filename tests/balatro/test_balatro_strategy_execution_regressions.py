from types import SimpleNamespace

import games.balatro.strategy_execution_guard_policy as no_discard
import games.balatro.strategy_resource_coherence_policy as resource_coherence
from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.aces_dna_hand_policy import _safe_dna_rank_plan
from games.balatro.bond_power_engine_retention_policy import _incumbent_realized_bonds
from games.balatro.bonds.behavior_strategy import _Node, _relation
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime import live_memory_autonomous_step_injected as live_step
from games.balatro.strategy_resource_coherence_policy import _strategy_card_need


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
    decision = SimpleNamespace(pace_target=100.0)
    selected = no_discard._safe_pace_play(policy, SimpleNamespace(), (play,), decision)
    assert selected is not None
    assert selected[1] is play


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
    monkeypatch.setattr(no_discard, "_hand_key", lambda _policy, plan: "pair" if plan is repeat else "straight")
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
    monkeypatch.setattr(no_discard, "_hand_key", lambda _policy, _plan: "pair")
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
    assert _safe_dna_rank_plan((irrelevant, required), ("4", "10")) is required


def test_realized_incumbent_bond_protection_is_not_limited_to_top_power_engine():
    incumbent = SimpleNamespace(label="DNA", name="DNA")
    diagnostics = {
        "power_engine": "low_ranks",
        "relevant_bonds": [
            {"bond_id": "low_ranks", "realization": "ACTIVE", "contributors": [{"source": "Walkie Talkie"}]},
            {"bond_id": "deck_growth", "realization": "ACTIVE", "contributors": [{"source": "DNA"}]},
        ],
    }
    protected = _incumbent_realized_bonds(diagnostics, incumbent)
    assert [item["bond_id"] for item in protected] == ["deck_growth"]


def test_r2_partial_power_engine_is_retention_protected():
    incumbent = SimpleNamespace(label="Jolly Joker", name="Jolly Joker")
    diagnostics = {
        "power_engine": "pair",
        "relevant_bonds": [
            {
                "bond_id": "pair",
                "rank_value": 2,
                "realization": "PARTIAL",
                "contributors": [{"source": "Jolly Joker"}],
            },
            {
                "bond_id": "held_cards",
                "rank_value": 2,
                "realization": "PARTIAL",
                "contributors": [{"source": "Raised Fist"}],
            },
        ],
    }

    protected = _incumbent_realized_bonds(diagnostics, incumbent)

    assert [item["bond_id"] for item in protected] == ["pair"]


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


def _standard_policy_profile():
    policy = SimpleNamespace(
        FAMILY_CARD_FEATURE_PREFIXES={"STANDARD": ("rank:",)},
        FAMILY_TRANSFORM_FEATURES={"STANDARD": frozenset()},
    )
    profile = SimpleNamespace(
        enhancement_counts=(),
        seal_counts=(),
        edition_counts=(),
        deck_size=52,
        strength=lambda _feature: 0.0,
        can_produce=lambda _feature: False,
    )
    return policy, profile


def test_standard_pack_need_uses_strategy_scope_instead_of_every_owned_effect(monkeypatch):
    policy, profile = _standard_policy_profile()
    candidate = SimpleNamespace(strategy_id="behavior:low_ranks", prescriptions=("seek_feature:rank:4", "seek_feature:rank:10"))
    monkeypatch.setattr(resource_coherence, "_strategy_candidate", lambda _state: candidate)
    monkeypatch.setattr(resource_coherence, "_strategy_features", lambda _state: ("rank:4", "rank:10"))
    result = _strategy_card_need(policy, SimpleNamespace(), profile, "STANDARD")
    assert result is not None
    need, notes = result
    assert need == 0.5
    joined = " ".join(notes)
    assert "rank:4" in joined and "rank:10" in joined
    assert "rank:A" not in joined


def test_standard_pack_need_is_zero_when_forming_strategy_has_no_card_goal(monkeypatch):
    policy, profile = _standard_policy_profile()
    candidate = SimpleNamespace(strategy_id="behavior:straight+straight_flush", prescriptions=())
    monkeypatch.setattr(resource_coherence, "_strategy_candidate", lambda _state: candidate)
    monkeypatch.setattr(resource_coherence, "_strategy_features", lambda _state: ())
    result = _strategy_card_need(policy, SimpleNamespace(), profile, "STANDARD")
    assert result is not None
    need, notes = result
    assert need == 0.0
    assert "random deck growth" in " ".join(notes)


def test_resource_goals_follow_strongest_committed_strategy_not_container_order(monkeypatch):
    exploratory = SimpleNamespace(
        commitment=0,
        confidence=0.9,
        strength=9.0,
        prescriptions=("seek_feature:rank:A",),
    )
    pinned = SimpleNamespace(
        commitment=2,
        confidence=0.7,
        strength=7.0,
        prescriptions=("seek_feature:rank:4", "seek_feature:rank:10"),
    )
    composition = SimpleNamespace(strategy_candidates=(exploratory, pinned))
    monkeypatch.setattr(
        resource_coherence,
        "evaluate_bond_composition",
        lambda _state: ((), composition),
    )
    assert resource_coherence._strategy_features(SimpleNamespace()) == ("rank:4", "rank:10")
