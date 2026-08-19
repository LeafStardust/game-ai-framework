from types import SimpleNamespace

from games.balatro.safe_pace_optimization_policy import (
    _hologram_has_generator,
    _safe_search_schedule,
)


def _state(*joker_names):
    return SimpleNamespace(
        jokers=tuple(SimpleNamespace(name=name) for name in joker_names),
    )


def test_live_safe_search_is_one_shallow_advisory_pass():
    schedule = _safe_search_schedule(
        hands_remaining=4,
        discards_remaining=4,
        max_horizon=8,
        max_nodes=5000,
    )
    assert len(schedule) == 1
    assert schedule[0].horizon == 2
    assert schedule[0].max_nodes == 750
    assert schedule[0].discard_width == 2


def test_safe_search_never_expands_to_engineered_five_action_clear():
    schedule = _safe_search_schedule(
        hands_remaining=4,
        discards_remaining=4,
        max_horizon=5,
        max_nodes=20000,
    )
    assert [item.horizon for item in schedule] == [2]
    assert schedule[0].max_nodes == 750


def test_hologram_alone_has_no_gold_generator_evidence():
    assert not _hologram_has_generator(_state("Hologram"))


def test_hologram_gold_generator_evidence_accepts_repeatable_sources():
    assert _hologram_has_generator(_state("Hologram", "Marble"))
    assert _hologram_has_generator(_state("Hologram", "Certificate"))
    assert _hologram_has_generator(_state("Hologram", "DNA"))
