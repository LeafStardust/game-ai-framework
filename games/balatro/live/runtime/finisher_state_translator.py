from __future__ import annotations

from games.balatro.live.translator import DefaultBalatroStateTranslator


class FinisherAwareBalatroStateTranslator(DefaultBalatroStateTranslator):
    """Hydrate narrow finisher-boss fields omitted by the generic translator.

    The base live snapshot already contains Joker debuff bits and the production
    observer adds Cerulean Bell's current forced-selection bit to hand cards. Keep
    the generic translator stable and layer these controller-facing fields only on
    the production autonomous path.
    """

    def translate(self, snapshot):
        state = super().translate(snapshot)
        payload = snapshot.payload

        hand_payload = payload.get("hand")
        hand_cards = (
            hand_payload.get("cards", [])
            if isinstance(hand_payload, dict)
            else []
        )
        for card, raw in zip(getattr(state, "hand", []), hand_cards):
            if isinstance(raw, dict):
                card.forced_selection = bool(raw.get("forced_selection", False))

        joker_payload = payload.get("jokers")
        joker_cards = (
            joker_payload.get("cards", [])
            if isinstance(joker_payload, dict)
            else []
        )
        for joker, raw in zip(getattr(state, "jokers", []), joker_cards):
            if isinstance(raw, dict):
                joker.debuffed = bool(raw.get("debuff", False))

        return state
