from __future__ import annotations

"""Targeted corrections from the 2026-08-21 Red/White five-run batch.

These rules use public state only and repair four deterministic mistakes observed in
that batch:

* Buffoon-pack Scary Face must recognize an owned Sock and Buskin retrigger engine.
* Joker Stencil must not be admitted into a roster where its post-acquisition XMult
  is only x1 (unless the candidate is Negative and therefore changes slot capacity).
* Hieroglyph is not a safe formation/commitment purchase for Red/White because the
  permanent -1 hand can erase more scoring capacity than the extra ante supplies.
* After The Mouth has locked a hand type, D1 must not spend later hands on a
  different hand type that the boss will score for zero.
"""

from dataclasses import replace

from games.balatro.actions import BUY_JOKER, BUY_VOUCHER, DISCARD_CARDS, PLAY_CARDS, SKIP_BOOSTER
from games.balatro.live.hand_action_policy import PACE_RECOVERY
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.mouth_hand_policy import _hand_type, _replace_with_play
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.shop_arbiter import BuildAwareShopArbiter


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _label(item: object) -> str:
    return str(
        getattr(item, "label", None)
        or getattr(item, "name", None)
        or getattr(item, "ability_name", None)
        or getattr(item, "center", None)
        or type(item).__name__
    )


def _joker_token(joker: object) -> str:
    token = _normalize(_label(joker))
    return token if token.endswith("joker") else token + "joker"


def _owned_tokens(state) -> frozenset[str]:
    return frozenset(_joker_token(joker) for joker in getattr(state, "jokers", ()) or ())


def sock_scary_face_synergy(state, label: str) -> bool:
    """Return whether a visible face scorer directly feeds owned Sock retriggers."""
    if _normalize(label) not in {"scaryface", "smileyface"}:
        return False
    return "sockandbuskinjoker" in _owned_tokens(state)


def stencil_would_be_dead(state, candidate: object) -> bool:
    """True when acquiring this ordinary Stencil can produce only x1 Mult.

    Joker Stencil's own slot behaves as an empty slot for its multiplier. With only
    one effective empty slot after acquisition it is x1 and contributes no scoring.
    Negative candidates are excluded because their slot-capacity change is handled
    by the normal edition-aware path.
    """
    if _joker_token(candidate) != "jokerstenciljoker":
        return False
    if _normalize(getattr(candidate, "edition", "")) == "negative":
        return False
    slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
    if slots <= 0:
        return False
    non_stencil = sum(
        _joker_token(joker) != "jokerstenciljoker"
        for joker in getattr(state, "jokers", ()) or ()
    )
    # ADD from slots-1 occupied leaves x1; a full-roster REPLACE also leaves x1.
    return non_stencil >= slots - 1


def hieroglyph_blocked(state, candidate: object) -> bool:
    """Block mid/late Hieroglyph on the Red/White calibration target."""
    if _normalize(_label(candidate)) != "hieroglyph":
        return False
    deck = _normalize(getattr(state, "deck_name", getattr(state, "deck", "RED")) or "RED")
    stake = _normalize(getattr(state, "stake_name", getattr(state, "stake", "WHITE")) or "WHITE")
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    return deck in {"", "red"} and stake in {"", "white"} and ante >= 3


def _pack_choice_label(result: PackActionScore) -> str:
    target = getattr(result.action, "target", None)
    return str(getattr(target, "label", "") or "")


def _pack_choice_edition(result: PackActionScore) -> str:
    target = getattr(result.action, "target", None)
    data = getattr(target, "data", {}) or {}
    return str(data.get("edition") or "")


def _stencil_pack_dead(state, result: PackActionScore) -> bool:
    if _normalize(_pack_choice_label(result)) != "jokerstencil":
        return False
    if _normalize(_pack_choice_edition(result)) == "negative":
        return False
    slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
    non_stencil = sum(
        _joker_token(joker) != "jokerstenciljoker"
        for joker in getattr(state, "jokers", ()) or ()
    )
    return slots > 0 and non_stencil >= slots - 1


def _enforce_latest_pack_calibration(state, ranked):
    ranked = list(ranked)
    if not ranked:
        return ranked

    skip_total = max(
        (float(item.total) for item in ranked if item.action.name == SKIP_BOOSTER),
        default=0.35,
    )
    rewritten: list[PackActionScore] = []
    for item in ranked:
        label = _pack_choice_label(item)
        if _stencil_pack_dead(state, item):
            rewritten.append(
                replace(
                    item,
                    total=-1.0,
                    notes=(
                        *item.notes,
                        "latest five-run calibration: ordinary Joker Stencil would be x1 after acquisition, so it is not a scoring upgrade",
                    ),
                )
            )
            continue
        if sock_scary_face_synergy(state, label):
            # The observed miss was replacement advantage 0.668 vs 0.750. Do not
            # encode that specific threshold; instead establish a clear positive
            # retrigger-engine floor so the candidate survives replacement gating.
            floor = skip_total + 1.25
            rewritten.append(
                replace(
                    item,
                    total=max(float(item.total), floor),
                    notes=(
                        *item.notes,
                        "latest five-run calibration: owned Sock and Buskin retriggers every scored face card, so visible face-scoring support is an immediate engine upgrade",
                    ),
                )
            )
            continue
        rewritten.append(item)

    return sorted(
        rewritten,
        key=lambda item: (float(item.total), item.action.name != SKIP_BOOSTER),
        reverse=True,
    )


def _matching_mouth_plays(policy, state, plans):
    locked = str(getattr(state, "boss_blind_only_hand", "") or "").upper()
    if not locked:
        return ()
    return tuple(
        plan
        for plan in plans
        if plan.action.name == PLAY_CARDS and _hand_type(policy, plan) == locked
    )


def install_latest_five_run_calibration_policy() -> None:
    if getattr(BalatroPackPolicy, "_latest_five_run_calibration_installed", False):
        return

    original_rank_actions = BalatroPackPolicy.rank_actions

    def rank_actions(self, state, actions):
        return _enforce_latest_pack_calibration(
            state,
            original_rank_actions(self, state, actions),
        )

    BalatroPackPolicy.rank_actions = rank_actions

    original_shop_decide = BuildAwareShopArbiter.decide

    def shop_decide(self, state, visible_actions, *, reroll_cost: int | None):
        filtered = []
        for action in visible_actions:
            if action.name == BUY_JOKER and stencil_would_be_dead(state, action.target):
                continue
            if action.name == BUY_VOUCHER and hieroglyph_blocked(state, action.target):
                continue
            filtered.append(action)
        return original_shop_decide(
            self,
            state,
            filtered,
            reroll_cost=reroll_cost,
        )

    BuildAwareShopArbiter.decide = shop_decide

    original_hand_decide = StrategyAwareLiveHandActionPolicy.decide

    def hand_decide(self, state, plans, **kwargs):
        decision = original_hand_decide(self, state, plans, **kwargs)
        if str(getattr(state, "boss_name", "") or "") != "The Mouth":
            return decision
        locked = str(getattr(state, "boss_blind_only_hand", "") or "").upper()
        if not locked:
            return decision
        if decision.action.name == PLAY_CARDS and _hand_type(self, decision.selected_plan) == locked:
            return decision

        matching = _matching_mouth_plays(self, state, plans)
        if matching:
            plan = max(
                matching,
                key=lambda candidate: (
                    float(self.evaluator.project_play(state, candidate.action).expected_hand_score),
                    self._strategy_fit(state, candidate.action)[0],
                    self._within_type_key(candidate),
                ),
            )
            return _replace_with_play(
                self,
                state,
                decision,
                plan,
                rationale=(
                    f"The Mouth is already locked to {locked}; reject a different poker-hand type that would score zero",
                    "use the highest projected currently playable locked hand instead",
                ),
            )

        if int(getattr(state, "discards_remaining", 0) or 0) > 0:
            discards = tuple(plan for plan in plans if plan.action.name == DISCARD_CARDS)
            if discards:
                plan = max(
                    discards,
                    key=lambda candidate: (
                        float(self.evaluator.evaluate(state, candidate.action)),
                        self._within_type_key(candidate),
                    ),
                )
                value = float(self.evaluator.evaluate(state, plan.action))
                return replace(
                    decision,
                    mode=PACE_RECOVERY,
                    action=plan.action,
                    selected_plan=plan,
                    selected_immediate_score=None,
                    selected_pace_ratio=None,
                    selected_fallback_value=value,
                    rationale=(
                        f"The Mouth is locked to {locked} and no locked hand is currently playable",
                        "discard rather than spend a hand on a boss-invalid zero-score hand",
                        *decision.rationale,
                    ),
                )
        return decision

    StrategyAwareLiveHandActionPolicy.decide = hand_decide

    BalatroPackPolicy._latest_five_run_calibration_installed = True
    BuildAwareShopArbiter._latest_five_run_calibration_installed = True
    StrategyAwareLiveHandActionPolicy._latest_five_run_calibration_installed = True
