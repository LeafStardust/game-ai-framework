from __future__ import annotations

"""D1 DNA execution with canonical strategy-aware card duplication.

DNA's first-hand single-card copy is a strategic setup action.  The old policy only
understood the hand-written Scholar/Aces case; generic Bond composition may instead
link DNA to any engine that requires a concrete card rank.  This policy now derives
those targets from the active semantic strategy while keeping blind survival
strictly authoritative.
"""

from dataclasses import replace

from games.balatro.actions import PLAY_CARDS
from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.build.profile import BalatroBuildProfiler
from games.balatro.live.hand_action_policy import CLEAR_PATH, PACE_PLAY
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


DNA_SAFE_CLEAR_PROBABILITY = 0.90


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


def _owns(state, token: str) -> bool:
    return any(_joker_token(joker) == token for joker in getattr(state, "jokers", ()) or ())


def _first_hand(state) -> bool:
    counts = getattr(state, "round_hand_play_counts", None)
    if not isinstance(counts, dict):
        return False
    return not any(int(value or 0) > 0 for value in counts.values())


def _aces_bond_active(policy, state) -> bool:
    """Use canonical Bond composition instead of the retired strategy tracker."""
    intents = policy._hand_bond_intents(state)
    return any(
        str(target).upper() in {"PAIR", "THREE_OF_A_KIND", "FOUR_OF_A_KIND", "FIVE_OF_A_KIND"}
        and "ace" in str(source).lower()
        for target, _weight, source in intents
    )


def _ace_cards(plan):
    return tuple(card for card in plan.action.cards if str(getattr(card, "rank", "")) in {"A", "Ace"})


def _card_future_key(card) -> tuple[float, ...]:
    edition = str(getattr(card, "edition", "") or "")
    seal = str(getattr(card, "seal", "") or "")
    enhancement = str(getattr(card, "enhancement", "") or "")
    return (
        1.0 if edition else 0.0,
        1.0 if seal else 0.0,
        1.0 if enhancement else 0.0,
        float(getattr(card, "permanent_bonus", 0) or 0),
    )


def _safe_ace_plan(plans, *, dna_single: bool):
    candidates = []
    for plan in plans:
        if plan.action.name != PLAY_CARDS:
            continue
        aces = _ace_cards(plan)
        if not aces:
            continue
        if dna_single and (len(plan.action.cards) != 1 or len(aces) != 1):
            continue
        candidates.append(plan)
    if not candidates:
        return None
    if dna_single:
        safe = [
            plan
            for plan in candidates
            if float(plan.value.clear_probability) >= DNA_SAFE_CLEAR_PROBABILITY
        ]
        if not safe:
            return None
        return max(
            safe,
            key=lambda plan: (
                _card_future_key(_ace_cards(plan)[0]),
                float(plan.value.clear_probability),
                float(plan.value.expected_score),
                float(plan.value.expected_hands_remaining),
            ),
        )
    return max(
        candidates,
        key=lambda plan: (
            float(plan.value.clear_probability),
            len(_ace_cards(plan)),
            float(plan.value.expected_score),
            float(plan.value.expected_hands_remaining),
        ),
    )


def _strategy_dna_rank_targets(state) -> tuple[str, ...]:
    """Return concrete rank requirements from the strategy component linked to DNA."""
    if not _owns(state, "dnajoker"):
        return ()
    try:
        _developments, composition = evaluate_bond_composition(state)
        candidates = tuple(getattr(composition, "strategy_candidates", ()) or ())
        if not candidates:
            return ()
        candidate = next(
            (
                item
                for item in candidates
                if any(_normalize(source) == "dna" for source in getattr(item, "sources", ()) or ())
            ),
            None,
        )
        if candidate is None:
            return ()
        strategy_sources = {
            _normalize(source)
            for source in getattr(candidate, "sources", ()) or ()
            if _normalize(source) != "dna"
        }
        profile = BalatroBuildProfiler().profile(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return ()

    ranks: list[str] = []
    for descriptor in profile.descriptors(kind="JOKER"):
        if _normalize(descriptor.source) not in strategy_sources:
            continue
        features = set(descriptor.requires) | set(descriptor.scales_with) | set(descriptor.amplifies)
        for feature in features:
            text = str(feature)
            if "rank:" not in text.lower():
                continue
            rank = text.split(":")[-1].strip().upper()
            if rank == "ACE":
                rank = "A"
            if rank:
                ranks.append(rank)
    return tuple(dict.fromkeys(ranks))


def _safe_dna_rank_plan(plans, ranks: tuple[str, ...]):
    targets = {str(rank).upper() for rank in ranks}
    if not targets:
        return None
    candidates = []
    for plan in plans:
        if plan.action.name != PLAY_CARDS or len(plan.action.cards) != 1:
            continue
        card = plan.action.cards[0]
        rank = str(getattr(card, "rank", "")).upper()
        if rank == "ACE":
            rank = "A"
        if rank not in targets:
            continue
        probability = float(plan.value.clear_probability)
        if probability < DNA_SAFE_CLEAR_PROBABILITY:
            continue
        candidates.append(plan)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda plan: (
            _card_future_key(plan.action.cards[0]),
            float(plan.value.clear_probability),
            float(plan.value.expected_score),
            float(plan.value.expected_hands_remaining),
        ),
    )


def _replace_with_plan(policy, state, decision, plan, rationale):
    projection = policy.evaluator.project_play(state, plan.action)
    pace_target = float(decision.pace_target or 0.0)
    pace_ratio = (
        float(projection.expected_hand_score) / pace_target
        if pace_target > 0.0
        else float("inf")
    )
    mode = (
        CLEAR_PATH
        if float(plan.value.clear_probability)
        >= float(decision.thresholds.clear_path_probability_floor)
        else PACE_PLAY
    )
    return replace(
        decision,
        mode=mode,
        action=plan.action,
        selected_plan=plan,
        selected_immediate_score=float(projection.expected_hand_score),
        selected_pace_ratio=pace_ratio,
        confidence=max(float(decision.confidence), float(plan.value.clear_probability)),
        rationale=(*rationale, *decision.rationale),
    )


def install_aces_dna_hand_policy() -> None:
    if getattr(StrategyAwareLiveHandActionPolicy, "_aces_dna_hand_policy_installed", False):
        return
    original_decide = StrategyAwareLiveHandActionPolicy.decide

    def decide(self, state, plans, **kwargs):
        plans = tuple(plans)
        decision = original_decide(self, state, plans, **kwargs)

        # Generic canonical strategy path: DNA may duplicate any concrete rank that
        # a mechanically linked strategy component requires.  This covers Walkie's
        # 4/10 engine without a DNA+Walkie pair table and generalizes to future
        # rank-dependent components.
        if _owns(state, "dnajoker") and _first_hand(state):
            rank_targets = _strategy_dna_rank_targets(state)
            plan = _safe_dna_rank_plan(plans, rank_targets)
            if plan is not None and plan.action.cards != decision.action.cards:
                return _replace_with_plan(
                    self,
                    state,
                    decision,
                    plan,
                    (
                        "DNA semantic strategy contract: duplicate a rank required by a mechanically linked component when the blind remains safe",
                        f"required ranks={rank_targets}; selected rank={getattr(plan.action.cards[0], 'rank', None)}",
                        f"DNA line projected clear probability={float(plan.value.clear_probability):.3f} >= {DNA_SAFE_CLEAR_PROBABILITY:.2f}",
                        "long-term duplication remains subordinate to blind survival",
                    ),
                )

        if not _aces_bond_active(self, state):
            return decision

        dna_setup = _owns(state, "dnajoker") and _owns(state, "scholarjoker") and _first_hand(state)
        if dna_setup:
            plan = _safe_ace_plan(plans, dna_single=True)
            if plan is not None and plan.action.cards != decision.action.cards:
                return _replace_with_plan(
                    self,
                    state,
                    decision,
                    plan,
                    (
                        "Aces Bond + Scholar + DNA first-hand contract: duplicate a strategically valuable Ace when the full blind remains safe",
                        f"DNA Ace line projected clear probability={float(plan.value.clear_probability):.3f} >= {DNA_SAFE_CLEAR_PROBABILITY:.2f}",
                        "long-term duplication is subordinate to blind survival",
                    ),
                )
            if plan is None:
                return replace(
                    decision,
                    rationale=(
                        *decision.rationale,
                        f"Aces Bond + DNA setup was not forced because no single-Ace line retained {DNA_SAFE_CLEAR_PROBABILITY:.0%} projected clear probability",
                    ),
                )

        best_ace = _safe_ace_plan(plans, dna_single=False)
        if best_ace is None:
            return decision
        selected_probability = float(decision.selected_plan.value.clear_probability)
        ace_probability = float(best_ace.value.clear_probability)
        tolerance = float(decision.thresholds.safe_clear_probability_tolerance)
        if ace_probability + tolerance < selected_probability:
            return decision
        if not _ace_cards(decision.selected_plan):
            return _replace_with_plan(
                self,
                state,
                decision,
                best_ace,
                (
                    "Aces Bond safe-equivalent tie-break: prefer an Ace-bearing play for Scholar/deck development",
                    f"Ace line clear probability={ace_probability:.3f}; selected baseline={selected_probability:.3f}; tolerance={tolerance:.3f}",
                ),
            )
        return decision

    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._aces_dna_hand_policy_installed = True
