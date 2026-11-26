"""Permanent-card insertion for an exact DNA scoring callback."""

from dataclasses import replace

from games.balatro.card import BalatroCard
from games.balatro.env.boss_debuffs import require_pillar_history_debuff_state
from games.balatro.env.card_order import MAX_DNA_DECK_CARDS, has_bounded_base_copy_order
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def append_dna_copy(run: HeadlessRunState, source: BalatroCard) -> BalatroCard:
    """Append the single played card's copy to the caller's isolated branch."""
    state = run.public
    order = run.require_playing_card_order()
    if (
        state.phase != "SELECTING_HAND"
        or state.owned_deck is None
        or len(run.played_pile) != 1
        or run.played_pile[0] is not source
        or all(card is not source for card in order)
        or any(card is source for card in state.hand)
    ):
        raise HeadlessTransitionError("DNA requires its exact single played source")
    if not has_bounded_base_copy_order(order) or len(order) >= MAX_DNA_DECK_CARDS:
        raise HeadlessTransitionError("DNA requires a retained deck within its copy bound")
    if (
        source.enhancement not in (None, "Gold")
        or source.edition is not None
        or source.seal is not None
        or source.permanent_bonus != 0
        or source.forced_selection
        or source.face_down
        or type(source.debuffed) is not bool
        or source.played_this_ante is not True
        or source.played_this_ante_observed is not True
    ):
        raise HeadlessTransitionError("DNA source modifiers or public history are not exact")

    snapshot = run.pillar_debuff_snapshot
    active_pillar = state.boss_name == "The Pillar" and not getattr(state.blind, "disabled", False)
    if active_pillar:
        if snapshot is None:
            raise HeadlessTransitionError("DNA requires retained active Pillar debuffs")
        require_pillar_history_debuff_state(run)
    elif snapshot is not None:
        raise HeadlessTransitionError("DNA found stale Pillar debuff authority")
    copied = replace(source, live_id=None, facing_observed=True)
    if run.playing_card_order is not state.owned_deck:
        run.playing_card_order.append(copied)
    state.owned_deck.append(copied)
    state.hand.append(copied)
    if snapshot is not None:
        predeal, created = snapshot
        run.pillar_debuff_snapshot = (predeal, (*created, copied.debuffed))
    return copied
