import pytest

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.build import ContextualConsumableTargetEvaluator
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState
from games.balatro.tarots import TAROT_CARDS


class _Estimator:
    def estimate(self, state, action):
        return 2.0, ("fixture deterministic immediate value",)


def _state():
    state = BalatroState()
    state.phase = "TAROT_PACK"
    state.money = 10
    state.jokers = [object()]
    state.consumables = []
    state.consumable_slots = 2
    return state


def _choice(name: str, index: int = 0) -> LivePackChoice:
    return LivePackChoice(
        area_index=index,
        address=0x1000 + index,
        data={
            "area_index": index,
            "address": 0x1000 + index,
            "live_id": 500 + index,
            "label": name,
            "ability_name": name,
            "ability_set": "Tarot",
        },
    )


def _rank(name: str, state=None):
    choice = _choice(name)
    return BalatroPackPolicy(
        item_estimator=_Estimator(),
        skip_bias=0.35,
    ).rank_actions(
        state or _state(),
        [
            BalatroAction(SELECT_PACK_CARD, target=choice),
            BalatroAction(SKIP_BOOSTER),
        ],
    )


@pytest.mark.parametrize(
    "name",
    sorted(BalatroPackPolicy.STOCHASTIC_DEFERRED_TAROTS),
)
def test_stochastic_deferred_tarots_fail_closed_below_skip(name):
    ranked = _rank(name)

    assert ranked[0].action.name == SKIP_BOOSTER
    tarot = next(
        result
        for result in ranked
        if result.action.name == SELECT_PACK_CARD
    )
    assert tarot.total == -1.0
    assert any(
        note.startswith(f"stochastic Tarot deferred: {name}")
        for note in tarot.notes
    )


@pytest.mark.parametrize(
    "name",
    sorted(BalatroPackPolicy.DETERMINISTIC_IMMEDIATE_TAROTS),
)
def test_usable_deterministic_immediate_tarots_remain_directly_scoreable(name):
    ranked = _rank(name)

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].total == 2.0


def test_unusable_hermit_fails_closed_below_skip():
    state = _state()
    state.money = 0

    ranked = _rank("The Hermit", state)

    assert ranked[0].action.name == SKIP_BOOSTER
    hermit = next(
        result
        for result in ranked
        if result.action.name == SELECT_PACK_CARD
    )
    assert hermit.total == -1.0
    assert any("deterministic immediate Tarot unavailable" in note for note in hermit.notes)


def test_unusable_temperance_fails_closed_below_skip():
    state = _state()
    state.jokers = []

    ranked = _rank("Temperance", state)

    assert ranked[0].action.name == SKIP_BOOSTER
    temperance = next(
        result
        for result in ranked
        if result.action.name == SELECT_PACK_CARD
    )
    assert temperance.total == -1.0
    assert any(
        "deterministic immediate Tarot unavailable" in note
        for note in temperance.notes
    )


def test_tarot_policy_classification_is_exhaustive_and_disjoint():
    fool = {"The Fool"}
    immediate = set(BalatroPackPolicy.DETERMINISTIC_IMMEDIATE_TAROTS)
    modeled_stochastic = set(BalatroPackPolicy.STOCHASTIC_MODELED_TAROTS)
    deferred_stochastic = set(BalatroPackPolicy.STOCHASTIC_DEFERRED_TAROTS)
    targeted = set(ContextualConsumableTargetEvaluator.SUPPORTED_TAROTS)

    buckets = [
        fool,
        immediate,
        modeled_stochastic,
        deferred_stochastic,
        targeted,
    ]
    for index, left in enumerate(buckets):
        for right in buckets[index + 1:]:
            assert left.isdisjoint(right)

    classified = set().union(*buckets)
    assert classified == set(TAROT_CARDS)
    assert classified == set(BalatroPackPolicy.classified_tarots())


def test_safe_immediate_compatibility_alias_excludes_all_stochastic_tarots():
    assert (
        BalatroPackPolicy.SAFE_IMMEDIATE_TAROTS
        == BalatroPackPolicy.DETERMINISTIC_IMMEDIATE_TAROTS
    )
    assert BalatroPackPolicy.SAFE_IMMEDIATE_TAROTS.isdisjoint(
        BalatroPackPolicy.STOCHASTIC_MODELED_TAROTS
    )
    assert BalatroPackPolicy.SAFE_IMMEDIATE_TAROTS.isdisjoint(
        BalatroPackPolicy.STOCHASTIC_DEFERRED_TAROTS
    )


def test_wheel_is_modeled_stochastic_not_deferred():
    assert "The Wheel of Fortune" in BalatroPackPolicy.STOCHASTIC_MODELED_TAROTS
    assert "The Wheel of Fortune" not in BalatroPackPolicy.STOCHASTIC_DEFERRED_TAROTS
