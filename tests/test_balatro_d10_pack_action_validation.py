from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.live.external.live_memory_pack_action_injected_validation import (
    _ranked_select_action,
)
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import PackActionScore


def _choice(index: int, label: str, center: str, *, kind: str) -> LivePackChoice:
    return LivePackChoice(
        area_index=index,
        address=1000 + index,
        data={
            "live_id": 2000 + index,
            "label": label,
            "center": center,
            "ability_set": kind,
        },
    )


def test_d10_guarded_pack_choice_preserves_policy_selected_hand_targets():
    choice = _choice(1, "Deja Vu", "c_deja_vu", kind="Spectral")
    first_target = object()
    second_target = object()
    targeted_action = BalatroAction(
        SELECT_PACK_CARD,
        cards=[first_target, second_target],
        target=choice,
    )
    ranked = (
        PackActionScore(BalatroAction(SKIP_BOOSTER), total=0.0),
        PackActionScore(targeted_action, total=2.0),
    )

    selected = _ranked_select_action(ranked, 1)

    assert selected is targeted_action
    assert selected.target is choice
    assert selected.cards == [first_target, second_target]


def test_d10_guarded_standard_pack_choice_remains_single_stage_selection():
    choice = _choice(0, "Ace of Hearts", "c_base", kind="PLAYING_CARD")
    standard_action = BalatroAction(SELECT_PACK_CARD, target=choice)
    ranked = (PackActionScore(standard_action, total=1.0),)

    selected = _ranked_select_action(ranked, 0)

    assert selected is standard_action
    assert selected.cards == []


def test_d10_guarded_choice_does_not_substitute_a_different_pack_action():
    first = _choice(0, "The Empress", "c_empress", kind="Tarot")
    second = _choice(1, "The Chariot", "c_chariot", kind="Tarot")
    ranked = (
        PackActionScore(BalatroAction(SELECT_PACK_CARD, target=first), total=2.0),
        PackActionScore(BalatroAction(SKIP_BOOSTER), total=0.0),
    )

    assert _ranked_select_action(ranked, second.area_index) is None
