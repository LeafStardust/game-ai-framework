from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.build.profile import (
    BalatroBuildProfiler,
    BalatroPlaystyleIntentTracker,
)
from games.balatro.joker import (
    Joker,
    JokerContext,
    Playstyle,
    PlaystyleAffinity,
)
from games.balatro.jokers.business_card import BusinessCardJoker
from games.balatro.jokers.ride_the_bus import RideTheBusJoker
from games.balatro.state import BalatroState


class FaceAlignedJoker(Joker):
    playstyle_affinities = {
        Playstyle.FACE_CARDS: PlaystyleAffinity.POSITIVE,
        Playstyle.NO_FACE_CARDS: PlaystyleAffinity.NEGATIVE,
    }

    def apply(self, context: JokerContext) -> JokerContext:
        return context


class NoFaceAlignedJoker(Joker):
    playstyle_affinities = {
        Playstyle.NO_FACE_CARDS: PlaystyleAffinity.POSITIVE,
        Playstyle.FACE_CARDS: PlaystyleAffinity.NEGATIVE,
    }

    def apply(self, context: JokerContext) -> JokerContext:
        return context


def _state(ante: int, *jokers: Joker) -> BalatroState:
    state = BalatroState()
    state.ante = ante
    state.jokers = list(jokers)
    return state


def test_joker_files_declare_opposed_face_card_affinities():
    ride = RideTheBusJoker()
    business = BusinessCardJoker()

    assert ride.playstyle_affinity(Playstyle.NO_FACE_CARDS) == PlaystyleAffinity.POSITIVE
    assert ride.playstyle_affinity(Playstyle.FACE_CARDS) == PlaystyleAffinity.NEGATIVE
    assert business.playstyle_affinity(Playstyle.FACE_CARDS) == PlaystyleAffinity.POSITIVE
    assert business.playstyle_affinity(Playstyle.NO_FACE_CARDS) == PlaystyleAffinity.NEGATIVE
    assert ride.playstyle_affinity(Playstyle.DIAMONDS) is None


def test_ante_four_remains_pivotable_and_ante_five_locks():
    profiler = BalatroBuildProfiler()
    tracker = BalatroPlaystyleIntentTracker()

    early = tracker.resolve(profiler.profile(_state(1, RideTheBusJoker())))
    assert early.locked is False
    assert early.strength(Playstyle.NO_FACE_CARDS) > 0.0
    assert early.strength(Playstyle.FACE_CARDS) < 0.0

    # Ante 4 is still allowed to reverse direction completely.
    ante_four = tracker.resolve(profiler.profile(_state(4, BusinessCardJoker())))
    assert ante_four.locked is False
    assert ante_four.strength(Playstyle.FACE_CARDS) > 0.0
    assert ante_four.strength(Playstyle.NO_FACE_CARDS) < 0.0

    ante_five = tracker.resolve(profiler.profile(_state(5, BusinessCardJoker())))
    assert ante_five.locked is True
    assert ante_five.lock_ante == 5
    assert ante_five.strength(Playstyle.FACE_CARDS) > 0.0

    # Once locked, later ownership changes cannot silently redefine the run.
    later = tracker.resolve(profiler.profile(_state(6, RideTheBusJoker())))
    assert later.locked is True
    assert later.strength(Playstyle.FACE_CARDS) > 0.0
    assert later.strength(Playstyle.NO_FACE_CARDS) < 0.0


def test_ante_five_uses_recent_direction_if_current_affinities_cancel():
    profiler = BalatroBuildProfiler()
    tracker = BalatroPlaystyleIntentTracker()

    tracker.resolve(profiler.profile(_state(4, RideTheBusJoker())))
    locked = tracker.resolve(
        profiler.profile(
            _state(5, RideTheBusJoker(), BusinessCardJoker())
        )
    )

    assert locked.locked is True
    assert locked.strength(Playstyle.NO_FACE_CARDS) > 0.0
    assert locked.strength(Playstyle.FACE_CARDS) < 0.0


def test_d2_conflict_penalty_becomes_stronger_after_ante_five_lock():
    evaluator = JokerBuildValueEvaluator()

    ante_four = evaluator.evaluate(
        _state(4, RideTheBusJoker()),
        FaceAlignedJoker(),
    )
    assert ante_four.playstyle_locked is False
    assert ante_four.playstyle_fit < 0.0
    assert ante_four.playstyle_value == -4.0

    # The same evaluator captures the no-face direction when Ante 5 is reached.
    evaluator.evaluate(
        _state(5, RideTheBusJoker()),
        NoFaceAlignedJoker(),
    )

    # Even if Ride the Bus is subsequently gone, the committed direction survives.
    conflict = evaluator.evaluate(
        _state(6, BusinessCardJoker()),
        FaceAlignedJoker(),
    )
    aligned = evaluator.evaluate(
        _state(6, BusinessCardJoker()),
        NoFaceAlignedJoker(),
    )

    assert conflict.playstyle_locked is True
    assert conflict.playstyle_fit < 0.0
    assert conflict.playstyle_value == -8.0
    assert aligned.playstyle_fit > 0.0
    assert aligned.playstyle_value == 4.0


def test_reset_starts_a_fresh_run_without_inheriting_commitment():
    evaluator = JokerBuildValueEvaluator()
    evaluator.evaluate(
        _state(5, RideTheBusJoker()),
        NoFaceAlignedJoker(),
    )

    evaluator.reset_playstyle_intent()
    fresh = evaluator.evaluate(
        _state(1, BusinessCardJoker()),
        FaceAlignedJoker(),
    )

    assert fresh.playstyle_locked is False
    assert fresh.playstyle_fit > 0.0
    assert fresh.playstyle_value == 1.0
