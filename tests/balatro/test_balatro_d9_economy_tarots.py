from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.consumable import ConsumableContext
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState
from games.balatro.tarots import create_tarot


def _choice(label: str) -> LivePackChoice:
    data = {
        "area_index": 0,
        "address": 0x1000,
        "live_id": 500,
        "label": label,
        "ability_name": label,
        "ability_set": "Tarot",
    }
    return LivePackChoice(
        area_index=0,
        address=0x1000,
        data=data,
    )


def _rank(state: BalatroState, label: str):
    return BalatroPackPolicy(skip_bias=0.35).rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=_choice(label)),
            BalatroAction(SKIP_BOOSTER),
        ],
    )


def test_hermit_caps_money_gain_at_twenty_not_total_money():
    state = BalatroState()
    state.money = 25

    result = create_tarot("The Hermit").use(ConsumableContext(state=state))

    assert result.state.money == 45
    assert result.data["money_before"] == 25
    assert result.data["money_after"] == 45
    assert result.data["money"] == 20


def test_temperance_adds_public_joker_sell_value_capped_at_fifty():
    state = BalatroState()
    state.money = 7
    state.jokers = [
        SimpleNamespace(sell_value=12),
        SimpleNamespace(sell_value=45),
    ]

    result = create_tarot("Temperance").use(ConsumableContext(state=state))

    assert result.state.money == 57
    assert result.data["money"] == 50


def test_d9_hermit_values_twenty_dollar_gain_above_twenty_cash():
    state = BalatroState()
    state.phase = "TAROT_PACK"
    state.money = 25

    ranked = _rank(state, "The Hermit")

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].total > 0.35
    assert any(
        "Hermit deterministic money gain=20" in note
        for note in ranked[0].notes
    )


def test_d9_temperance_values_public_joker_sell_value_capped_at_fifty():
    state = BalatroState()
    state.phase = "TAROT_PACK"
    state.jokers = [
        SimpleNamespace(sell_value=12),
        SimpleNamespace(sell_value=45),
    ]

    ranked = _rank(state, "Temperance")

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].total > 0.35
    assert any(
        "Temperance deterministic money gain=50" in note
        for note in ranked[0].notes
    )
    assert any(
        "public Joker sell value=57" in note
        for note in ranked[0].notes
    )
