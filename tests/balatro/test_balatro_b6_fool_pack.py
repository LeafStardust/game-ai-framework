from types import SimpleNamespace

import games.balatro.live.pack as pack_module
from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.live.pack import LivePackActionGenerator, LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState


class _Estimator:
    def estimate(self, state, action):
        name = str(getattr(action.target, "name", ""))
        return {
            "The Sun": 4.0,
            "Pluto": 5.0,
        }.get(name, 1.0), (f"fixture copied value={name}",)


def _state():
    state = BalatroState()
    state.phase = "TAROT_PACK"
    state.consumables = []
    state.consumable_slots = 2
    return state


def _choice(last_key=None):
    data = {
        "area_index": 0,
        "address": 0x1000,
        "live_id": 501,
        "label": "The Fool",
        "ability_name": "The Fool",
        "ability_set": "Tarot",
        "center": "c_fool",
    }
    if last_key is not None:
        data["last_tarot_planet"] = last_key
    return LivePackChoice(0, 0x1000, data)


def _rank(state, choice):
    return BalatroPackPolicy(
        item_estimator=_Estimator(),
        skip_bias=0.35,
    ).rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=choice),
            BalatroAction(SKIP_BOOSTER),
        ],
    )


def test_fool_pack_values_exact_public_last_tarot():
    ranked = _rank(_state(), _choice("c_sun"))

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].total == 4.0
    assert any(
        note == "Fool copies public last Tarot/Planet=The Sun"
        for note in ranked[0].notes
    )
    assert any(note == "last_tarot_planet=c_sun" for note in ranked[0].notes)


def test_fool_pack_values_exact_public_last_planet():
    ranked = _rank(_state(), _choice("c_pluto"))

    assert ranked[0].action.name == SELECT_PACK_CARD
    assert ranked[0].total == 5.0
    assert any(
        note == "Fool copies public last Tarot/Planet=Pluto"
        for note in ranked[0].notes
    )


def test_fool_pack_fails_closed_without_public_history():
    ranked = _rank(_state(), _choice())

    assert ranked[0].action.name == SKIP_BOOSTER
    fool = next(result for result in ranked if result.action.name == SELECT_PACK_CARD)
    assert fool.total == -1.0


def test_fool_pack_fails_closed_when_last_card_is_fool():
    ranked = _rank(_state(), _choice("c_fool"))

    assert ranked[0].action.name == SKIP_BOOSTER
    fool = next(result for result in ranked if result.action.name == SELECT_PACK_CARD)
    assert fool.total == -1.0


def test_fool_pack_requires_free_consumable_slot():
    state = _state()
    state.consumable_slots = 1
    state.consumables = [object()]

    ranked = _rank(state, _choice("c_sun"))

    assert ranked[0].action.name == SKIP_BOOSTER
    fool = next(result for result in ranked if result.action.name == SELECT_PACK_CARD)
    assert fool.total == -1.0
    assert any("consumable slots full" in note for note in fool.notes)


def test_fool_pack_fails_closed_for_unknown_center_key():
    ranked = _rank(_state(), _choice("c_not_modeled"))

    assert ranked[0].action.name == SKIP_BOOSTER
    fool = next(result for result in ranked if result.action.name == SELECT_PACK_CARD)
    assert fool.total == -1.0
    assert any("not modeled" in note for note in fool.notes)


def test_live_pack_reader_whitelists_last_tarot_planet(monkeypatch):
    game_table = 100
    pack_table = 200
    cards_table = 201
    root = {
        "GAME": SimpleNamespace(kind="table", value=game_table),
        "pack_cards": SimpleNamespace(kind="table", value=pack_table),
    }

    class _Decoder:
        def string_fields(self, address):
            if address == game_table:
                return {
                    "last_tarot_planet": SimpleNamespace(
                        kind="string",
                        value="c_sun",
                    )
                }
            if address == pack_table:
                return {
                    "cards": SimpleNamespace(kind="table", value=cards_table)
                }
            return {}

    class _Observer:
        def observe(self):
            return SimpleNamespace(phase="TAROT_PACK")

        def _root(self):
            return _Decoder(), 0, root

    monkeypatch.setattr(
        pack_module,
        "_array_table_values",
        lambda decoder, value: [(1, 0x1000)],
    )
    monkeypatch.setattr(
        pack_module,
        "_normalize_item",
        lambda decoder, address, area_index: {
            "area_index": area_index,
            "live_id": 501,
            "label": "The Fool",
            "ability_name": "The Fool",
            "ability_set": "Tarot",
            "center": "c_fool",
        },
    )
    monkeypatch.setattr(
        pack_module,
        "_normalize_card",
        lambda decoder, address: {"value": {}},
    )

    choices = LivePackActionGenerator().read_choices(_Observer())

    assert len(choices) == 1
    assert choices[0].data["last_tarot_planet"] == "c_sun"
