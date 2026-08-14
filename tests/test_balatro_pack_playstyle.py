from games.balatro.actions import SELECT_PACK_CARD, BalatroAction
from games.balatro.consumable import PlanetCard
from games.balatro.joker import (
    Joker,
    JokerContext,
    Playstyle,
    PlaystyleAffinity,
)
from games.balatro.jokers.business_card import BusinessCardJoker
from games.balatro.jokers.ride_the_bus import RideTheBusJoker
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_playstyle import PackPlaystyleEvaluator
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState


class FlushAlignedJoker(Joker):
    playstyle_affinities = {
        Playstyle.FLUSH: PlaystyleAffinity.POSITIVE,
        Playstyle.PAIR: PlaystyleAffinity.NEGATIVE,
    }

    def apply(self, context: JokerContext) -> JokerContext:
        return context


class _NoPlayingCardContext:
    def evaluate(self, state, **kwargs):
        del state, kwargs
        return type("Evaluation", (), {"total_gain": 0.0, "rationale": ()})()


def _state(ante: int, *jokers: Joker) -> BalatroState:
    state = BalatroState()
    state.ante = ante
    state.jokers = list(jokers)
    state.phase = "STANDARD_PACK"
    return state


def _playing_choice(rank: str, suit: str, index: int = 0) -> LivePackChoice:
    return LivePackChoice(
        area_index=index,
        address=1000 + index,
        data={
            "ability_set": "PLAYING_CARD",
            "value": {"rank": rank, "suit": suit},
            "modifier": {},
        },
    )


def test_planet_direct_signal_follows_hand_type_intent():
    evaluator = PackPlaystyleEvaluator()
    state = _state(4, FlushAlignedJoker())

    flush = evaluator.evaluate(
        state,
        kind="PLANET",
        target=PlanetCard("Jupiter", "FLUSH", 15, 2),
    )
    pair = evaluator.evaluate(
        state,
        kind="PLANET",
        target=PlanetCard("Mercury", "PAIR", 15, 1),
    )

    assert flush.intent.locked is False
    assert flush.fit > 0.0
    assert flush.value > 0.0
    assert pair.fit < 0.0
    assert pair.value < 0.0


def test_playing_card_signal_follows_face_and_suit_intent():
    evaluator = PackPlaystyleEvaluator()
    face_state = _state(4, BusinessCardJoker())
    no_face_state = _state(4, RideTheBusJoker())

    face = evaluator.evaluate(
        face_state,
        kind="PLAYING_CARD",
        rank="K",
        suit="Hearts",
    )
    non_face = evaluator.evaluate(
        face_state,
        kind="PLAYING_CARD",
        rank="2",
        suit="Hearts",
    )
    ride_face = evaluator.evaluate(
        no_face_state,
        kind="PLAYING_CARD",
        rank="Q",
        suit="Clubs",
    )
    ride_non_face = evaluator.evaluate(
        no_face_state,
        kind="PLAYING_CARD",
        rank="7",
        suit="Clubs",
    )

    assert face.value > non_face.value
    assert ride_non_face.value > ride_face.value


def test_pack_intent_remains_pivotable_at_four_then_locks_at_five():
    evaluator = PackPlaystyleEvaluator()

    early = evaluator.evaluate(
        _state(4, RideTheBusJoker()),
        kind="PLAYING_CARD",
        rank="2",
        suit="Spades",
    )
    pivot = evaluator.evaluate(
        _state(4, BusinessCardJoker()),
        kind="PLAYING_CARD",
        rank="K",
        suit="Spades",
    )
    locked = evaluator.evaluate(
        _state(5, BusinessCardJoker()),
        kind="PLAYING_CARD",
        rank="K",
        suit="Spades",
    )
    later_conflicting_build = evaluator.evaluate(
        _state(6, RideTheBusJoker()),
        kind="PLAYING_CARD",
        rank="K",
        suit="Spades",
    )

    assert early.intent.locked is False
    assert early.value > 0.0
    assert pivot.intent.locked is False
    assert pivot.value > 0.0
    assert locked.intent.locked is True
    assert locked.value > 0.0
    assert later_conflicting_build.intent.locked is True
    assert later_conflicting_build.value > 0.0


def test_joker_and_unmodeled_consumables_do_not_receive_direct_pack_bonus():
    evaluator = PackPlaystyleEvaluator()
    state = _state(5, RideTheBusJoker())

    joker = evaluator.evaluate(state, kind="JOKER", target=BusinessCardJoker())
    tarot = evaluator.evaluate(state, kind="TAROT", target=object())
    spectral = evaluator.evaluate(state, kind="SPECTRAL", target=object())

    assert joker.value == 0.0
    assert tarot.value == 0.0
    assert spectral.value == 0.0
    assert any("already included by D2" in note for note in joker.rationale)


def test_pack_policy_applies_direct_playstyle_to_playing_card_ranking():
    evaluator = PackPlaystyleEvaluator()
    policy = BalatroPackPolicy(
        playing_card_build=_NoPlayingCardContext(),
        playstyle_evaluator=evaluator,
    )
    state = _state(4, RideTheBusJoker())
    face = _playing_choice("K", "Hearts", 0)
    non_face = _playing_choice("2", "Hearts", 1)

    ranked = policy.rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=face),
            BalatroAction(SELECT_PACK_CARD, target=non_face),
        ],
    )

    assert ranked[0].action.target is non_face
    assert ranked[0].total > ranked[1].total
    assert any(note.startswith("D4 playstyle fit=") for note in ranked[0].notes)
