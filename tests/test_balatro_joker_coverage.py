from games.balatro.build.joker_coverage import (
    COVERED,
    PARAMETERIZED,
    UNANALYZED,
    JokerCoverageAuditor,
)
from games.balatro.build.joker_lifecycle import LifecycleJokerBehaviorAnalyzer
from games.balatro.jokers.constellation import ConstellationJoker


def test_inventory_discovers_repository_jokers_without_claiming_semantic_coverage():
    report = JokerCoverageAuditor().audit(analyze_semantics=False)
    entries = {(entry.module, entry.class_name): entry for entry in report.entries}

    assert entries[("constellation", "ConstellationJoker")].status == UNANALYZED
    assert entries[("castle", "CastleJoker")].status == PARAMETERIZED
    assert "suit" in entries[("castle", "CastleJoker")].required_parameters
    assert entries[("supernova", "SupernovaJoker")].status == PARAMETERIZED
    assert "poker_hand" in entries[("supernova", "SupernovaJoker")].required_parameters


def test_known_stateful_descriptor_classifies_as_covered():
    auditor = JokerCoverageAuditor()
    descriptor = LifecycleJokerBehaviorAnalyzer().describe(ConstellationJoker())

    entry = auditor._classify("constellation", "ConstellationJoker", descriptor)

    assert entry.status == COVERED
    assert entry.known_features
    assert not entry.unknown_signals
