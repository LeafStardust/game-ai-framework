from __future__ import annotations

"""Final live semantic guards for dominated Red/White decisions.

These guards are intentionally mechanics/public-state based. They do not predict
future draws, shop identities, RNG state, or use a named Joker tier table.
"""

from dataclasses import replace

import games.balatro.build_health_policy as build_health_policy
from games.balatro.actions import REFRESH_SHOP, BalatroAction
from games.balatro.build.joker_scenarios import ScenarioJokerBehaviorAnalyzer
from games.balatro.joker_policy import BUY, HOLD
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.shop_arbiter import BuildAwareShopArbiter


_ANALYZER = ScenarioJokerBehaviorAnalyzer()


def _descriptor_tokens(joker: object) -> tuple[str, ...]:
    try:
        descriptor = _ANALYZER.describe(joker)
    except (AttributeError, TypeError, ValueError):
        return ()
    values = []
    for field in ("produces", "requires", "scales_with", "amplifies"):
        values.extend(str(value).lower() for value in (getattr(descriptor, field, ()) or ()))
    return tuple(values)


def _has_discard_precision_semantics(state) -> bool:
    for card in tuple(getattr(state, "hand", ()) or ()):
        if "purple" in str(getattr(card, "seal", "") or "").lower():
            return True
    return any(
        any("discard" in token for token in _descriptor_tokens(joker))
        for joker in tuple(getattr(state, "jokers", ()) or ())
    )


def _has_single_play_semantics(state) -> bool:
    return any(
        any("single" in token or "one_card" in token for token in _descriptor_tokens(joker))
        for joker in tuple(getattr(state, "jokers", ()) or ())
    )


def _immediate_scoring_candidate(candidate: object) -> bool:
    tokens = _descriptor_tokens(candidate)
    return any(
        any(marker in token for marker in ("chip", "mult", "score"))
        for token in tokens
    )


def _has_authoritative_hold_veto(decision) -> bool:
    """Keep semantic/strategy vetoes above the late competence rescue layer."""
    notes = tuple(str(note).lower() for note in (getattr(decision, "rationale", ()) or ()))
    veto_markers = (
        "canonical bond conflict veto",
        "strategy conflict",
        "conflict veto",
        "mechanical conflict",
        "banned",
        "incompatible",
    )
    return any(marker in note for note in notes for marker in veto_markers)


def install_live_competence_guard_policy() -> None:
    if getattr(LiveBlindClearPlanner, "_rw_live_competence_guard_installed", False):
        return

    original_discard_priority = LiveBlindClearPlanner._discard_priority
    original_candidate_actions = LiveBlindClearPlanner._candidate_actions
    original_joker_decide = PlaybookJokerAcquisitionPolicy.decide
    original_shop_decide = BuildAwareShopArbiter.decide

    def discard_priority(self, state, action):
        priority = original_discard_priority(self, state, action)
        if len(tuple(getattr(action, "cards", ()) or ())) != 1:
            return priority
        if _has_discard_precision_semantics(state):
            return priority
        return (-1_000_000_000.0, 1)

    def candidate_actions(
        self,
        state,
        *,
        allow_discards: bool,
        play_width: int | None = None,
        discard_width: int | None = None,
    ):
        candidates = original_candidate_actions(
            self,
            state,
            allow_discards=allow_discards,
            play_width=play_width,
            discard_width=discard_width,
        )
        if not allow_discards or int(getattr(state, "discards_remaining", 0) or 0) <= 0:
            return candidates
        if int(getattr(state, "hands_remaining", 0) or 0) <= 1:
            return candidates
        if _has_single_play_semantics(state):
            return candidates

        context = self.evaluator._context(state)
        if float(context.best_play_score) >= float(context.required_per_hand):
            return candidates
        has_multi_discard = any(
            action.name == "DISCARD_CARDS" and len(tuple(action.cards or ())) >= 2
            for action in candidates
        )
        if not has_multi_discard:
            return candidates

        filtered = []
        for action in candidates:
            if action.name != "PLAY_CARDS" or len(tuple(action.cards or ())) != 1:
                filtered.append(action)
                continue
            projection = self.evaluator.project_play(state, action)
            if projection.clear_probability > 0.0:
                filtered.append(action)
        return filtered or candidates

    def joker_decide(self, state, candidate):
        decision = original_joker_decide(self, state, candidate)
        if decision.action != HOLD:
            return decision
        # This layer may rescue only an ordinary threshold/adequacy HOLD. Existing
        # semantic direction, Bond-conflict, banned/incompatible, legality and other
        # authoritative vetoes must remain final.
        if _has_authoritative_hold_veto(decision):
            return decision
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        if ante > 4 or not _immediate_scoring_candidate(candidate):
            return decision
        if len(tuple(getattr(state, "jokers", ()) or ())) >= int(getattr(state, "joker_slots", 0) or 0):
            return decision

        options = tuple(getattr(decision, "options", ()) or ())
        legal = [
            option for option in options
            if getattr(option, "mode", None) == BUY
            and float(getattr(option, "build_gain", 0.0) or 0.0) > 0.0
            and int(getattr(getattr(option, "economics", None), "money_after", -1)) >= 0
        ]
        if not legal:
            return decision
        raw_selected = max(
            legal,
            key=lambda option: float(getattr(option, "build_gain", 0.0) or 0.0),
        )
        selected = replace(raw_selected, eligible=True)
        return replace(
            decision,
            action=BUY,
            selected=selected,
            options=tuple(
                selected if option is raw_selected else option
                for option in options
            ),
            rationale=(
                *tuple(getattr(decision, "rationale", ()) or ()),
                "live competence guard: affordable positive immediate scoring in a free early slot cannot be threshold-rejected",
            ),
        )

    def shop_decide(self, state, visible_actions, *, reroll_cost: int | None):
        result = original_shop_decide(self, state, visible_actions, reroll_cost=reroll_cost)
        if str(getattr(getattr(result, "action", None), "name", "")) != "END_SHOP":
            return result
        if reroll_cost is None:
            return result
        try:
            cost = int(reroll_cost)
        except (TypeError, ValueError):
            return result
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        if ante < 3 or cost <= 0 or cost > 8:
            return result
        money = max(0, int(getattr(state, "money", 0) or 0))
        if money - cost < 15:
            return result
        health = build_health_policy._cached_health(self, state)
        if not bool(getattr(health, "scaling_deficit", False)):
            return result
        signature = build_health_policy._shop_signature(state)
        if getattr(self, "_rw_scaling_rescue_reroll_signature", None) == signature:
            return result
        self._rw_scaling_rescue_reroll_signature = signature
        return replace(
            result,
            action=BalatroAction(REFRESH_SHOP),
            source="BUILD_HEALTH_REROLL",
            normalized_gain=max(0.001, float(getattr(result, "normalized_gain", 0.0) or 0.0)),
            rationale=(
                "live competence guard: unresolved scaling deficit with ample cash gets one bounded visible-shop reroll",
                f"reroll=${cost}; cash after=${money - cost}",
                *tuple(getattr(result, "rationale", ()) or ()),
            ),
        )

    LiveBlindClearPlanner._discard_priority = discard_priority
    LiveBlindClearPlanner._candidate_actions = candidate_actions
    PlaybookJokerAcquisitionPolicy.decide = joker_decide
    BuildAwareShopArbiter.decide = shop_decide
    LiveBlindClearPlanner._rw_live_competence_guard_installed = True
    PlaybookJokerAcquisitionPolicy._rw_live_competence_guard_installed = True
    BuildAwareShopArbiter._rw_live_competence_guard_installed = True
