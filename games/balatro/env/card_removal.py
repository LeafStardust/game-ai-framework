"""Permanent removal for an exact single played-six destruction."""

from games.balatro.card import BalatroCard
from games.balatro.env.boss_debuffs import require_pillar_history_debuff_state
from games.balatro.env.card_order import BASE_DECK_CARD_COUNT, has_bounded_base_copy_order
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def remove_played_six(run: HeadlessRunState, source: BalatroCard) -> None:
    """Remove the authoritative played object from the caller's isolated branch."""
    state = run.public
    order = run.require_playing_card_order()
    if not has_bounded_base_copy_order(order, run.removed_base_six_suits):
        raise HeadlessTransitionError("played-six removal requires exact retained deck order")
    position = next((index for index, card in enumerate(order) if card is source), None)
    if (
        state.phase != "SELECTING_HAND"
        or state.owned_deck is None
        or position is None
        or len(run.played_pile) != 1
        or run.played_pile[0] is not source
        or source.rank != "6"
        or source.enhancement not in (None, "Gold")
        or source.edition is not None
        or source.seal is not None
        or source.permanent_bonus != 0
        or source.forced_selection
        or source.face_down
        or source.played_this_ante is not True
        or source.played_this_ante_observed is not True
        or any(
            card is source
            for zone in (state.hand, state.deck, state.discard_pile, run.draw_pile, run.discard_pile)
            for card in zone
        )
    ):
        raise HeadlessTransitionError("removal requires its exact sole played six")

    snapshot = run.pillar_debuff_snapshot
    active_pillar = state.boss_name == "The Pillar" and not getattr(state.blind, "disabled", False)
    if active_pillar:
        if snapshot is None:
            raise HeadlessTransitionError("played-six removal requires retained active Pillar debuffs")
        require_pillar_history_debuff_state(run)
    elif snapshot is not None:
        raise HeadlessTransitionError("played-six removal found stale Pillar debuff authority")

    base_count = BASE_DECK_CARD_COUNT - len(run.removed_base_six_suits)
    if position < base_count:
        run.removed_base_six_suits = tuple(sorted((*run.removed_base_six_suits, source.suit)))
    if snapshot is not None:
        predeal, created = snapshot
        if position < len(predeal):
            predeal = predeal[:position] + predeal[position + 1:]
        else:
            offset = position - len(predeal)
            created = created[:offset] + created[offset + 1:]
        run.pillar_debuff_snapshot = (predeal, created)

    if run.playing_card_order is not state.owned_deck:
        del run.playing_card_order[position]
    state.owned_deck[:] = [card for card in state.owned_deck if card is not source]
    run.played_pile.clear()
