from games.balatro.card import BalatroCard
from games.balatro.live.consumable_timing import HOLD, USE, LiveConsumableTimingPolicy
from games.balatro.live.external.live_memory_observer import snapshot_payload_from_live_memory
from games.balatro.live.external.luajit_memory import LuaValue
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.planets import create_planet
from games.balatro.state import BalatroState
from games.balatro.tarots import Fool


class _Blind:
    def __init__(self, requirement: int):
        self.requirement = requirement

    def copy(self):
        return _Blind(self.requirement)


class _Decoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return self.tables.get(address, {})

    def array_items(self, address):
        return ()


def _table(address):
    return LuaValue("table", address, 0)


def _string(value):
    return LuaValue("string", value, 0)


def _number(value):
    return LuaValue("number", float(value), 0)


def _boolean(value):
    return LuaValue("boolean", bool(value), 0)


def _state(cards, *, hands_remaining=4, requirement=100_000):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = [
        BalatroCard(
            card.rank,
            card.suit,
            card.enhancement,
            card.edition,
            card.seal,
            card.live_id,
        )
        for card in cards
    ]
    state.hands_remaining = hands_remaining
    state.score = 0
    state.blind = _Blind(requirement)
    return state


def test_live_snapshot_whitelists_public_last_tarot_planet():
    game = 100
    states = 101
    decoder = _Decoder(
        {
            game: {
                "last_tarot_planet": _string("c_strength"),
                "secret_rng": _table(999),
            },
            states: {"SELECTING_HAND": _number(1)},
        }
    )
    root = {
        "GAME": _table(game),
        "STATE": _number(1),
        "STATE_COMPLETE": _boolean(True),
        "STATES": _table(states),
    }

    payload, phase, complete = snapshot_payload_from_live_memory(decoder, root)

    assert phase == "SELECTING_HAND"
    assert complete is True
    assert payload["last_tarot_planet"] == "c_strength"
    assert "secret_rng" not in payload
    assert payload["hidden_rng_exposed"] is False
    assert payload["hidden_draw_order_exposed"] is False


def test_translator_and_state_copy_preserve_last_tarot_planet():
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={"last_tarot_planet": "c_hermit"},
    )

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.last_tarot_planet == "c_hermit"
    assert state.copy().last_tarot_planet == "c_hermit"


def test_held_fool_fails_closed_without_valid_public_history():
    for last_key in (None, "c_fool", "c_not_modeled"):
        state = _state([BalatroCard("2", "Hearts")])
        fool = Fool()
        state.consumables = [fool]
        state.last_tarot_planet = last_key

        recommendation = LiveConsumableTimingPolicy().recommend(state, fool)

        assert recommendation.decision == HOLD
        assert recommendation.target is None
        assert recommendation.to_action() is None


def test_held_fool_materializes_peak_hermit_without_requiring_free_slot():
    state = _state([BalatroCard("2", "Hearts")])
    fool = Fool()
    state.money = 10
    state.consumables = [fool]
    state.consumable_slots = 1
    state.last_tarot_planet = "c_hermit"

    recommendation = LiveConsumableTimingPolicy().recommend(state, fool)

    assert recommendation.decision == USE
    assert recommendation.target is None
    assert recommendation.before_projection is None
    assert recommendation.after_projection is None
    assert any("The Hermit" in note for note in recommendation.rationale)
    assert any("fresh observation" in note for note in recommendation.rationale)

    action = recommendation.to_action()
    assert action is not None
    assert action.target is fool
    assert action.cards == []


def test_held_fool_preserves_option_when_copied_hermit_should_hold():
    state = _state([BalatroCard("2", "Hearts")])
    fool = Fool()
    state.money = 6
    state.consumables = [fool]
    state.consumable_slots = 2
    state.last_tarot_planet = "c_hermit"

    recommendation = LiveConsumableTimingPolicy().recommend(state, fool)

    assert recommendation.decision == HOLD
    assert recommendation.target is None
    assert any("no concrete modeled use now" in note for note in recommendation.rationale)


def test_held_fool_can_prepare_targeted_tarot_but_does_not_copy_its_targets():
    first = BalatroCard("2", "Hearts")
    second = BalatroCard("3", "Clubs")
    state = _state([first, second], hands_remaining=1)
    fool = Fool()
    state.consumables = [fool]
    state.last_tarot_planet = "c_strength"

    recommendation = LiveConsumableTimingPolicy().recommend(state, fool)

    assert recommendation.decision == USE
    assert recommendation.target is None
    action = recommendation.to_action()
    assert action is not None
    assert action.target is fool
    assert action.cards == []
    assert any("Strength" in note for note in recommendation.rationale)
    assert any("follow-up action chaining remains disabled" in note for note in recommendation.rationale)


def test_planet_timing_uses_final_hand_upgrade_and_is_targetless():
    state = _state(
        [BalatroCard("K", "Hearts"), BalatroCard("K", "Clubs")],
        hands_remaining=1,
    )
    mercury = create_planet("MERCURY")
    state.consumables = [mercury]

    recommendation = LiveConsumableTimingPolicy().recommend(state, mercury)

    assert recommendation.decision == USE
    assert recommendation.target is None
    assert recommendation.after_projection is not None
    assert (
        recommendation.after_projection.expected_hand_score
        > recommendation.before_projection.expected_hand_score
    )
    action = recommendation.to_action()
    assert action is not None
    assert action.target is mercury
    assert action.cards == []


def test_held_fool_can_prepare_public_planet_copy_for_next_step():
    state = _state(
        [BalatroCard("K", "Hearts"), BalatroCard("K", "Clubs")],
        hands_remaining=1,
    )
    fool = Fool()
    state.consumables = [fool]
    state.last_tarot_planet = "c_mercury"

    recommendation = LiveConsumableTimingPolicy().recommend(state, fool)

    assert recommendation.decision == USE
    assert recommendation.target is None
    assert any("Mercury" in note for note in recommendation.rationale)
    action = recommendation.to_action()
    assert action is not None
    assert action.target is fool
    assert action.cards == []
