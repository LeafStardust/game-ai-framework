from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.external.live_memory_pack_terms import LivePackSelectionTerms
from games.balatro.live.injected.action_dispatcher import LiveMemoryInjectedActionDispatcher
from games.balatro.live.injected.bridge import FirstPartyBalatroBridge
from games.balatro.live.pack import LivePackChoice
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState


class _Estimator:
    def estimate(self, state, action):
        return 1.0, ("fixture consumable value",)


class _RecordingBridge(FirstPartyBalatroBridge):
    def __init__(self):
        self.calls = []

    def _call(self, action, indices=()):
        self.calls.append((action, tuple(indices)))
        return "accepted"


class _Observer:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)

    def observe(self):
        if len(self.snapshots) > 1:
            return self.snapshots.pop(0)
        return self.snapshots[0]


def _choice(label="The Chariot", *, area_index=0, address=0x1000):
    return LivePackChoice(
        area_index=area_index,
        address=address,
        data={
            "area_index": area_index,
            "address": address,
            "live_id": 501,
            "label": label,
            "ability_name": label,
            "ability_set": "Tarot",
        },
    )


def _pack_state(cards):
    state = BalatroState()
    state.phase = "TAROT_PACK"
    state.hand = list(cards)
    state.deck = [
        BalatroCard(card.rank, card.suit, card.enhancement, card.edition, card.seal)
        for card in cards
    ]
    return state


def _snapshot(sequence, phase):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={},
    )


def test_targeted_tarot_pack_choice_carries_exact_b6_hand_target():
    card = BalatroCard("4", "Clubs")
    state = _pack_state([card])
    choice = _choice()
    actions = [
        BalatroAction(SELECT_PACK_CARD, target=choice),
        BalatroAction(SKIP_BOOSTER),
    ]

    ranked = BalatroPackPolicy(
        item_estimator=_Estimator(),
        skip_bias=0.35,
    ).rank_actions(state, actions)

    selected = ranked[0]
    assert selected.action.name == SELECT_PACK_CARD
    assert selected.action.target is choice
    assert selected.action.cards == [card]
    assert any("target_indices=(0,)" in note for note in selected.notes)
    assert any("B6 pack target gain=" in note for note in selected.notes)


def test_targeted_tarot_without_a_legal_hand_target_still_fails_closed():
    state = _pack_state([])
    choice = _choice()

    ranked = BalatroPackPolicy(item_estimator=_Estimator()).rank_actions(
        state,
        [BalatroAction(SELECT_PACK_CARD, target=choice), BalatroAction(SKIP_BOOSTER)],
    )

    assert ranked[0].action.name == SKIP_BOOSTER
    targeted = next(result for result in ranked if result.action.name == SELECT_PACK_CARD)
    assert targeted.total == -1.0
    assert targeted.action.cards == []


def test_bridge_encodes_pack_slot_and_hand_targets_as_separate_index_spaces():
    bridge = _RecordingBridge()

    bridge.select_pack_card(0, (0, 2))

    assert bridge.calls == [("PACK_SELECT", (0, 0, 2))]


def test_dispatcher_forwards_exact_target_indices_for_targeted_pack_choice():
    card = SimpleNamespace(live_id=101)
    state = SimpleNamespace(hand=[card])
    choice = _choice()
    action = BalatroAction(SELECT_PACK_CARD, cards=[card], target=choice)
    before = _snapshot(10, "TAROT_PACK")
    after = _snapshot(11, "SHOP")
    bridge = _RecordingBridge()
    terms = LivePackSelectionTerms(
        choices_remaining=1,
        choice_addresses=(choice.address,),
    )

    result = LiveMemoryInjectedActionDispatcher(
        _Observer([after]),
        bridge=bridge,
        timeout=0.1,
        poll_interval=0,
        pack_terms_reader=lambda: terms,
    ).dispatch(action, state=state, snapshot=before)

    assert bridge.calls == [("PACK_SELECT", (0, 0))]
    assert result.after is after
    assert result.details["area_index"] == 0
    assert result.details["target_indices"] == (0,)
    assert result.details["selected_address"] == choice.address


def test_dispatcher_requires_state_when_targeted_pack_action_has_cards():
    card = SimpleNamespace(live_id=101)
    choice = _choice()
    action = BalatroAction(SELECT_PACK_CARD, cards=[card], target=choice)
    before = _snapshot(10, "TAROT_PACK")
    terms = LivePackSelectionTerms(
        choices_remaining=1,
        choice_addresses=(choice.address,),
    )

    dispatcher = LiveMemoryInjectedActionDispatcher(
        _Observer([before]),
        bridge=_RecordingBridge(),
        timeout=0,
        poll_interval=0,
        pack_terms_reader=lambda: terms,
    )

    try:
        dispatcher.dispatch(action, snapshot=before)
    except RuntimeError as error:
        assert "targeted SELECT_PACK_CARD requires the translated state" in str(error)
    else:
        raise AssertionError("targeted pack execution must fail closed without translated state")
