from __future__ import annotations

"""Make D2 value a prospective Blueprint in a legal useful position.

``JokerBuildValueEvaluator`` historically appended every candidate to the end of the
current roster before running literal scoring probes. That is harmless for ordinary
Jokers but mechanically disables Blueprint, which copies only the Joker immediately
to its right. Live play can reorder Jokers before scoring, so D2 must not value a
purchasable Blueprint as though it were permanently stranded in the final slot.

For Blueprint only, evaluate every insertion position against each existing whole-
build scoring probe and retain the best literal score. No synthetic copy bonus is
added; the ordinary Balatro scorer and Blueprint implementation remain authoritative.
"""

import copy

from games.balatro.build.joker_strategy import JokerBuildValueEvaluator


def install_blueprint_candidate_value_policy() -> None:
    if getattr(JokerBuildValueEvaluator, "_blueprint_candidate_value_installed", False):
        return

    original = JokerBuildValueEvaluator._direct_scoring_gain

    def direct_scoring_gain(self, state, joker):
        if type(joker).__name__ != "BlueprintJoker":
            return original(self, state, joker)

        weighted_gain = 0.0
        total_weight = 0.0
        observed = self._probe_weights(state)

        for hand, template_cards in self._scoring_probes(state):
            cards = copy.deepcopy(list(template_cards))
            before_state = copy.deepcopy(state)
            before_state.hand = copy.deepcopy(cards)

            try:
                before = self.scorer.score(
                    hand,
                    state=before_state,
                    cards=copy.deepcopy(cards),
                    resolve_random_effects=False,
                ).total
            except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
                continue

            best_after = None
            roster_size = len(tuple(getattr(before_state, "jokers", ()) or ()))
            for insertion_index in range(roster_size + 1):
                after_state = copy.deepcopy(before_state)
                candidate = copy.deepcopy(joker)
                after_state.jokers.insert(insertion_index, candidate)
                try:
                    after = self.scorer.score(
                        hand,
                        state=after_state,
                        cards=copy.deepcopy(cards),
                        resolve_random_effects=False,
                    ).total
                except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
                    continue
                if best_after is None or float(after) > float(best_after):
                    best_after = after

            if best_after is None:
                continue

            gain = (float(best_after) - float(before)) / max(abs(float(before)), 1.0)
            if observed is None:
                weight = 1.0
            else:
                weight = (
                    self._OBSERVED_HAND_PRIOR_WEIGHT
                    + observed.get(self._hand_key(hand.value), 0.0)
                )
            weighted_gain += gain * weight
            total_weight += weight

        return weighted_gain / total_weight if total_weight > 0.0 else 0.0

    JokerBuildValueEvaluator._direct_scoring_gain = direct_scoring_gain
    JokerBuildValueEvaluator._blueprint_candidate_value_installed = True
