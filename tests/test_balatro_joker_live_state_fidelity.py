from games.balatro.build.joker_live_state_fidelity import (
    ERROR,
    GAP,
    HYDRATED,
    STATELESS,
    JokerLiveStateFidelityAuditor,
)
from games.balatro.jokers.cavendish import CavendishJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.glass_joker import GlassJoker
from games.balatro.jokers.gros_michel import GrosMichelJoker
from games.balatro.jokers.ice_cream import IceCreamJoker
from games.balatro.jokers.runner import RunnerJoker


def test_mutable_field_detection_ignores_constructor_only_configuration():
    auditor = JokerLiveStateFidelityAuditor()

    assert auditor._mutable_instance_fields(FlatMultJoker) == frozenset()
    assert auditor._mutable_instance_fields(RunnerJoker) == frozenset({"chips"})
    assert auditor._mutable_instance_fields(IceCreamJoker) == frozenset({"chips"})
    assert auditor._mutable_instance_fields(GlassJoker) == frozenset({"x_mult"})


def test_live_state_contract_covers_all_mutable_joker_model_fields():
    report = JokerLiveStateFidelityAuditor().audit()
    entries = {(entry.module, entry.class_name): entry for entry in report.entries}

    assert entries[("flat_mult", "FlatMultJoker")].status == STATELESS
    assert entries[("glass_joker", "GlassJoker")].status == HYDRATED
    assert entries[("ice_cream", "IceCreamJoker")].status == HYDRATED
    assert entries[("runner", "RunnerJoker")].status == HYDRATED

    cavendish = entries[("cavendish", "CavendishJoker")]
    gros_michel = entries[("gros_michel", "GrosMichelJoker")]
    assert cavendish.status == HYDRATED
    assert cavendish.derived_fields == ("active",)
    assert gros_michel.status == HYDRATED
    assert gros_michel.derived_fields == ("destroyed",)

    assert report.count(GAP) == 0
    assert report.count(ERROR) == 0
