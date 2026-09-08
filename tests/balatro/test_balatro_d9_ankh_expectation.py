from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.build.ankh_expectation import AnkhExpectationEvaluator
from games.balatro.consumable import ConsumableContext
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.spectrals import Ankh
from games.balatro.state import BalatroState


class _FirstChoiceRng:
    @staticmethod
    def choice(values):
        return values[0]


def _choice() -> LivePackChoice:
    data = {
        "area_index": 0,
        "address": 0x1000,
        "live_id": 500,
        "label": "Ankh",
        "ability_name": "Ankh",
        "ability_set": "Spectral",
    }
    return LivePackChoice(area_index=0, address=0x1000, data=data)


def _rank(state: BalatroState):
    return BalatroPackPolicy(skip_bias=0.35).rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=_choice()),
            BalatroAction(SKIP_BOOSTER),
        ],
    )


def test_ankh_keeps_chosen_joker_and_created_copy():
    chosen = FlatMultJoker(4)
    destroyed = FlatMultJoker(1)
    state = BalatroState()
    state.jokers = [chosen, destroyed]
    context = ConsumableContext(state=state, data={"rng": _FirstChoiceRng()})

    result = Ankh().use(context)

    assert len(result.state.jokers) == 2
    assert result.state.jokers[0] is chosen
    assert result.state.jokers[1] is not chosen
    assert isinstance(result.state.jokers[1], FlatMultJoker)
    assert result.state.jokers[1].mult == chosen.mult
    assert destroyed not in result.state.jokers


def test_ankh_copy_does_not_inherit_negative_edition():
    chosen = FlatMultJoker(4)
    chosen.edition = "Negative"
    state = BalatroState()
    state.jokers = [chosen]
    context = ConsumableContext(state=state, data={"rng": _FirstChoiceRng()})

    result = Ankh().use(context)

    assert len(result.state.jokers) == 2
    assert result.state.jokers[0].edition == "Negative"
    assert result.state.jokers[1].edition is None


def test_ankh_preserves_other_eternal_jokers_when_field_is_available():
    chosen = FlatMultJoker(4)
    eternal = FlatMultJoker(2)
    eternal.eternal = True
    destroyed = FlatMultJoker(1)
    state = BalatroState()
    state.jokers = [chosen, eternal, destroyed]
    context = ConsumableContext(state=state, data={"rng": _FirstChoiceRng()})

    result = Ankh().use(context)

    assert len(result.state.jokers) == 3
    assert chosen in result.state.jokers
    assert eternal in result.state.jokers
    assert destroyed not in result.state.jokers


def test_d9_ankh_single_joker_has_positive_b3_expected_value():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.jokers = [FlatMultJoker(4)]

    expectation = AnkhExpectationEvaluator().evaluate(state)
    ranked = _rank(state)

    assert expectation.available
    assert expectation.complete
    assert expectation.branch_count == 1
    assert expectation.expected_build_gain > 0.35
    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].total == expectation.expected_build_gain
    assert any(
        "Ankh uses analytic B3 whole-build expectation" in note
        for note in ranked[0].notes
    )


def test_d9_ankh_without_jokers_fails_closed_to_skip():
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"

    expectation = AnkhExpectationEvaluator().evaluate(state)
    ranked = _rank(state)

    assert not expectation.available
    assert expectation.complete
    assert ranked[0].action.name == SKIP_BOOSTER
    ankh = next(result for result in ranked if result.action.name == SELECT_PACK_CARD)
    assert ankh.total == -1.0
    assert any("Ankh unavailable" in note for note in ankh.notes)
