from games.balatro.build.joker_live_state_fidelity import (
    GAP,
    HYDRATED,
    STATELESS,
    JokerLiveStateFidelityAuditor,
)
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.ice_cream import IceCreamJoker
from games.balatro.jokers.runner import RunnerJoker


def test_mutable_field_detection_ignores_constructor_only_configuration():
    auditor = JokerLiveStateFidelityAuditor()

    assert auditor._mutable_instance_fields(FlatMultJoker) == frozenset()
    assert auditor._mutable_instance_fields(RunnerJoker) == frozenset({"chips"})
    assert auditor._mutable_instance_fields(IceCreamJoker) == frozenset({"chips"})


def test_current_contract_distinguishes_hydrated_and_missing_live_state():
    report = JokerLiveStateFidelityAuditor().audit()
    entries = {(entry.module, entry.class_name): entry for entry in report.entries}

    assert entries[("flat_mult", "FlatMultJoker")].status == STATELESS
    assert entries[("ice_cream", "IceCreamJoker")].status == HYDRATED

    runner = entries[("runner", "RunnerJoker")]
    assert runner.status == GAP
    assert runner.mutable_fields == ("chips",)
    assert runner.missing_fields == ("chips",)
