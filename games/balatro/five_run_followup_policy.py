from __future__ import annotations

"""Follow-up corrections from the second 2026-08-20 five-run review."""

from dataclasses import replace

from games.balatro.actions import (
    DISCARD_CARDS,
    END_SHOP,
    PLAY_CARDS,
    REFRESH_SHOP,
    SKIP_BOOSTER,
    BalatroAction,
)
from games.balatro.live.hand_action_policy import PACE_PLAY, LiveHandActionPolicy
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.shop_arbiter import BuildAwareShopArbiter


WEAK_FULL_ROSTER_TOKENS = frozenset(
    {
        "banner",
        "bannerjoker",
        "goldenjoker",
        "todolist",
        "todolistjoker",
        "jokerstencil",
        "jokerstenciljoker",
    }
)


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _joker_token(joker: object) -> str:
    return _normalize(
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )


def _public_state_value(joker: object, name: str, default: float = 0.0) -> float:
    public_state = getattr(joker, "public_state", None)
    value = None
    if isinstance(public_state, dict):
        value = public_state.get(name)
    elif public_state is not None:
        value = getattr(public_state, name, None)
    if value is None:
        value = getattr(joker, name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _realized_joker_weakness(joker: object) -> float:
    """Return a bounded weak-roster contribution from public realized state.

    This is deliberately not a replacement for strategy ranking. It only informs
    whether a cash-rich full roster is developed enough to justify ending a shop.
    Static filler contributes 1.0. Scalers contribute weakness only while their
    public scaling is still materially under-developed.
    """

    token = _joker_token(joker)
    if token in WEAK_FULL_ROSTER_TOKENS:
        return 1.0
    if token in {"redcard", "redcardjoker"}:
        mult = _public_state_value(joker, "mult")
        if mult <= 0:
            return 1.0
        if mult < 10:
            return 0.5
        return 0.0
    if token in {"greenjoker", "greenjokerjoker"}:
        mult = _public_state_value(joker, "mult")
        if mult < 8:
            return 0.75
        if mult < 16:
            return 0.35
        return 0.0
    return 0.0


def _roster_pressure(state) -> float:
    jokers = tuple(getattr(state, "jokers", ()) or ())
    slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
    if slots <= 0 or len(jokers) < slots:
        return 0.0
    return sum(_realized_joker_weakness(joker) for joker in jokers)


def _shop_signature(state) -> tuple[int, int]:
    return (
        max(1, int(getattr(state, "ante", 1) or 1)),
        max(0, int(getattr(state, "round_num", 0) or 0)),
    )


def _should_force_roster_reroll(state, *, reroll_cost: int | None) -> bool:
    if reroll_cost is None:
        return False
    cost = int(reroll_cost)
    if cost <= 0 or cost > 8:
        return False
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    if ante < 4:
        return False
    pressure = _roster_pressure(state)
    if pressure < 2.0:
        return False
    money = max(0, int(getattr(state, "money", 0) or 0))
    # Keep the established late-game safety reserve while allowing surplus cash
    # to search for an actual scoring upgrade instead of dying with $20-$50 idle.
    return money - cost >= 20


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


def _final_discard_is_material(result) -> bool:
    selected = result.selected_plan
    best_play = result.best_play
    probability_gain = (
        float(selected.value.clear_probability)
        - float(best_play.value.clear_probability)
    )
    score_gain = (
        float(selected.value.expected_score)
        - float(best_play.value.expected_score)
    )
    required_score_gain = max(25.0, 0.35 * float(result.pace_target))
    return probability_gain >= 0.08 or score_gain >= required_score_gain


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

    original_shop_decide = BuildAwareShopArbiter.decide

    def shop_decide(self, state, visible_actions, *, reroll_cost: int | None):
        result = original_shop_decide(
            self,
            state,
            visible_actions,
            reroll_cost=reroll_cost,
        )
        if result.action.name != END_SHOP:
            return result
        if not _should_force_roster_reroll(state, reroll_cost=reroll_cost):
            return result

        signature = _shop_signature(state)
        if getattr(self, "_five_run_roster_reroll_signature", None) == signature:
            return result
        self._five_run_roster_reroll_signature = signature

        pressure = _roster_pressure(state)
        return replace(
            result,
            action=BalatroAction(REFRESH_SHOP),
            source="ROSTER_PRESSURE_REROLL",
            normalized_gain=max(0.001, float(result.normalized_gain)),
            rationale=(
                "five-run optimization: cash-rich full weak roster should search once for a concrete upgrade before ending shop",
                f"realized roster pressure={pressure:.2f}",
                f"paid reroll cost=${int(reroll_cost or 0)}; at least $20 remains afterward",
                "realized public scaler state is included so an unscaled route is not protected like an online engine",
                *result.rationale,
            ),
        )

    BuildAwareShopArbiter.decide = shop_decide

    original_hand_decide = LiveHandActionPolicy.decide

    def hand_decide(self, state, plans, **kwargs):
        result = original_hand_decide(self, state, plans, **kwargs)

        # Preserve the final discard unless the modeled recovery improvement is
        # material. The logs repeatedly ended with all discards gone and no clear
        # probability gain commensurate with spending the last recovery resource.
        if (
            result.action.name == DISCARD_CARDS
            and int(getattr(state, "discards_remaining", 0) or 0) == 1
            and int(getattr(state, "hands_remaining", 0) or 0) > 1
            and not _final_discard_is_material(result)
        ):
            play = result.best_play
            projected = float(
                self.evaluator.project_play(state, play.action).expected_hand_score
            )
            ratio = self._pace_ratio(projected, result.pace_target)
            return replace(
                result,
                action=play.action,
                selected_plan=play,
                selected_immediate_score=projected,
                selected_pace_ratio=ratio,
                selected_fallback_value=float(self.evaluator.evaluate(state, play.action)),
                rationale=(
                    "five-run optimization: preserve the final discard because its modeled recovery gain is not material",
                    "last discard now requires >=8 percentage-point clear-probability gain or >=35% of pace-target expected-score gain",
                    *result.rationale,
                ),
            )

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
