from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.playbook_pack_policy import PlaybookBalatroPackPolicy
from games.balatro.state import BalatroState


def test_judgement_beats_skip_when_a_joker_slot_is_empty():
    state = BalatroState()
    state.phase = "ARCANA_PACK"
    state.joker_slots = 5
    state.jokers = [object(), object(), object(), object()]

    judgement = SimpleNamespace(kind="TAROT", label="Judgement")
    policy = PlaybookBalatroPackPolicy()

    judgement_score = policy.score_action(
        state,
        BalatroAction(SELECT_PACK_CARD, target=judgement),
    )
    skip_score = policy.score_action(state, BalatroAction(SKIP_BOOSTER))

    assert judgement_score.total > skip_score.total
    assert "empty Joker slot" in " ".join(judgement_score.notes)


def test_judgement_empty_slot_bonus_scales_with_available_capacity():
    state = BalatroState()
    state.phase = "ARCANA_PACK"
    state.joker_slots = 5
    judgement = SimpleNamespace(kind="TAROT", label="Judgement")
    policy = PlaybookBalatroPackPolicy()

    state.jokers = [object(), object(), object(), object()]
    one_slot = policy.score_action(
        state,
        BalatroAction(SELECT_PACK_CARD, target=judgement),
    ).total

    state.jokers = [object(), object()]
    three_slots = policy.score_action(
        state,
        BalatroAction(SELECT_PACK_CARD, target=judgement),
    ).total

    assert three_slots > one_slot
