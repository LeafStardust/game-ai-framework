from games.balatro.build.joker_coverage import (
    COVERED,
    UNANALYZED,
    JokerCoverageAuditor,
)
from games.balatro.build.joker_lifecycle import LifecycleJokerBehaviorAnalyzer
from games.balatro.jokers.constellation import ConstellationJoker


def test_inventory_discovers_canonical_balatro_joker_roster_without_claiming_semantic_coverage():
    report = JokerCoverageAuditor().audit(analyze_semantics=False)
    entries = {(entry.module, entry.class_name): entry for entry in report.entries}

    assert len(report.entries) == 150
    assert report.count(UNANALYZED) == 150
    assert "coupon_tag" not in {entry.module for entry in report.entries}
    assert "jokers_apprentice" not in {entry.module for entry in report.entries}

    assert entries[("constellation", "ConstellationJoker")].status == UNANALYZED
    assert entries[("castle", "CastleJoker")].status == UNANALYZED
    assert entries[("castle", "CastleJoker")].required_parameters == ("suit",)
    assert entries[("the_idol", "TheIdolJoker")].status == UNANALYZED
    assert entries[("the_idol", "TheIdolJoker")].required_parameters == ("rank", "suit")
    assert entries[("supernova", "SupernovaJoker")].status == UNANALYZED
    assert entries[("supernova", "SupernovaJoker")].required_parameters == ()
    assert entries[("flat_mult", "FlatMultJoker")].status == UNANALYZED
    assert entries[("flat_mult", "FlatMultJoker")].required_parameters == ()


def test_known_stateful_descriptor_classifies_as_covered():
    auditor = JokerCoverageAuditor()
    descriptor = LifecycleJokerBehaviorAnalyzer().describe(ConstellationJoker())

    entry = auditor._classify("constellation", "ConstellationJoker", descriptor)

    assert entry.status == COVERED
    assert entry.known_features
    assert not entry.unknown_signals
