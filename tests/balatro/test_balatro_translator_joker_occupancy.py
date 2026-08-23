from types import SimpleNamespace

from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator


def _snapshot(*, joker_count: int, joker_limit: int, card_count: int | None = None) -> LiveBalatroSnapshot:
    visible = joker_count if card_count is None else card_count
    return LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload={
            "money": 20,
            "jokers": {
                "cards": [
                    {"ability_name": f"Owned {index}", "live_id": index + 1}
                    for index in range(visible)
                ],
                "count": joker_count,
                "limit": joker_limit,
            },
            "consumables": {"cards": [], "count": 0, "limit": 2},
            "shop_jokers": {"cards": [], "count": 0, "limit": 2},
            "shop_boosters": {"cards": [], "count": 0, "limit": 2},
            "shop_vouchers": {"cards": [], "count": 0, "limit": 1},
        },
    )


def _translator_with_modeled_count(modeled_count: int) -> DefaultBalatroStateTranslator:
    translator = DefaultBalatroStateTranslator()
    calls = {"count": 0}

    def create(_data):
        index = calls["count"]
        calls["count"] += 1
        if index >= modeled_count:
            return None
        return SimpleNamespace(live_id=index + 1)

    translator.joker_factory = SimpleNamespace(create=create)
    return translator


def test_unmodeled_owned_jokers_reserve_their_authoritative_slots():
    state = _translator_with_modeled_count(5).translate(
        _snapshot(joker_count=6, joker_limit=6)
    )

    assert len(state.jokers) == 5
    assert state.joker_slots == 5
    assert state.joker_slots - len(state.jokers) == 0


def test_unmodeled_owned_jokers_preserve_authoritative_free_slot_count():
    state = _translator_with_modeled_count(4).translate(
        _snapshot(joker_count=5, joker_limit=6)
    )

    assert len(state.jokers) == 4
    assert state.joker_slots == 5
    assert state.joker_slots - len(state.jokers) == 1


def test_fully_modeled_roster_keeps_authoritative_limit_unchanged():
    state = _translator_with_modeled_count(6).translate(
        _snapshot(joker_count=6, joker_limit=6)
    )

    assert len(state.jokers) == 6
    assert state.joker_slots == 6
    assert state.joker_slots - len(state.jokers) == 0


def test_authoritative_count_reserves_transitioning_joker_not_yet_in_card_list():
    state = _translator_with_modeled_count(5).translate(
        _snapshot(joker_count=6, joker_limit=6, card_count=5)
    )

    # Balatro's area count is the same capacity authority used by the injected
    # bridge. A temporarily lagging normalized card list must not invent a free slot.
    assert len(state.jokers) == 5
    assert state.joker_slots == 5
    assert state.joker_slots - len(state.jokers) == 0
