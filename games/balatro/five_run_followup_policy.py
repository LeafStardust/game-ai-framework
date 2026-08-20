from __future__ import annotations

"""Follow-up corrections from the second 2026-08-20 five-run review."""

from dataclasses import replace

from games.balatro.actions import PLAY_CARDS, SKIP_BOOSTER
from games.balatro.live.hand_action_policy import PACE_PLAY, LiveHandActionPolicy
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _joker_token(joker: object) -> str:
    return _normalize(
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )


def _has_red_card(state) -> bool:
    return any(
        token in {"redcard", "redcardjoker"}
        for token in (_joker_token(joker) for joker in getattr(state, "jokers", ()) or ())
    )


def _card_is_debuffed(card: object) -> bool:
    return bool(
        getattr(card, "debuffed", getattr(card, "debuff", False))
    )


def _all_played_cards_debuffed(action) -> bool:
    cards = tuple(getattr(action, "cards", ()) or ())
    return bool(cards) and all(_card_is_debuffed(card) for card in cards)


def install_five_run_followup_policy() -> None:
    if getattr(BalatroPackPolicy, "_five_run_followup_installed", False):
        return

    original_rank_actions = BalatroPackPolicy.rank_actions

    def rank_actions(self, state, actions):
        ranked = original_rank_actions(self, state, actions)
        if not _has_red_card(state):
            return ranked

        skip_index = next(
            (
                index
                for index, scored in enumerate(ranked)
                if scored.action.name == SKIP_BOOSTER
            ),
            None,
        )
        if skip_index is None:
            return ranked

        skip = ranked.pop(skip_index)
        best_visible = max((score.total for score in ranked), default=skip.total)
        skip = PackActionScore(
            action=skip.action,
            total=max(float(skip.total), float(best_visible) + 1.0),
            notes=(
                "Red Card owned: prioritize skipping this opened booster to gain permanent Mult",
                *skip.notes,
            ),
        )
        return [skip, *ranked]

    BalatroPackPolicy.rank_actions = rank_actions

    original_hand_decide = LiveHandActionPolicy.decide

    def hand_decide(self, state, plans, **kwargs):
        result = original_hand_decide(self, state, plans, **kwargs)
        if result.mode != PACE_PLAY or result.action.name != PLAY_CARDS:
            return result
        if not _all_played_cards_debuffed(result.action):
            return result

        alternatives = []
        for plan in result.plans:
            if plan.action.name != PLAY_CARDS:
                continue
            if _all_played_cards_debuffed(plan.action):
                continue
            projected = float(
                self.evaluator.project_play(state, plan.action).expected_hand_score
            )
            ratio = self._pace_ratio(projected, result.pace_target)
            if ratio + self.EPSILON < self.thresholds.pace_ratio_floor:
                continue
            alternatives.append((projected, ratio, plan))

        if not alternatives:
            return result

        projected, ratio, alternative = max(
            alternatives,
            key=lambda item: (
                item[0],
                item[1],
                self._within_type_key(item[2]),
            ),
        )
        return replace(
            result,
            action=alternative.action,
            selected_plan=alternative,
            selected_immediate_score=projected,
            selected_pace_ratio=ratio,
            confidence=min(float(result.confidence), self._pace_confidence(ratio)),
            rationale=(
                "suit-boss correction: avoid a play made entirely of visibly debuffed cards when another play still meets required pace",
                *result.rationale,
            ),
        )

    LiveHandActionPolicy.decide = hand_decide
    BalatroPackPolicy._five_run_followup_installed = True
