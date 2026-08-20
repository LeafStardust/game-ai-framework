from __future__ import annotations

"""Pack-choice contracts approved for committed strategy play.

- An opened Celestial pack resolves by selecting the best visible Planet unless Red
  Card gives an explicit reason to skip the booster.
- Standard-pack playing cards keep their ordinary card-quality score, then receive
  additional fit for the committed strategy's preferred rank/suit and a small
  deck-growth floor when Blue Joker/Hologram is the active growth engine.
"""

from games.balatro.actions import SKIP_BOOSTER
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore


_DECK_GROWTH_ID = "blue_joker_deck"
_DECK_GROWTH_SCORERS = frozenset({"bluejoker", "hologramjoker"})


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _joker_token(joker: object) -> str:
    for value in (
        type(joker).__name__,
        getattr(joker, "name", ""),
        getattr(joker, "label", ""),
        getattr(joker, "ability_name", ""),
    ):
        token = _normalize(value)
        if token and token not in {"simplenamespace", "object"}:
            return token if token.endswith("joker") else token + "joker"
    return ""


def _owns_red_card(state) -> bool:
    return any(_joker_token(joker) == "redcardjoker" for joker in getattr(state, "jokers", ()) or ())


def _deck_growth_owned(state) -> bool:
    return any(_joker_token(joker) in _DECK_GROWTH_SCORERS for joker in getattr(state, "jokers", ()) or ())


def _strategy_tracker(policy):
    evaluator = getattr(policy, "playstyle_evaluator", None)
    return getattr(evaluator, "strategy_tracker", None)


def _primary_id(tracker, state):
    if tracker is None:
        return None
    resolution = tracker.observe(state)
    primary = resolution.dominant_strategy_id
    getter = getattr(tracker, "primary_strategy_id", None)
    if callable(getter):
        primary = getter(resolution)
    return primary


def _definition_for_primary(tracker, state):
    primary = _primary_id(tracker, state)
    if primary is None:
        return None, None
    return primary, tracker.definitions.get(primary)


def install_committed_pack_choice_policy() -> None:
    if getattr(BalatroPackPolicy, "_committed_pack_choice_policy_installed", False):
        return

    original_rank_actions = BalatroPackPolicy.rank_actions
    original_score_playing_card = BalatroPackPolicy._score_playing_card

    def rank_actions(self, state, actions):
        ranked = original_rank_actions(self, state, actions)
        phase = str(getattr(state, "phase", "") or "")
        if phase != "CELESTIAL_PACK" or _owns_red_card(state):
            return ranked

        planets = [
            result
            for result in ranked
            if getattr(getattr(result.action, "target", None), "kind", None) == "PLANET"
        ]
        if not planets:
            return ranked

        # Keep all existing Planet strategy/outlook ordering. The only correction is
        # that Skip may not beat every visible permanent Planet upgrade after the pack
        # has already been opened and paid for.
        best_planet = max(planets, key=lambda result: result.total)
        skip_total = max(
            (
                float(result.total)
                for result in ranked
                if result.action.name == SKIP_BOOSTER
            ),
            default=float("-inf"),
        )
        if float(best_planet.total) > skip_total:
            return ranked

        forced_total = skip_total + 1e-6
        replacement = PackActionScore(
            best_planet.action,
            forced_total,
            (
                *best_planet.notes,
                "opened Celestial pack contract: take the best visible Planet rather than receive no permanent upgrade",
                "Red Card is not owned, so no explicit pack-skip payoff overrides the Planet",
            ),
        )
        rewritten = [replacement if result is best_planet else result for result in ranked]
        return sorted(
            rewritten,
            key=lambda result: (result.total, result.action.name != SKIP_BOOSTER),
            reverse=True,
        )

    def score_playing_card(self, state, action, choice):
        result = original_score_playing_card(self, state, action, choice)
        tracker = _strategy_tracker(self)
        primary, definition = _definition_for_primary(tracker, state)
        if definition is None:
            return result

        data = getattr(choice, "data", {}) or {}
        value = data.get("value") or {}
        modifier = data.get("modifier") or {}
        rank = str(value.get("rank") or "")
        suit = str(value.get("suit") or "")
        enhancement = str(modifier.get("enhancement") or "")
        seal = str(modifier.get("seal") or "").upper()

        bonus = 0.0
        notes = list(result.notes)
        preferred_ranks = {str(item) for item in getattr(definition, "preferred_ranks", ()) or ()}
        preferred_suits = {str(item) for item in getattr(definition, "preferred_suits", ()) or ()}
        preferred_enhancements = {
            _normalize(item) for item in getattr(definition, "preferred_enhancements", ()) or ()
        }
        preferred_seals = {str(item).upper() for item in getattr(definition, "preferred_seals", ()) or ()}

        rank_alias = {"Ace": "A", "King": "K", "Queen": "Q", "Jack": "J"}.get(rank, rank)
        if rank_alias in preferred_ranks:
            bonus += 1.50
            notes.append(f"committed strategy preferred rank {rank_alias}=+1.500")
        if suit in preferred_suits:
            bonus += 1.25
            notes.append(f"committed strategy preferred suit {suit}=+1.250")
        if enhancement and _normalize(enhancement).removeprefix("m") in preferred_enhancements:
            bonus += 1.00
            notes.append(f"committed strategy preferred enhancement {enhancement}=+1.000")
        if seal and seal in preferred_seals:
            bonus += 1.00
            notes.append(f"committed strategy preferred seal {seal}=+1.000")

        if primary == _DECK_GROWTH_ID and _deck_growth_owned(state):
            bonus += 0.75
            notes.append("Blue/Hologram deck-growth Standard choice: any added playing card advances the engine=+0.750")

        if bonus <= 0.0:
            return result
        return PackActionScore(result.action, float(result.total) + bonus, tuple(notes))

    BalatroPackPolicy.rank_actions = rank_actions
    BalatroPackPolicy._score_playing_card = score_playing_card
    BalatroPackPolicy._committed_pack_choice_policy_installed = True
