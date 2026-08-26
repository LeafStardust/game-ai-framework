from __future__ import annotations

"""Make D2 value prospective copy Jokers under legal scoring order.

``JokerBuildValueEvaluator`` historically appended every candidate to the end of the
current roster before running literal scoring probes. That mechanically disables a
new Blueprint (no Joker to its right) and can undervalue Brainstorm when the best
copy target is not currently leftmost.

For Blueprint/Brainstorm, compare the best literal whole-build score reachable by
ordering the incumbent roster against the best literal score after adding the copy
candidate. Ordinary five-slot rosters are searched exhaustively, matching the live
Joker-order authority. Larger Negative-expanded rosters use bounded copy-target
orders. No synthetic copy bonus is added.
"""

import copy
from itertools import permutations

from games.balatro.build.joker_strategy import JokerBuildValueEvaluator


_COPY_JOKERS = frozenset({"BlueprintJoker", "BrainstormJoker"})
_MAX_EXHAUSTIVE = 5


def _bounded_orders(jokers, *, candidate_name: str | None = None):
    count = len(jokers)
    current = tuple(range(count))
    if count <= _MAX_EXHAUSTIVE:
        return permutations(current)

    orders: list[tuple[int, ...]] = [current]
    if candidate_name == "BlueprintJoker" and count >= 2:
        candidate_index = count - 1
        incumbents = tuple(range(candidate_index))
        for target_position in range(len(incumbents)):
            target_index = incumbents[target_position]
            remaining = [index for index in incumbents if index != target_index]
            # Keep incumbent relative order stable and insert Blueprint immediately
            # before each possible target.
            target_slot = remaining.index(target_index) if target_index in remaining else target_position
            order = list(incumbents)
            order.remove(target_index)
            order.insert(min(target_position, len(order)), candidate_index)
            order.insert(min(target_position + 1, len(order)), target_index)
            if len(order) == count:
                orders.append(tuple(order))
    elif candidate_name == "BrainstormJoker" and count >= 2:
        candidate_index = count - 1
        incumbents = tuple(range(candidate_index))
        for target_index in incumbents:
            order = [target_index]
            order.extend(index for index in incumbents if index != target_index)
            order.append(candidate_index)
            orders.append(tuple(order))

    return tuple(dict.fromkeys(orders))


def _best_score(self, probe_state, cards, hand, *, candidate_name: str | None = None):
    jokers = tuple(getattr(probe_state, "jokers", ()) or ())
    best = None
    for order in _bounded_orders(jokers, candidate_name=candidate_name):
        ordered = copy.deepcopy(probe_state)
        ordered.jokers = [ordered.jokers[index] for index in order]
        try:
            score = self.scorer.score(
                hand,
                state=ordered,
                cards=copy.deepcopy(cards),
                resolve_random_effects=False,
            ).total
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            continue
        if best is None or float(score) > float(best):
            best = score
    return best


def install_blueprint_candidate_value_policy() -> None:
    if getattr(JokerBuildValueEvaluator, "_blueprint_candidate_value_installed", False):
        return

    original = JokerBuildValueEvaluator._direct_scoring_gain

    def direct_scoring_gain(self, state, joker):
        candidate_name = type(joker).__name__
        if candidate_name not in _COPY_JOKERS:
            return original(self, state, joker)

        weighted_gain = 0.0
        total_weight = 0.0
        observed = self._probe_weights(state)

        for hand, template_cards in self._scoring_probes(state):
            cards = copy.deepcopy(list(template_cards))
            before_state = copy.deepcopy(state)
            before_state.hand = copy.deepcopy(cards)

            after_state = copy.deepcopy(before_state)
            after_state.jokers.append(copy.deepcopy(joker))

            before = _best_score(self, before_state, cards, hand)
            after = _best_score(
                self,
                after_state,
                cards,
                hand,
                candidate_name=candidate_name,
            )
            if before is None or after is None:
                continue

            gain = (float(after) - float(before)) / max(abs(float(before)), 1.0)
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
