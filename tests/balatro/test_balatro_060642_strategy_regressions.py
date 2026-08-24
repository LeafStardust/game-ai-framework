from types import SimpleNamespace

import games.balatro.latest_batch_no_discard_policy as no_discard
from games.balatro.bond_power_engine_retention_policy import _incumbent_realized_bonds
from games.balatro.bonds.behavior_strategy import _Node, _relation
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime import live_memory_autonomous_step_injected as live_step
from games.balatro.strategy_resource_coherence_policy import _strategy_card_need


def test_active_no_discard_engine_recognizes_green_joker(monkeypatch):
    monkeypatch.setattr(
        no_discard,
        "bond_strategy_diagnostics",
        lambda _state: {
            "relevant_bonds": [
                {"bond_id": "no_discard", "realization": "ACTIVE"},
            ]
        },
    )
    state = SimpleNamespace(
        jokers=[SimpleNamespace(label="Green Joker")],
    )
    assert no_discard._realized_no_discard_engine(state) is True


def test_active_no_discard_engine_recognizes_delayed_without_banner(monkeypatch):
    monkeypatch.setattr(
        no_discard,
        "bond_strategy_diagnostics",
        lambda _state: {
            "relevant_bonds": [
                {"bond_id": "no_discard", "realization": "ACTIVE"},
            ]
        },
    )
    state = SimpleNamespace(
        jokers=[SimpleNamespace(label="Delayed Gratification")],
    )
    assert no_discard._realized_no_discard_engine(state) is True


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


def test_realized_incumbent_bond_protection_is_not_limited_to_top_power_engine():
    incumbent = SimpleNamespace(label="DNA", name="DNA")
    diagnostics = {
        "power_engine": "low_ranks",
        "relevant_bonds": [
            {
                "bond_id": "low_ranks",
                "realization": "ACTIVE",
                "contributors": [{"source": "Walkie Talkie"}],
            },
            {
                "bond_id": "deck_growth",
                "realization": "ACTIVE",
                "contributors": [{"source": "DNA"}],
            },
        ],
    }
    protected = _incumbent_realized_bonds(diagnostics, incumbent)
    assert [item["bond_id"] for item in protected] == ["deck_growth"]


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


def test_standard_pack_need_uses_strategy_scope_instead_of_every_owned_effect(monkeypatch):
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
    monkeypatch.setattr(
        "games.balatro.strategy_resource_coherence_policy._strategy_features",
        lambda _state: ("rank:4", "rank:10"),
    )
    result = _strategy_card_need(policy, SimpleNamespace(), profile, "STANDARD")
    assert result is not None
    need, notes = result
    assert need == 0.5
    joined = " ".join(notes)
    assert "rank:4" in joined and "rank:10" in joined
    assert "rank:A" not in joined
