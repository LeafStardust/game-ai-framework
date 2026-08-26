from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.live.pack import LivePackChoice
from games.balatro.playbook_pack_policy import PlaybookBalatroPackPolicy
from games.balatro.state import BalatroState


def _judgement_choice() -> LivePackChoice:
    return LivePackChoice(
        area_index=0,
        address=0x1234,
        data={
            "area_index": 0,
            "address": 0x1234,
            "live_id": 77,
            "ability_set": "Tarot",
            "ability_name": "Judgement",
            "label": "Judgement",
            "center": "c_judgement",
        },
    )


def _state(*, owned: int) -> BalatroState:
    state = BalatroState()
    state.phase = "ARCANA_PACK"
    state.joker_slots = 5
    state.jokers = [object() for _ in range(owned)]
    state.joker_generation_pool_observed = True
    joker = {
        "center": "j_joker",
        "label": "Joker",
        "ability_name": "Joker",
        "ability_set": "JOKER",
        "rarity": "COMMON",
    }
    # The base game falls back to Joker when a requested rarity pool is empty, but
    # supplying the same fully modeled public outcome in each rarity keeps this
    # direct pack-policy regression independent of fallback details.
    state.joker_generation_pools = {
        "COMMON": (dict(joker),),
        "UNCOMMON": (dict(joker),),
        "RARE": (dict(joker),),
    }
    state.joker_generation_edition_rate = 1.0
    return state


def test_judgement_beats_skip_when_public_pool_has_positive_joker_and_slot_is_empty():
    state = _state(owned=4)
    choice = _judgement_choice()
    policy = PlaybookBalatroPackPolicy()

    judgement_score = policy.score_action(
        state,
        BalatroAction(SELECT_PACK_CARD, target=choice),
    )
    skip_score = policy.score_action(state, BalatroAction(SKIP_BOOSTER))

    assert judgement_score.total > skip_score.total
    assert any("expected Judgement Joker gain=" in note for note in judgement_score.notes)


def test_judgement_value_does_not_invent_bonus_for_extra_empty_slots():
    choice = _judgement_choice()
    policy = PlaybookBalatroPackPolicy()

    one_slot = policy.score_action(
        _state(owned=4),
        BalatroAction(SELECT_PACK_CARD, target=choice),
    ).total
    three_slots = policy.score_action(
        _state(owned=2),
        BalatroAction(SELECT_PACK_CARD, target=choice),
    ).total

    # Judgement creates exactly one Joker. Additional spare capacity beyond the one
    # required slot is not extra utility and must not receive a synthetic slot bonus.
    assert three_slots == one_slot


def test_judgement_fails_closed_when_roster_is_full():
    state = _state(owned=5)
    choice = _judgement_choice()
    scored = PlaybookBalatroPackPolicy().score_action(
        state,
        BalatroAction(SELECT_PACK_CARD, target=choice),
    )

    assert scored.total < 0.0
    assert any("requires a free Joker slot" in note for note in scored.notes)
