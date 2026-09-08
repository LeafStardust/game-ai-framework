from __future__ import annotations

"""Replace D9's fixed Blue Joker/Hologram card-add bonus with literal score value.

The historical playing-card scorer treated any active Blue Joker/Hologram as a flat
``+1.0`` and, for vanilla cards, replaced the ordinary dilution penalty with that
bonus. The two effects are independent: a weak extra card still dilutes deck quality,
while Blue Joker/Hologram gain their exact scoring mechanics from the addition.

This wrapper restores the vanilla dilution term when applicable and adds the shared
literal before/after deck-growth score value for every selected playing card,
modified or not.
"""

from dataclasses import replace

from games.balatro.build.deck_growth_value import DeckGrowthScoreValueEvaluator
from games.balatro.deck_growth_pack_policy import deck_growth_pack_support_active
from games.balatro.pack_policy import BalatroPackPolicy


def install_deck_growth_playing_card_value_policy() -> None:
    if getattr(BalatroPackPolicy, "_literal_deck_growth_card_value_installed", False):
        return

    original_init = BalatroPackPolicy.__init__
    original_score = BalatroPackPolicy._score_playing_card

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._literal_deck_growth_evaluator = DeckGrowthScoreValueEvaluator()

    def score_playing_card(self, state, action, choice):
        scored = original_score(self, state, action, choice)
        if not deck_growth_pack_support_active(state):
            return scored

        value, notes = self._literal_deck_growth_evaluator.evaluate(state, added_count=1)
        modifier = choice.data.get("modifier") or {}
        enhancement = modifier.get("enhancement")
        edition = modifier.get("edition")
        seal = modifier.get("seal")
        vanilla = not enhancement and not edition and not seal

        # The historical branch added +1.0 instead of the vanilla dilution penalty.
        # Remove that synthetic replacement and restore the independent dilution cost.
        correction = float(value)
        correction -= float(self.DECK_GROWTH_CARD_SUPPORT_VALUE) if vanilla else 0.0
        correction -= float(self.VANILLA_CARD_DILUTION_PENALTY) if vanilla else 0.0

        return replace(
            scored,
            total=float(scored.total) + correction,
            notes=(
                *tuple(scored.notes),
                *(
                    (
                        f"remove historical deck-growth support= -{self.DECK_GROWTH_CARD_SUPPORT_VALUE:.3f}",
                        f"restore independent vanilla dilution= -{self.VANILLA_CARD_DILUTION_PENALTY:.3f}",
                    )
                    if vanilla
                    else ()
                ),
                *notes,
            ),
        )

    BalatroPackPolicy.__init__ = init
    BalatroPackPolicy._score_playing_card = score_playing_card
    BalatroPackPolicy._literal_deck_growth_card_value_installed = True
