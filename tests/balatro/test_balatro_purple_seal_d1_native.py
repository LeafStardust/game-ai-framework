from types import SimpleNamespace

import games.balatro  # noqa: F401 - initialize the production stack
from games.balatro.actions import BalatroAction, DISCARD_CARDS
from games.balatro.live.hand_action_planner_core import D1LiveBlindClearPlanner


def _card(*, seal=None, visible_value=0.0):
    return SimpleNamespace(
        rank="2",
        suit="Clubs",
        enhancement=None,
        edition=None,
        seal=seal,
        debuffed=False,
        permanent_bonus=0,
        visible_value=visible_value,
    )


def _state(hand):
    return SimpleNamespace(
        hand=list(hand),
        consumable_slots=2,
        consumables=[],
    )


def test_native_child_discard_candidates_preserve_purple_seal_branch():
    planner = D1LiveBlindClearPlanner()
    planner._card_visible_value = lambda card: card.visible_value

    low = _card(visible_value=0.0)
    middle = _card(visible_value=1.0)
    purple = _card(seal="Purple", visible_value=100.0)
    state = _state([low, middle, purple])

    candidates = planner._child_discard_candidates(state)

    assert any(
        len(action.cards) == 1 and action.cards[0] is purple
        for action in candidates
    )


def test_native_discard_beam_keeps_purple_seal_when_generic_slots_fill_first():
    planner = D1LiveBlindClearPlanner()

    first = _card()
    second = _card()
    purple = _card(seal="Purple")
    state = _state([first, second, purple])

    one_card = BalatroAction(DISCARD_CARDS, cards=[first])
    two_cards = BalatroAction(DISCARD_CARDS, cards=[first, second])
    purple_discard = BalatroAction(DISCARD_CARDS, cards=[purple])
    priorities = {
        id(one_card): 100.0,
        id(two_cards): 90.0,
        id(purple_discard): 1.0,
    }
    planner._discard_priority = lambda _state, action: priorities[id(action)]

    chosen = planner._diverse_discard_beam(
        state,
        [one_card, two_cards, purple_discard],
        limit=2,
    )

    assert purple_discard in chosen
    assert len(chosen) == 2


def test_production_stack_does_not_install_purple_seal_overlay():
    assert not hasattr(
        D1LiveBlindClearPlanner,
        "_purple_seal_discard_policy_installed",
    )
