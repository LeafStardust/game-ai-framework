from dataclasses import replace

from games.balatro.build.effects import EffectDescriptor
from games.balatro.build.profile import (
    BalatroPlaystyleIntentTracker,
    BuildProfile,
)
from games.balatro.joker import Playstyle
from games.balatro.live.build_intent_log import BuildIntentLogTracker


class _Profiler:
    def __init__(self, profile: BuildProfile):
        self.current = profile

    def profile(self, state):
        del state
        return self.current


def _profile(
    *,
    ante: int = 4,
    money: int = 10,
    playstyle: str = Playstyle.FLUSH.value,
) -> BuildProfile:
    return BuildProfile(
        money=money,
        ante=ante,
        joker_slots=5,
        free_joker_slots=4,
        consumable_slots=2,
        free_consumable_slots=2,
        deck_size=52,
        rank_counts=(("A", 4),),
        suit_counts=(("Spades", 13),),
        enhancement_counts=(),
        seal_counts=(),
        edition_counts=(),
        hand_levels=(("FLUSH", 2),),
        joker_names=("TestJoker",),
        consumable_names=(),
        effects=(
            EffectDescriptor(
                source="TestJoker",
                kind="JOKER",
                requires=frozenset({"suit:Spades"}),
                amplifies=frozenset({"hand:FLUSH"}),
            ),
        ),
        feature_strengths=(
            ("hand:FLUSH", 1.0),
            ("suit:Spades", 13.0),
        ),
        playstyle_strengths=((playstyle, 1.0),),
    )


def test_prepare_does_not_consume_event_until_committed():
    profiler = _Profiler(_profile())
    tracker = BuildIntentLogTracker(
        profiler=profiler,
        intent_tracker=BalatroPlaystyleIntentTracker(),
    )

    first = tracker.prepare(object())
    repeated = tracker.prepare(object())

    assert first is not None
    assert repeated is not None
    assert first.payload["transition"] == "INITIAL"
    assert repeated.payload["transition"] == "INITIAL"

    repeated.commit()
    assert tracker.prepare(object()) is None


def test_money_only_change_is_logged_as_context_but_not_as_build_change():
    profiler = _Profiler(_profile(money=10))
    tracker = BuildIntentLogTracker(
        profiler=profiler,
        intent_tracker=BalatroPlaystyleIntentTracker(),
    )

    initial = tracker.prepare(object())
    assert initial is not None
    assert initial.payload["profile"]["money"] == 10
    initial.commit()

    profiler.current = replace(profiler.current, money=17)
    assert tracker.prepare(object()) is None


def test_pivot_and_ante_five_lock_are_reported_without_late_drift():
    profiler = _Profiler(_profile(playstyle=Playstyle.FLUSH.value))
    intent_tracker = BalatroPlaystyleIntentTracker()
    tracker = BuildIntentLogTracker(
        profiler=profiler,
        intent_tracker=intent_tracker,
    )

    initial = tracker.prepare(object())
    assert initial is not None
    initial.commit()

    profiler.current = replace(
        profiler.current,
        playstyle_strengths=((Playstyle.PAIR.value, 1.0),),
    )
    pivot = tracker.prepare(object())
    assert pivot is not None
    assert pivot.payload["transition"] == "PIVOTED"
    assert pivot.payload["intent"]["mode"] == "PIVOTABLE"
    assert pivot.payload["intent"]["strengths"] == {Playstyle.PAIR.value: 1.0}
    pivot.commit()

    profiler.current = replace(profiler.current, ante=5)
    locked = tracker.prepare(object())
    assert locked is not None
    assert locked.payload["transition"] == "LOCKED"
    assert locked.payload["intent"]["mode"] == "LOCKED"
    assert locked.payload["intent"]["lock_ante"] == 5
    locked.commit()

    profiler.current = replace(
        profiler.current,
        ante=6,
        playstyle_strengths=((Playstyle.FLUSH.value, 1.0),),
    )
    later = tracker.prepare(object())
    assert later is not None
    assert later.payload["transition"] == "BUILD_UPDATED"
    assert later.payload["intent"]["strengths"] == {Playstyle.PAIR.value: 1.0}


def test_locked_intent_conflict_is_logged_as_structured_public_evidence():
    profiler = _Profiler(_profile(playstyle=Playstyle.PAIR.value))
    tracker = BuildIntentLogTracker(
        profiler=profiler,
        intent_tracker=BalatroPlaystyleIntentTracker(),
    )

    initial = tracker.prepare(object())
    assert initial is not None
    assert initial.payload["detected_conflicts"] == []
    initial.commit()

    profiler.current = replace(profiler.current, ante=5)
    locked = tracker.prepare(object())
    assert locked is not None
    assert locked.payload["detected_conflicts"] == []
    locked.commit()

    profiler.current = replace(
        profiler.current,
        ante=6,
        playstyle_strengths=((Playstyle.PAIR.value, -1.0),),
    )
    conflict = tracker.prepare(object())

    assert conflict is not None
    assert conflict.payload["intent"]["strengths"] == {Playstyle.PAIR.value: 1.0}
    assert conflict.payload["detected_conflicts"] == [
        {
            "kind": "LOCKED_INTENT_CONFLICT",
            "axis": Playstyle.PAIR.value,
            "committed_strength": 1.0,
            "current_strength": -1.0,
        }
    ]


def test_behavior_backed_supported_interactions_are_logged_as_detected_synergies():
    profiler = _Profiler(_profile())
    tracker = BuildIntentLogTracker(
        profiler=profiler,
        intent_tracker=BalatroPlaystyleIntentTracker(),
    )

    prepared = tracker.prepare(object())

    assert prepared is not None
    assert prepared.payload["detected_synergies"] == [
        {
            "source": "TestJoker",
            "relation": "amplifies",
            "feature": "hand:FLUSH",
            "feature_strength": 1.0,
        },
        {
            "source": "TestJoker",
            "relation": "requires",
            "feature": "suit:Spades",
            "feature_strength": 13.0,
        },
    ]
