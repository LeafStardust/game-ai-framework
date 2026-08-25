from dataclasses import replace

from games.balatro.build.effects import EffectDescriptor
from games.balatro.build.profile import BuildProfile
from games.balatro.live.bond_build_log import BondBuildLogTracker


class _Profiler:
    def __init__(self, profile: BuildProfile):
        self.current = profile

    def profile(self, state):
        del state
        return self.current


class _Diagnostics:
    def __init__(self):
        self.pinned = None

    def __call__(self, state):
        del state
        candidates = []
        if self.pinned is not None:
            candidates.append(
                {
                    "strategy_id": self.pinned,
                    "commitment": "APPLIED",
                    "pinned": True,
                }
            )
        return {
            "pinned_strategy": self.pinned,
            "strategy_candidates": candidates,
            "relevant_bonds": [],
            "composition": {"conflicts": [], "synergies": []},
        }


def _profile(*, ante: int = 4, money: int = 10) -> BuildProfile:
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
    )


def _tracker(profiler, diagnostics=None):
    return BondBuildLogTracker(
        profiler=profiler,
        strategy_diagnostics=diagnostics or _Diagnostics(),
    )


def test_prepare_does_not_consume_event_until_committed():
    tracker = _tracker(_Profiler(_profile()))

    first = tracker.prepare(object())
    repeated = tracker.prepare(object())

    assert first is not None
    assert repeated is not None
    assert first.payload["transition"] == "INITIAL"
    assert repeated.payload["transition"] == "INITIAL"

    repeated.commit()
    assert tracker.prepare(object()) is None


def test_money_only_change_is_context_not_structural_build_change():
    profiler = _Profiler(_profile(money=10))
    tracker = _tracker(profiler)
    initial = tracker.prepare(object())
    assert initial is not None
    initial.commit()

    profiler.current = replace(profiler.current, money=17)
    assert tracker.prepare(object()) is None


def test_canonical_strategy_change_is_reported_without_irreversible_lock():
    profiler = _Profiler(_profile())
    diagnostics = _Diagnostics()
    tracker = _tracker(profiler, diagnostics)
    initial = tracker.prepare(object())
    assert initial is not None
    initial.commit()

    diagnostics.pinned = "pair_engine"
    changed = tracker.prepare(object())

    assert changed is not None
    assert changed.payload["transition"] == "STRATEGY_CHANGED"
    assert changed.payload["bond_strategy"]["pinned_strategy"] == "pair_engine"
    assert "intent" not in changed.payload


def test_behavior_backed_supported_interactions_are_logged():
    prepared = _tracker(_Profiler(_profile())).prepare(object())

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
