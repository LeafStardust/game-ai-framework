from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState


class _Estimator:
    def estimate(self, state, action):
        return 1.0, ("fixture consumable value",)


def _choice(label, *, area_index=0, address=0x1000):
    return LivePackChoice(
        area_index=area_index,
        address=address,
        data={
            "area_index": area_index,
            "address": address,
            "live_id": 501,
            "label": label,
            "ability_name": label,
            "ability_set": "Spectral",
        },
    )


def _pack_state(cards):
    state = BalatroState()
    state.phase = "SPECTRAL_PACK"
    state.hand = list(cards)
    state.deck = [BalatroCard(card.rank, card.suit, card.enhancement, card.edition, card.seal) for card in cards]
    return state


def test_targeted_spectral_pack_choice_carries_exact_b6_hand_target():
    card = BalatroCard("4", "Clubs")
    state = _pack_state([card])
    choice = _choice("Deja Vu")
    ranked = BalatroPackPolicy(item_estimator=_Estimator(), skip_bias=0.35).rank_actions(
        state,
        [BalatroAction(SELECT_PACK_CARD, target=choice), BalatroAction(SKIP_BOOSTER)],
    )
    selected = ranked[0]
    assert selected.action.name == SELECT_PACK_CARD
    assert selected.action.target is choice
    assert selected.action.cards == [card]
    assert any("target_indices=(0,)" in note for note in selected.notes)
    assert any("B6 pack target gain=" in note for note in selected.notes)


def test_deferred_spectral_pack_choice_remains_fail_closed():
    card = BalatroCard("4", "Clubs")
    state = _pack_state([card])
    choice = _choice("Familiar")
    ranked = BalatroPackPolicy(item_estimator=_Estimator()).rank_actions(
        state,
        [BalatroAction(SELECT_PACK_CARD, target=choice), BalatroAction(SKIP_BOOSTER)],
    )
    assert ranked[0].action.name == SKIP_BOOSTER
    spectral = next(result for result in ranked if result.action.name == SELECT_PACK_CARD)
    assert spectral.total == -1.0
    assert spectral.action.cards == []
